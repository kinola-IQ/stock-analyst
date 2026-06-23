"""Tools for stock analysis: fetch data, extract metrics, score sentiment, and decide buy/sell/hold."""

from typing import Dict, Any, List, Optional
import datetime
import json
import logging
import yfinance as yf
from system.utility.utils import retry_on_exception

logger = logging.getLogger(__name__)


def _safe_get_ticker_attr(ticker, attr: str):
    """Safely get ticker attribute with error handling."""
    try:
        return getattr(ticker, attr) or None
    except Exception:
        return None

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
    metrics = {"current_price": None, "trailing_pe": None, "forward_pe": None, "market_cap": None}
    info = data.get("info", {}) or {}
    
    try:
        hist = data.get("history")
        if hist is not None and hasattr(hist, "empty") and not hist.empty:
            metrics["current_price"] = float(hist["Close"].iloc[-1])
        elif info.get("currentPrice"):
            metrics["current_price"] = float(info.get("currentPrice"))
    except Exception:
        pass
    
    metrics["trailing_pe"] = _first_numeric(info.get("trailingPE"))
    metrics["forward_pe"] = _first_numeric(info.get("forwardPE"))
    metrics["market_cap"] = _first_numeric(info.get("marketCap"))
    metrics["total_debt"] = _first_numeric(info.get("totalDebt"), info.get("debt"))
    metrics["total_equity"] = _first_numeric(info.get("totalStockholderEquity"), info.get("totalEquity"))
    metrics["debt_to_equity"] = _first_numeric(info.get("debtToEquity"))
    return metrics


def _extract_revenue_metrics(fin) -> Dict[str, Optional[float]]:
    """Extract revenue-related metrics."""
    metrics = {"revenue": None, "net_income": None, "revenue_growth_pct": None}
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
                        rev_new = float(row.iloc[-1]) if row.iloc[-1] is not None else None
                        rev_old = float(row.iloc[-2]) if row.iloc[-2] is not None else None
                        if rev_new is not None and rev_old not in (None, 0):
                            metrics["revenue_growth_pct"] = ((rev_new - rev_old) / abs(rev_old)) * 100.0
                    break
    except Exception as e:
        logger.debug(f"Revenue extraction failed: {e}")
    
    return metrics


def _extract_debt_metrics(bal) -> Dict[str, Optional[float]]:
    """Extract debt and equity metrics."""
    metrics = {"total_debt": None, "total_equity": None, "debt_to_equity": None}
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
    ticker = yf.Ticker(symbol)
    
    # Basic info
    try:
        info = ticker.info or {}
    except Exception:
        info = {}
    
    company = info.get("longName") or info.get("shortName") or symbol.upper()
    
    # Financial statements
    financials = _safe_get_ticker_attr(ticker, "financials")
    balance_sheet = _safe_get_ticker_attr(ticker, "balance_sheet")
    
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


def extract_financial_metrics(data: Dict[str, Any]) -> Dict[str, Optional[float]]:
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
    metrics = {
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
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        analyzer = SentimentIntensityAnalyzer()
        scores = [analyzer.polarity_scores(h).get("compound", 0.0) for h in headlines if h]
        return float(sum(scores) / len(scores)) if scores else 0.0
    except ImportError:
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


def generate_analysis_script(symbol: str, metrics: Dict[str, Any], headlines: List[str],
                             sentiment_score: float, filename: Optional[str] = None) -> str:
    """Generate a Python analysis script with company data and findings.
    
    Creates a complete, executable Python script that documents the analysis
    performed on a stock. The script includes company data, extracted metrics,
    news headlines, sentiment scores, and can be extended with further analysis.
    
    Args:
        symbol (str): The stock ticker symbol (will be uppercase).
        metrics (Dict[str, Any]): Dictionary of extracted financial metrics.
        headlines (List[str]): List of news headlines to include in the script.
        sentiment_score (float): The calculated sentiment score (-1.0 to 1.0).
        filename (Optional[str]): Name for the generated script file.
                                 Defaults to "{SYMBOL}_analysis.py".
    
    Returns:
        str: A complete Python script as a multi-line string that:
             - Imports necessary libraries
             - Defines the ticker symbol
             - Fetches company info
             - Prints current stock price
             - Outputs metrics snapshot
             - Lists recent headlines
             - Displays sentiment score
             - Provides template for further analysis
    
    Note:
        The returned script is ready to execute and can be extended with
        additional analysis, visualizations, backtests, or data exports.
    
    Example:
        script = generate_analysis_script("AAPL", metrics, headlines, 0.45)
        # Returns a complete Python script as a string
    """
    if filename is None:
        filename = f"{symbol.upper()}_analysis.py"

    script_lines = [
        "import yfinance as yf",
        "import pandas as pd",
        "from datetime import datetime",
        "",
        f"symbol = {repr(symbol.upper())}",
        "t = yf.Ticker(symbol)",
        "info = t.info",
        "print('Company:', info.get('longName') or info.get('shortName') or symbol)",
        "hist = t.history(period='1y')",
        "print('Latest close:', hist['Close'].iloc[-1] if not hist.empty else info.get('currentPrice'))",
        "print('Generated metrics snapshot:')",
        f"metrics_snapshot = {json.dumps(metrics, default=str)}",
        "print(metrics_snapshot)",
        "",
        "print('Recent headlines:')",
        f"headlines = {json.dumps(headlines)}",
        "for h in headlines:",
        "    print('-', h)",
        "",
        f"print('Sentiment score:', {sentiment_score})",
        "",
        "# Add further analysis: ratio calculations, visualizations, backtests, or export results.",
        "print('Script generated on', datetime.utcnow().isoformat())",
    ]
    return "\n".join(script_lines)


def decide_action(metrics: Dict[str, Any], sentiment_score: float, script_text: str,
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
        script_text (str): Generated analysis script (stored in results for reference).
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
            - script (str): The input script for reference
    
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
        decision = decide_action(metrics, 0.3, script_text)
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
        "script": script_text
    }
