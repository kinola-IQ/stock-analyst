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
    """Create a Research Agent for gathering company information via web search.
    
    This agent uses the Google Search tool to find relevant information about
    a given company or ticker. It searches for and returns 2-3 key pieces of
    information with proper citations.
    
    Returns:
        Agent: A configured Research Agent instance with Google Search capability
               that can be used as a tool by the root coordinator agent.
    
    Raises:
        RuntimeError: If the LLM model cannot be loaded or API keys are not set.
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
        instruction="""
        You are a specialized research agent.
        Your only job is to use the google_search tool\
              to find 2-3 pieces of relevant information\
                on the given topic and present the findings with citations.
        Be concise and to the point in your findings.""",
        tools=[google_search],
        # The result of this agent will be stored in the session state
        #  with this key.
        output_key="research_findings"
    )


# logger tool for logging progress
def log_tool(message: str):
    """Log a progress message using the configured logger.
    
    This tool is useful for recording progress, milestones, debugging information,
    or important events during the research and analysis workflow. Messages are
    logged at INFO level with timestamps for traceability.
    
    Args:
        message (str): The message to log. Should be descriptive and concise,
                      including context about what action or milestone is being recorded.
    
    Returns:
        None
    
    Example:
        log_tool("Starting analysis for AAPL")
        log_tool("Successfully fetched company financials")
    """
    return logger.info(message)


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
    data = fetch_company_data(symbol)
    metrics = extract_financial_metrics(data)
    headlines = [n.get("title", "") for n in data.get("news", [])]
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
summary_result = []


def save_summary(summary: str):
    """Save a research summary to persistent storage.
    
    This tool is useful for storing findings from research, analysis, and conclusions
    in a structured format that can be retrieved later. Each summary is saved with
    a timestamp and index for easy retrieval.
    
    Args:
        summary (str): The research summary text to save. Should be a comprehensive
                      summary that includes key findings, analysis results, investment
                      verdict, and any relevant caveats or recommendations.
    
    Returns:
        None: The summary is appended to the internal storage list.
    
    Example:
        save_summary("AAPL Analysis: Strong fundamentals with positive sentiment. Verdict: BUY")
    """
    return summary_result.append(
        {'summary': summary}
    )