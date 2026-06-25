""" module to configure agent tools"""

from google.adk.agents import Agent
from google.adk.tools import google_search
from typing import Dict, Any

# custom modules
# from ...utility.utils import retry_config
from ...utility.logger import logger
from .tools_config.ticker_tools import (
    fetch_company_data,
    extract_financial_metrics,
    score_news_sentiment,
    generate_analysis_script,
    decide_action)
from ...utility import model



# Research agent for websearching
def research_agent() -> Agent:
    """Create a research agent for web-based company investigation.

    The agent uses Google Search to gather 2–3 concise, relevant facts about
    the specified company, event, milestone, or market development, and returns
    them with citations.

    Args:
        company (str): The research topic. Use a short, specific phrase such as
            a company name, ticker symbol, product name, or recent business event.

    Returns:
        Agent: A configured research agent with Google Search access. The agent
        is intended to be invoked by the root coordinator agent.

    Raises:
        RuntimeError: If the model cannot be loaded or required API keys are missing.
    """
    try:
        AGENT_MODEL = model.get_model()
    except Exception as exc:
        # Surface a clearer error when model is not available
        raise RuntimeError(
            "LLM model not loaded; ensure API KEY is set and load_model() succeeded"
        ) from exc

    return Agent(
        name="ResearchAgent",
        model=AGENT_MODEL,
        instruction=
        """
        You are a specialized research agent.

        Use the google_search tool to find 2–3 relevant facts about:
        {company}

        Return concise findings with citations only. Do not add filler, speculation, or unrelated commentary.
        """.strip(),
        tools=[google_search],
        # The result of this agent will be stored in the session state
        #  with this key.
        output_key="research_findings"
    )


# Convenience wrapper that ties everything together
def analyse_ticker(symbol: str) -> Dict[str, Any]:
    """Execute a comprehensive financial analysis pipeline for a given stock ticker.
    
    This is a high-level wrapper function that orchestrates a complete research and
    analysis workflow for a stock. It fetches current company data, extracts financial
    metrics, analyzes news sentiment, generates an analysis script, and produces a
    buy/sell/hold verdict.
    
    The analysis steps are executed in sequence:
    1. Fetch company data and financials from yfinance
    2. Extract key financial metrics (P/E ratios, revenue, debt, etc.)
    3. Retrieve and analyze recent news headlines for sentiment
    4. Generate a Python analysis script with the findings
    5. Apply decision rules to produce a buy/sell/hold recommendation
    
    Args:
        symbol (str): The stock ticker symbol to analyze (e.g., "AAPL", "MSFT", "GOOGL").
                     Will be converted to uppercase. Must be a valid ticker symbol
                     recognized by yfinance.
    
    Returns:
        Dict[str, Any]: A comprehensive analysis result containing:
            - symbol (str): The stock ticker symbol in uppercase
            - company (str): The company name or long name
            - metrics (Dict): Financial metrics including:
                * current_price (float): Current stock price
                * trailing_pe (float): Trailing price-to-earnings ratio
                * forward_pe (float): Forward P/E ratio
                * market_cap (float): Market capitalization
                * revenue (float): Annual revenue
                * net_income (float): Annual net income
                * revenue_growth_pct (float): Year-over-year revenue growth percentage
                * total_debt (float): Total company debt
                * total_equity (float): Total stockholder equity
                * debt_to_equity (float): Debt-to-equity ratio
            - headlines (List[str]): Recent news headlines for the company
            - sentiment_score (float): Aggregate sentiment score (-1.0 to 1.0)
                                      where positive indicates bullish sentiment
            - verdict (str): Investment decision: "BUY", "SELL", or "HOLD"
            - verdict_details (Dict): Detailed reasoning for the decision including:
                * score (int): Net score from decision rules
                * reasons (List[str]): List of factors that influenced the decision
                * recommendation (str): Full recommendation text
            - script (str): Generated Python script for further analysis
    
    Raises:
        Exception: May raise various exceptions if yfinance fails to fetch data,
                  if the ticker symbol is invalid, or if network issues occur.
                  These are logged but may propagate up.
    
    Example:
        result = analyse_ticker("AAPL")
        print(f"Verdict for {result['symbol']}: {result['verdict']}")
        print(f"Current Price: ${result['metrics']['current_price']}")
        print(f"Sentiment: {result['sentiment_score']}")
    """
    try:
        data = fetch_company_data(symbol)
    except Exception as exc:
        return {
            "symbol": symbol.upper(),
            "error": f"Fetch failed: {exc}"
        }

    metrics = extract_financial_metrics(data)
    headlines = []
    for item in data.get("news", []):
        if isinstance(item, dict):
            headlines.append(item.get("title", ""))
        elif isinstance(item, str):
            headlines.append(item)
        else:
            headlines.append(str(item))

    sentiment = score_news_sentiment(headlines)
    script = generate_analysis_script(symbol, metrics, headlines, sentiment,)
    decision = decide_action(metrics, sentiment, script)
    result = {
        "symbol": symbol.upper(),
        "company": data.get("company"),
        "metrics": metrics,
        "headlines": headlines,
        "sentiment_score": sentiment,
        "verdict": decision["verdict"],
        "verdict_details": decision,
        "script": script
    }
    return result


# save summary of search results
research_result = []


def save_findings(findings: str) -> str:
    """Save the research findings to persistent storage.
    
    This tool is useful for storing findings from the research sub agent. it's analysis, and conclusions
    in a structured format that can be retrieved later.
    
    Args:
        findings (str): The research text to save. Should be a comprehensive
                      that that includes the key findings, citations, analysis results, investment
                      verdict, and any relevant caveats or recommendations.
    
    Returns:
        str: A status message indicating success or failure.
             - returns 'saved' if the findingd was appended to storage successfully.
             - returns 'failed: <error>' if an exception occurs.
    
    """
    try:
        research_result.append(
            {'findings': findings}
            )
        return "saved"
    except Exception as err:
        return f"failed: {err}"