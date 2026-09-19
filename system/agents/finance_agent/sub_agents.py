"""module to configure sub agents"""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from langchain_experimental.tools import PythonREPLTool
from langchain_community.tools import DuckDuckGoSearchRun

from ...utility import model
from .prompts import foreign_stocks_prompt, local_stocks_prompt
from .data_tools import read_skills
from ..finance_agent.market_data_tools import analyse_ticker, financial_data_tool, macro_context_tool


# Research agent for websearching
def foreign_stocks_agent() -> Agent:
    """Create a sub-agent for foreign company investigation.

    The agent extracts financial information about non-african foreign stocks.

    Returns:
        Agent: A configured sub agent with yfinance access. The agent
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
        name="ForeignStocksAgent",
        model=AGENT_MODEL,
        instruction=foreign_stocks_prompt(),

        tools=[FunctionTool(analyse_ticker), FunctionTool(DuckDuckGoSearchRun)]
        # The result of this agent will be stored in the session state
        #  with this key.
        output_key="foreign_results",
         description="Agent focused on researching foreign stocks on yfinance"
)

# subagent for conducting analysis
def local_stocks_agent() -> Agent:
    """Create a local stocks agent for analyzing Nigerian and African stocks.

    The agent uses pythonRepl to run python codes performing analysis requested for by the root agent.

    Returns:
        Agent: A configured local stocks sub agent with programming capability. The agent
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
        name="LocalStocksAgent",
        model=AGENT_MODEL,
        instruction=local_stocks_prompt(),
        tools=[
            FunctionTool(PythonREPLTool),
            FunctionTool(financial_data_tool),
            FunctionTool(macro_context_tool),
            FunctionTool(read_skills)]
        # The result of this agent will be stored in the session state
        #  with this key.
        output_key="local_results",
        description="Agent focused on local nigerian and african stocks."
)