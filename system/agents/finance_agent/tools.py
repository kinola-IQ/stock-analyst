""" module to configure agent tools"""
from pathlib import Path
from typing import Dict, Any

from google.adk.agents import Agent
from google.adk.tools import google_search, FunctionTool

# custom modules
# from ...utility.utils import retry_config
from ...utility import model
from ...utility.logger import logger
from ...utility.constants import ASSETS_DIR, SYSTEMS_DIR
from .tools_config.ticker_tools import (
    fetch_company_data,
    extract_financial_metrics,
    score_news_sentiment,
    decide_action)



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
    decision = decide_action(metrics, sentiment)

    # save history plot to assets folder
    try:
        history = data.get("history", {}).reset_index()
        history.columns = [col.lower() for col in history.columns]
        history = history.set_index('date')
        # Save the plot to the assets folder
        plot_path = ASSETS_DIR / "plots" / f"{symbol.upper()}_stock_price_history.png"
        history[['open', 'high', 'low', 'close']].plot(
            title=f"{symbol.upper()} Stock Price History",
            figsize=(12, 6)
        ).get_figure().savefig(plot_path)
        logger.info("Saved stock price history plot to: %s", plot_path)
    except Exception as exc:
        logger.warning("Failed to generate plot: %s", exc)

    result = {
        "symbol": symbol.upper(),
        "company": data.get("company"),
        "metrics": metrics,
        "headlines": headlines,
        "sentiment_score": sentiment,
        "verdict": decision["verdict"],
        "verdict_details": decision,
        "plot_path": str(plot_path)
    }
    return result


# save results to persistent storage for later retrieval
research_result: Dict[str, Any] = {}

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
        research_result['findings'] = findings
        return "saved"
    except Exception as err:
        return f"failed: {err}"

def save_plot(plot: str) -> str:
    """Save the plot path to persistent storage.
    
    This tool is useful for storing the directory of the plot generated so that it can be retrieved later.
    
    Args:
        plot (str): The plot path to save to persistent storage.
    
    Returns:
        str: A status message indicating success or failure.
             - returns 'saved' if the plot was appended to storage successfully.
             - returns 'failed: <error>' if an exception occurs.
    
    """
    try:
        research_result['plot'] = plot
        return "saved"
    except Exception as err:
        return f"failed: {err}"

    
# accessing skills

def read_skills(skill: str) -> str:
    """
    Extract instructions that serve as guiding skills.

    Args:
        skill (str): The skill name to retrieve.
            Available skills include:
            - visualizations: for generating plots and visualizations of stock price and time series data
            - financial_analysis: for performing quantitative financial analysis and key metrics calculations
    Raises:
        ValueError: May raise value error exception if a non-existent skill is requested.
        These are logged but may propagate up.
    Returns:
        str: The full text of the requested skill instructions.
    """
    if skill.lower() not in ['visualizations','financial_analysis', 'standard guide']:
        raise ValueError('invalid input, available skills are:' \
                                        'visualizations ' \
                                        'financial_analysis')
    path = SYSTEMS_DIR / "agents" / "finance_agent" / "skills" / f"{skill.lower()}.md"
    return path.read_text(encoding="utf-8")


# accessing external files
def get_guardrails() -> str:
    return read_skills('standard guide')

def get_plots_dir() -> Path:
    """
    Return the path to the plots directory.
    This function provides a convenient way to access the directory where generated plots are stored.
    Returns:
        Path: The path to the plots directory.
    """
    return ASSETS_DIR / "plots"

# clear up assets and research results to avoid stale data
def delete_assets() -> None:
    """Delete only files inside subfolders of the assets folder, preserving empty subfolders."""
    assets_dir = Path(__file__).resolve().parents[3] / "assets"
    for subfolder in assets_dir.iterdir():
        if subfolder.is_dir():
            for item in subfolder.iterdir():
                if item.is_file():
                    item.unlink()
                else:
                    logger.warning("Skipping non-file item: %s", item)
                    pass
    logger.info("Cleared files inside subfolders of assets, preserving folder structure.")

def clear_research_results() -> None:
    """Clear the research results dictionary."""
    global research_result
    if not research_result:
        logger.info("Research results already empty.")
        return
    research_result.clear()
    logger.info("Cleared research results.")