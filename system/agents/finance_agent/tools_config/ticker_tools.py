"""
ticker_tools.py

Separated functions for:
1) fetching company data via yfinance
2) extracting financial metrics
3) scoring news sentiment
4) generating a Python analysis script string
5) running a lightweight rule-based decision (buy/sell/hold)
"""

from typing import Dict, Any, List, Optional, Tuple
import datetime
import json
import yfinance as yf

# Lazy imports inside functions to fail gracefully if not installed
def fetch_company_data(symbol: str, top_n_news: int = 5, history_period: str = "1y") -> Dict[str, Any]:
    """
    Resolve company name and pull financials and recent news using yfinance.

    Returns a dict with keys:
      - symbol, company, info, financials, balance_sheet, cashflow, news (list), history (DataFrame or None)
    """
    ticker = yf.Ticker(symbol)
    info = {}
    financials = None
    balance_sheet = None
    cashflow = None
    news = []
    history = None

    # Info
    try:
        info = ticker.info or {}
    except Exception:
        info = {}

    company = info.get("longName") or info.get("shortName") or symbol.upper()

    # Financial statements
    def _safe_get(attr):
        try:
            val = getattr(ticker, attr)
            # yfinance returns DataFrame-like objects; convert to pandas if present
            return val if val is not None else None
        except Exception:
            return None

    financials = _safe_get("financials")
    balance_sheet = _safe_get("balance_sheet")
    cashflow = _safe_get("cashflow")

    # News
    try:
        raw_news = ticker.news or []
        for n in raw_news[:top_n_news]:
            title = n.get("title") or n.get("headline") or ""
            link = n.get("link") or n.get("link")
            publisher = n.get("publisher") or n.get("source") or ""
            ts = n.get("providerPublishTime")
            if ts:
                try:
                    ts = datetime.datetime.fromtimestamp(int(ts)).isoformat()
                except Exception:
                    pass
            news.append({"title": title, "link": link, "publisher": publisher, "time": ts})
    except Exception:
        news = []

    # History
    try:
        history = ticker.history(period=history_period)
    except Exception:
        history = None

    return {
        "symbol": symbol.upper(),
        "company": company,
        "info": info,
        "financials": financials,
        "balance_sheet": balance_sheet,
        "cashflow": cashflow,
        "news": news,
        "history": history
    }


def extract_financial_metrics(data: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """
    Extract key financial metrics and compute simple growth / leverage measures.

    Input: dict returned by fetch_company_data
    Output: dict with numeric metrics (or None when unavailable)
      - current_price, trailing_pe, forward_pe, market_cap
      - revenue, net_income, revenue_growth_pct
      - total_debt, total_equity, debt_to_equity
    """
    info = data.get("info", {}) or {}
    fin = data.get("financials")
    bal = data.get("balance_sheet")
    metrics: Dict[str, Optional[float]] = {
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

    # Basic info
    try:
        # price from history if available
        hist = data.get("history")
        if hist is not None and hasattr(hist, "empty") and not hist.empty:
            metrics["current_price"] = float(hist["Close"].iloc[-1])
        else:
            metrics["current_price"] = float(info.get("currentPrice")) if info.get("currentPrice") else None
    except Exception:
        metrics["current_price"] = None

    metrics["trailing_pe"] = info.get("trailingPE")
    metrics["forward_pe"] = info.get("forwardPE")
    metrics["market_cap"] = info.get("marketCap")

    # Financials: revenue and net income (most recent column)
    try:
        if fin is not None and hasattr(fin, "empty") and not fin.empty:
            # yfinance DataFrame index names vary; try common labels
            def _get_row(df, candidates):
                for c in candidates:
                    if c in df.index:
                        return df.loc[c].iloc[0]
                return None

            rev_candidates = ["Total Revenue", "Revenue", "Revenues"]
            net_candidates = ["Net Income", "Net Income Applicable To Common Shares", "NetIncomeLoss"]

            rev = _get_row(fin, rev_candidates)
            net = _get_row(fin, net_candidates)
            metrics["revenue"] = float(rev) if rev is not None else None
            metrics["net_income"] = float(net) if net is not None else None

            # revenue growth: compare first two columns if present
            try:
                if fin.shape[1] >= 2:
                    # most recent column index 0, previous 1
                    rev_new = _get_row(fin, rev_candidates)
                    rev_old = None
                    for c in rev_candidates:
                        if c in fin.index:
                            if fin.shape[1] >= 2:
                                rev_old = fin.loc[c].iloc[1]
                            break
                    if rev_new is not None and rev_old not in (None, 0):
                        metrics["revenue_growth_pct"] = float((rev_new - rev_old) / abs(rev_old)) * 100.0
            except Exception:
                metrics["revenue_growth_pct"] = None
    except Exception:
        pass

    # Balance sheet: debt and equity
    try:
        if bal is not None and hasattr(bal, "empty") and not bal.empty:
            # common labels
            debt_candidates = ["Long Term Debt", "Total Debt", "Long-term Debt"]
            equity_candidates = ["Total Stockholder Equity", "Total Stockholders' Equity", "Total Equity", "Stockholders Equity"]

            def _get_val(df, candidates):
                for c in candidates:
                    if c in df.index:
                        return df.loc[c].iloc[0]
                return None

            total_debt = _get_val(bal, debt_candidates)
            total_equity = _get_val(bal, equity_candidates)
            metrics["total_debt"] = float(total_debt) if total_debt is not None else None
            metrics["total_equity"] = float(total_equity) if total_equity is not None else None
            if metrics["total_debt"] is not None and metrics["total_equity"] not in (None, 0):
                metrics["debt_to_equity"] = float(metrics["total_debt"]) / float(metrics["total_equity"])
            else:
                metrics["debt_to_equity"] = None
    except Exception:
        pass

    return metrics


def score_news_sentiment(headlines: List[str]) -> float:
    """
    Score news sentiment using vaderSentiment if available; fallback to a tiny wordlist.

    Returns average compound score in range [-1, 1].
    """
    # Try vader
    try:
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        analyzer = SentimentIntensityAnalyzer()
        if not headlines:
            return 0.0
        scores = []
        for h in headlines:
            if not h:
                continue
            s = analyzer.polarity_scores(h).get("compound", 0.0)
            scores.append(s)
        return float(sum(scores) / len(scores)) if scores else 0.0
    except Exception:
        # Fallback tiny lexicon
        POS = {"good", "great", "positive", "beat", "beats", "up", "gain", "gains", "growth", "strong", "profit", "outperform"}
        NEG = {"bad", "worse", "miss", "missed", "down", "loss", "losses", "weak", "decline", "fall", "cut", "warn"}
        if not headlines:
            return 0.0
        total = 0.0
        count = 0
        for h in headlines:
            words = set(w.strip(".,!?:;()[]\"'").lower() for w in h.split())
            pos = len(words & POS)
            neg = len(words & NEG)
            if pos + neg == 0:
                continue
            total += (pos - neg) / (pos + neg)
            count += 1
        return float(total / count) if count else 0.0


def generate_analysis_script(symbol: str,
                             metrics: Dict[str, Any],
                             headlines: List[str],
                             sentiment_score: float,
                             filename: Optional[str] = None) -> str:
    """
    Generate a Python analysis script as a string.

    The script is a readable starting point that re-fetches data and prints key metrics.
    """
    if filename is None:
        filename = f"{symbol.upper()}_analysis.py"

    # Build a compact script string
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
        f"print('Generated metrics snapshot:')",
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
    script_text = "\n".join(script_lines)


    return script_text


def decide_action(metrics: Dict[str, Any],
                  sentiment_score: float,
                  script_text: str,
                  thresholds: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """
    Lightweight rule-based decision to return BUY / SELL / HOLD.

    Returns dict with:
      - verdict: "BUY"|"SELL"|"HOLD"
      - score: numeric summary (pos_signals - neg_signals)
      - reasons: list of strings
      - script: the generated script_text (for convenience)
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

    # Net income positive
    ni = metrics.get("net_income")
    if ni is not None:
        if ni > 0:
            pos += 1
            reasons.append("positive net income")
        else:
            neg += 1
            reasons.append("negative net income or not reported")
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
            reasons.append(f"revenue growth muted {rg:.1f}%")
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
        reasons.append(f"positive news sentiment {sentiment_score:.2f}")
    elif sentiment_score < thresholds["sentiment_bad"]:
        neg += 1
        reasons.append(f"negative news sentiment {sentiment_score:.2f}")
    else:
        reasons.append(f"neutral news sentiment {sentiment_score:.2f}")

    # PE heuristic
    pe = metrics.get("trailing_pe") or metrics.get("forward_pe")
    if pe is not None:
        try:
            pe_val = float(pe)
            if pe_val < thresholds["pe_low"]:
                pos += 1
                reasons.append(f"low PE {pe_val:.1f}")
            elif pe_val > thresholds["pe_high"]:
                neg += 1
                reasons.append(f"high PE {pe_val:.1f}")
            else:
                reasons.append(f"PE in range {pe_val:.1f}")
        except Exception:
            reasons.append("PE parsing error")
    else:
        reasons.append("PE unavailable")

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
