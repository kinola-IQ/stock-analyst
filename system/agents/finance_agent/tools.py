""" module to configure agent tools"""

from google.adk.agents import Agent
from google.adk.models.google_llm import Gemini
from google.adk.tools import google_search
from typing import Dict, Any, List, Optional, Tuple 
import datetime 
import json

# custom modules
from ...utility.utils import retry_config
from ...utility.logger import logger
from .tools_config.ticker_tools import (
    fetch_company_data,
    extract_financial_metrics,
    score_news_sentiment,
    generate_analysis_script,
    decide_action)

# Research agent for websearching
def research_agent() -> Agent:
    """
    useful for employing a research agent that uses google search tool\
          to find relevant information on a company.
    """
    return Agent(
        name="ResearchAgent",
        model=Gemini(
            model="gemini-2.5-flash-lite",
            retry_options=retry_config
        ),
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
    """useful for logging progress using the configured logger."""
    return logger.info(message)


# Convenience wrapper that ties everything together
def analyse_ticker(symbol: str) -> Dict[str, Any]:
    """
    High-level wrapper that runs the a full research pipeline and returns a structured result.
    usefull for executing the following steps in order:
    1) fetching company data via yfinance
    2) extracting financial metrics
    3) scoring news sentiment
    4) generating a Python analysis script string
    5) running a lightweight rule-based decision (buy/sell/hold)
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
