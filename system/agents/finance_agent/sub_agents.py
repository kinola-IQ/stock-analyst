"""module to configure sub agents"""

from google.adk.agents import Agent
from google.adk.tools import google_search, FunctionTool
from langchain_experimental.tools import PythonREPLTool

from ...utility import model
from ..finance_agent.tools import (
    save_findings,
    save_plot,
    read_skills,
    get_guardrails
)

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

        Use the google_search tool to find all recent relevant facts about:
        {company}

        use the `save_findings` tool to store the full research results in memory.
        Return concise findings with citations only. Do not add filler, speculation, or unrelated commentary.
        
        """.strip(),
        tools=[google_search, FunctionTool(save_findings)],
        # The result of this agent will be stored in the session state
        #  with this key.
        output_key="research_findings",
        description="Agent focused on company research: gathers recent facts via search, stores findings, and returns concise, citation-backed summaries."
    )

# subagent for conducting analysis
def coding_agent() -> Agent:
    """Create a coding agent for added ticker based analysis.

    The agent uses pythonRepl to run python codes performing analysis requested for by the root agent.

    Returns:
        Agent: A configured coding sub agent with programming capability. The agent
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
        name="AnalyticsAgent",
        model=AGENT_MODEL,
        instruction=
        f"""
        You are a senior Python engineer.

        Always:

        1. Read the skill first using the `read_skills` tool.
        2. Follow every rule inside it.
        3. Produce executable Python code.
        4. Execute the code using Python REPL when needed.
        5. Explain the result.
        6. Save the `plot` using the `save_plot` tool when needed.
        
        You MUST obey following guardrails below:
        {get_guardrails()}
        Generate and execute Python code.
        """.strip(),
        tools=[PythonREPLTool, FunctionTool(read_skills), FunctionTool(save_plot)],
        # The result of this agent will be stored in the session state
        #  with this key.
        output_key="analytics_results",
        description="Agent specialized in analytics workflows: reads skills, executes Python code, and saves plots."
)