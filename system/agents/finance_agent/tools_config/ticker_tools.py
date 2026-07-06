"""Tools for stock analysis: fetch data, extract metrics, score sentiment, and decide buy/sell/hold."""

from typing import Dict, Any, List, Optional
import datetime
import json
import pandas as pd

import yfinance as yf
from system.utility.utils import retry_on_exception
from system.utility.logger import logger


try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except ImportError:  # pragma: no cover - optional dependency
    SentimentIntensityAnalyzer = None


def _safe_get_ticker_attr(ticker, attr: str):
    """Safely get ticker attribute with error handling."""
    try:
        value = getattr(ticker, attr, None)
        if value is None:
            return None
        return value
    except Exception:
        return None

# returns None safely when conversion is not possible
def _to_optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
    
# preprocess dataframes to ensure they have proper index

def _preprocess_dataframe(df):
    """Ensure DataFrame has a proper index and standardized format."""
    if df is None or not hasattr(df, "empty") or df.empty:
        return None
    
    df = df.copy()
    
    # Reset index to avoid duplicate/messy indices
    df.reset_index(drop=True, inplace=True)
    
    # Ensure the first column is treated as index if appropriate
    if df.shape[1] > 1:
        df.set_index(df.columns[0], inplace=True)
    
    # Transpose for consistency
    df = df.T
    
    # Reset index and rename the first column to 'Date'
    df.reset_index(inplace=True)
    df.rename(columns={df.columns[0]: "Date"}, inplace=True)
    
    return df.iloc[:-1]  # Exclude the last row if it's a summary or empty row


# implementing fallback for Financial extraction
def _first_numeric(*values):
    for v in values:
        if v is None:
            continue
        try:
            if str(v) != "nan":
                return float(v)
        except Exception:
            continue
    return None


def _parse_news(ticker, top_n: int = 5) -> List[Dict[str, Any]]:
    """Extract and parse news from ticker."""
    news = []
    try:
        raw_news = ticker.news or []
        for n in raw_news[:top_n]:
            if not isinstance(n, dict):
                continue
            title = n.get("title") or n.get("headline") or ""
            if not title:
                continue
            try:
                ts = n.get("providerPublishTime")
                if ts:
                    ts = datetime.datetime.fromtimestamp(int(ts)).isoformat()
            except (ValueError, OSError):
                ts = None
            news.append({
                "title": title,
                "link": n.get("link", ""),
                "publisher": n.get("publisher") or n.get("source", ""),
                "time": ts
            })
    except Exception as e:
        logger.debug(f"News fetch failed: {e}")
    return news


def _get_dataframe_row(df, candidates: List[str]):
    """Try to get row from DataFrame using candidate names."""
    if df is None or not hasattr(df, "index"):
        return None
    for name in candidates:
        if name in df.index:
            return df.loc[name].iloc[0] if len(df.loc[name]) > 0 else None
    return None


def _extract_price_metrics(data: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """Extract price-related metrics."""
    metrics : dict[str, Optional[float]] = {
        "current_price": None,
        "trailing_pe": None,
        "forward_pe": None,
        "market_cap": None,
        }
    info = data.get("info", {}) or {}
    
    try:
        hist = data.get("history")
        if hist is not None and hasattr(hist, "empty") and not hist.empty:
            metrics["current_price"] = float(hist["Close"].iloc[-1])
        elif info.get("currentPrice"):
            metrics["current_price"] = _to_optional_float(info.get("currentPrice"))
    except Exception:
        pass
    
    metrics["trailing_pe"] = _first_numeric(info.get("trailingPE"))
    metrics["forward_pe"] = _first_numeric(info.get("forwardPE"))
    metrics["market_cap"] = _first_numeric(info.get("marketCap"))
    return metrics


def _extract_revenue_metrics(fin) -> Dict[str, Optional[float]]:
    """Extract revenue-related metrics."""
    metrics: dict[str, Optional[float]] = {"revenue": None, "net_income": None, "revenue_growth_pct": None}
    if fin is None or not hasattr(fin, "empty") or fin.empty:
        return metrics
    
    try:
        rev_candidates = ["Total Revenue", "Revenue", "Revenues"]
        net_candidates = ["Net Income", "Net Income Applicable To Common Shares", "NetIncomeLoss"]
        
        rev = _get_dataframe_row(fin, rev_candidates)
        net = _get_dataframe_row(fin, net_candidates)
        
        metrics["revenue"] = float(rev) if rev is not None else None
        metrics["net_income"] = float(net) if net is not None else None
        
        # Revenue growth YoY
        if fin.shape[1] >= 2:
            for name in rev_candidates:
                if name in fin.index:
                    row = fin.loc[name]
                    if len(row) >= 2:
                        rev_new = float(row.iloc[0]) if row.iloc[0] is not None else None
                        rev_old = float(row.iloc[1]) if row.iloc[1] is not None else None
                        if rev_new is not None and rev_old not in (None, 0):
                            metrics["revenue_growth_pct"] = ((rev_new - rev_old) / abs(rev_old)) * 100.0
                    break
    except Exception as e:
        logger.debug(f"Revenue extraction failed: {e}")
    
    return metrics


def _extract_debt_metrics(bal) -> Dict[str, Optional[float]]:
    """Extract debt and equity metrics."""
    metrics: dict[str, Optional[float]] = {"total_debt": None, "total_equity": None, "debt_to_equity": None}
    if bal is None or not hasattr(bal, "empty") or bal.empty:
        return metrics
    
    try:
        debt_candidates = ["Long Term Debt", "Total Debt", "Long-term Debt"]
        equity_candidates = ["Total Stockholder Equity", "Total Stockholders' Equity", "Total Equity", "Stockholders Equity"]
        
        total_debt = _get_dataframe_row(bal, debt_candidates)
        total_equity = _get_dataframe_row(bal, equity_candidates)
        
        if total_debt is not None:
            metrics["total_debt"] = float(total_debt)
        if total_equity is not None:
            metrics["total_equity"] = float(total_equity)
        
        if (metrics["total_debt"] is not None and metrics["total_equity"] is not None and metrics["total_equity"] > 0):
            metrics["debt_to_equity"] = metrics["total_debt"] / metrics["total_equity"]
    except Exception as e:
        logger.debug(f"Debt extraction failed: {e}")
    
    return metrics


@retry_on_exception(max_attempts=3, delay=1.0)
def fetch_company_data(symbol: str, top_n_news: int = 5, history_period: str = "1y") -> Dict[str, Any]:
    """Fetch comprehensive company data from yfinance with retry and error handling.
    
    Retrieves company information, financial statements, news headlines, and
    historical price data for a given stock ticker. Handles network errors and
    missing data gracefully, retrying up to 3 times with exponential backoff.
    
    Args:
        symbol (str): The stock ticker symbol (e.g., "AAPL", "MSFT").
                     Will be converted to uppercase.
        top_n_news (int): Maximum number of recent news articles to retrieve.
                         Defaults to 5.
        history_period (str): Historical data period as yfinance period string
                             (e.g., "1y", "6mo", "3mo"). Defaults to "1y".
    
    Returns:
        Dict[str, Any]: A dictionary containing:
            - symbol (str): The ticker symbol in uppercase
            - company (str): Company name (long name, short name, or ticker)
            - info (Dict): Company information including P/E, market cap, etc.
            - financials (DataFrame): Annual financial statements
            - balance_sheet (DataFrame): Annual balance sheet data
            - news (List[Dict]): Recent news articles with title, link, publisher, time
            - history (DataFrame): Historical OHLCV price data
    
    Note:
        Missing data fields are set to None rather than raising exceptions.
        The function retries on network errors up to 3 times before failing.
    """
    try:
        ticker = yf.Ticker(symbol)
    except Exception as exc:
        return {
            "symbol": symbol.upper(),
            "company": symbol.upper(),
            "info": {},
            "financials": None,
            "balance_sheet": None,
            "news": [],
            "history": None,
            "error": str(exc),
        }
    
    # Basic info
    try:
        info = ticker.info or {}
    except Exception:
        info = {}
    
    company = info.get("longName") or info.get("shortName") or symbol.upper()
    
    # Financial statements
    financials = _safe_get_ticker_attr(ticker, "financials")
    balance_sheet = _safe_get_ticker_attr(ticker, "balance_sheet")
    
    # preprocess dataframes to ensure they are not empty and have proper index
    financials = _preprocess_dataframe(financials)
    balance_sheet = _preprocess_dataframe(balance_sheet)
    
    # News
    news = _parse_news(ticker, top_n_news)
    
    # History
    history = None
    try:
        history = ticker.history(period=history_period)
    except Exception:
        pass
    
    return {
        "symbol": symbol.upper(),
        "company": company,
        "info": info,
        "financials": financials,
        "balance_sheet": balance_sheet,
        "news": news,
        "history": history
    }


def extract_financial_metrics(data: dict) -> Dict[str, Optional[float]]:
    """Extract comprehensive financial metrics from company data.
    
    Processes company data fetched from yfinance and extracts key financial
    metrics organized into three categories: price metrics, revenue metrics,
    and debt/equity metrics. Handles missing or malformed data gracefully.
    
    Args:
        data (Dict[str, Any]): Company data dictionary as returned by fetch_company_data.
                              Should contain 'info', 'financials', and 'balance_sheet' keys.
    
    Returns:
        Dict[str, Optional[float]]: A dictionary with the following metrics:
            Price metrics:
                - current_price (float): Current stock price
                - trailing_pe (float): Trailing P/E ratio
                - forward_pe (float): Forward P/E ratio
                - market_cap (float): Market capitalization
            Revenue metrics:
                - revenue (float): Annual revenue
                - net_income (float): Annual net income
                - revenue_growth_pct (float): Year-over-year revenue growth %
            Debt metrics:
                - total_debt (float): Total company debt
                - total_equity (float): Total stockholder equity
                - debt_to_equity (float): Debt-to-equity ratio
            
            All values default to None if unavailable or cannot be extracted.
    
    Note:
        Missing metrics are set to None rather than raising exceptions.
        Extraction failures are logged at DEBUG level.
    """
    metrics: dict[str, Optional[float]] = {
        "current_price": None,
        "trailing_pe": None,
        "forward_pe": None,
        "market_cap": None,
        "revenue": None,
        "net_income": None,
        "revenue_growth_pct": None,
        "total_debt": None,
        "total_equity": None,
        "debt_to_equity": None
    }
    
    # Extract each metric group
    metrics.update(_extract_price_metrics(data))
    metrics.update(_extract_revenue_metrics(data.get("financials")))
    metrics.update(_extract_debt_metrics(data.get("balance_sheet")))
    
    return metrics


def score_news_sentiment(headlines: List[str]) -> float:
    """Analyze and score the overall sentiment of news headlines.
    
    Processes a list of news headlines and returns an aggregate sentiment score
    indicating overall market sentiment for the company. Uses VADER sentiment
    analysis if available, otherwise falls back to word-based scoring.
    
    Args:
        headlines (List[str]): List of news headlines to analyze. Can be any
                              text content; empty headlines are skipped.
    
    Returns:
        float: Aggregate sentiment score ranging from -1.0 to 1.0:
               - Positive values (closer to 1.0) indicate bullish sentiment
               - Negative values (closer to -1.0) indicate bearish sentiment
               - Zero indicates neutral sentiment
               - Empty headline list returns 0.0
    
    Note:
        Uses VADER (Valence Aware Dictionary and sEntiment Reasoner) from
        vaderSentiment if installed. Falls back to simple word lexicon matching
        with predefined positive/negative word sets.
        Returns 0.0 for empty input or if no sentiment indicators found.
    
    Example:
        headlines = ["Apple beats earnings expectations", "Stock price falls"]
        score = score_news_sentiment(headlines)
        # Returns a score between -1.0 and 1.0 reflecting overall sentiment
    """
    if not headlines:
        return 0.0
    
    # Try VADER
    try:
        if SentimentIntensityAnalyzer is None:
            raise ImportError
        analyzer = SentimentIntensityAnalyzer()
        scores = [analyzer.polarity_scores(h).get("compound", 0.0) for h in headlines if h]
        return float(sum(scores) / len(scores)) if scores else 0.0
    except Exception:
        pass

    # Fallback: simple word-based sentiment
    POS = {"good", "great", "positive", "beat", "beats", "up", "gain", "gains", "growth", "strong", 
           "profit", "profits", "outperform", "surge", "rally", "excellent", "bullish", "boost"}
    NEG = {"bad", "worse", "miss", "missed", "down", "loss", "losses", "weak", "decline", "fall", 
           "cut", "warn", "warning", "bearish", "slump", "crash", "plunge"}
    
    total_score = 0.0
    count = 0
    
    for h in headlines:
        if not h:
            continue
        words = set(w.strip(".,!?:;()[]\"'").lower() for w in h.split())
        pos = len(words & POS)
        neg = len(words & NEG)
        if pos + neg > 0:
            total_score += (pos - neg) / (pos + neg)
            count += 1
    
    return float(total_score / count) if count > 0 else 0.0



def decide_action(metrics: Dict[str, Any], sentiment_score: float,
                  thresholds: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Apply decision rules to financial metrics and generate a BUY/SELL/HOLD verdict.
    
    Evaluates company financial metrics, news sentiment, and valuation ratios
    against configurable thresholds to produce an investment recommendation.
    Uses a scoring system where positive factors contribute +1 and negative
    factors contribute -1 to determine the final verdict.
    
    Args:
        metrics (Dict[str, Any]): Dictionary of financial metrics extracted
                                 from company data. Expected keys include:
                                 - net_income (float): Annual net income
                                 - revenue_growth_pct (float): YoY revenue growth %
                                 - debt_to_equity (float): Debt-to-equity ratio
                                 - trailing_pe (float): Trailing P/E ratio
                                 - forward_pe (float): Forward P/E ratio
        sentiment_score (float): Overall sentiment score (-1.0 to 1.0) from
                               news headline analysis.
        thresholds (Optional[Dict[str, float]]): Custom decision thresholds. Defaults:
                                                - revenue_growth_good_pct: 5.0
                                                - revenue_growth_bad_pct: -5.0
                                                - debt_to_equity_good: 1.0
                                                - debt_to_equity_bad: 2.0
                                                - sentiment_good: 0.15
                                                - sentiment_bad: -0.15
                                                - pe_low: 15.0
                                                - pe_high: 40.0
    
    Returns:
        Dict[str, Any]: A dictionary containing:
            - verdict (str): Investment decision - "BUY" (score >= 2),
                            "SELL" (score <= -2), or "HOLD" (score -1 to 1)
            - score (int): Net score (positive_signals - negative_signals)
            - pos_signals (int): Count of positive indicators
            - neg_signals (int): Count of negative indicators
            - reasons (List[str]): Detailed list of factors influencing the decision
    
    Scoring Rules:
        Positive factors (+1 each):
            - Positive net income
            - Revenue growth > revenue_growth_good_pct
            - Debt-to-equity < debt_to_equity_good
            - Sentiment score > sentiment_good
            - P/E ratio < pe_low (undervalued)
        
        Negative factors (-1 each):
            - Negative net income
            - Revenue decline < revenue_growth_bad_pct
            - Debt-to-equity > debt_to_equity_bad
            - Sentiment score < sentiment_bad
            - P/E ratio > pe_high (overvalued)
    
    Example:
        decision = decide_action(metrics, 0.3)
        print(f"Verdict: {decision['verdict']}")  # Output: "BUY"
        print(f"Reasons: {decision['reasons']}")  # List of factors
    """
    if thresholds is None:
        thresholds = {
            "revenue_growth_good_pct": 5.0,
            "revenue_growth_bad_pct": -5.0,
            "debt_to_equity_good": 1.0,
            "debt_to_equity_bad": 2.0,
            "sentiment_good": 0.15,
            "sentiment_bad": -0.15,
            "pe_low": 15.0,
            "pe_high": 40.0
        }

    pos = 0
    neg = 0
    reasons: List[str] = []

    # Net income
    ni = metrics.get("net_income")
    if ni is not None:
        if ni > 0:
            pos += 1
            reasons.append("positive net income")
        else:
            neg += 1
            reasons.append("negative net income")
    else:
        reasons.append("net income unavailable")

    # Revenue growth
    rg = metrics.get("revenue_growth_pct")
    if rg is not None:
        if rg > thresholds["revenue_growth_good_pct"]:
            pos += 1
            reasons.append(f"revenue growth {rg:.1f}%")
        elif rg < thresholds["revenue_growth_bad_pct"]:
            neg += 1
            reasons.append(f"revenue decline {rg:.1f}%")
        else:
            reasons.append(f"muted growth {rg:.1f}%")
    else:
        reasons.append("revenue growth unavailable")

    # Debt to equity
    d2e = metrics.get("debt_to_equity")
    if d2e is not None:
        if d2e < thresholds["debt_to_equity_good"]:
            pos += 1
            reasons.append(f"low leverage d/e {d2e:.2f}")
        elif d2e > thresholds["debt_to_equity_bad"]:
            neg += 1
            reasons.append(f"high leverage d/e {d2e:.2f}")
        else:
            reasons.append(f"moderate leverage d/e {d2e:.2f}")
    else:
        reasons.append("debt/equity unavailable")

    # Sentiment
    if sentiment_score > thresholds["sentiment_good"]:
        pos += 1
        reasons.append(f"positive sentiment {sentiment_score:.2f}")
    elif sentiment_score < thresholds["sentiment_bad"]:
        neg += 1
        reasons.append(f"negative sentiment {sentiment_score:.2f}")
    else:
        reasons.append(f"neutral sentiment {sentiment_score:.2f}")

    # PE ratio
    pe = metrics.get("trailing_pe") or metrics.get("forward_pe")
    if pe is not None:
        try:
            pe_val = float(pe)
            if pe_val > 0:
                if pe_val < thresholds["pe_low"]:
                    pos += 1
                    reasons.append(f"low PE {pe_val:.1f}")
                elif pe_val > thresholds["pe_high"]:
                    neg += 1
                    reasons.append(f"high PE {pe_val:.1f}")
                else:
                    reasons.append(f"PE in range {pe_val:.1f}")
            else:
                reasons.append("PE invalid")
        except (ValueError, TypeError):
            reasons.append("PE parsing failed")
    else:
        reasons.append("PE unavailable")

    # Decision logic
    if pos == 0 and neg == 0:
        verdict = "HOLD"
        score = 0
    else:
        score = pos - neg
        if score >= 2:
            verdict = "BUY"
        elif score <= -2:
            verdict = "SELL"
        else:
            verdict = "HOLD"

    return {
        "verdict": verdict,
        "score": score,
        "pos_signals": pos,
        "neg_signals": neg,
        "reasons": reasons,
    }
