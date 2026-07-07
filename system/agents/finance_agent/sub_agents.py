"""module to configure sub agents"""

from google.adk.agents import Agent
from google.adk.tools import google_search, FunctionTool
from langchain_experimental.tools import PythonREPLTool

from ...utility import model
from ..finance_agent.tools import (
    research_agent,
    save_findings,
    save_plot,
    read_skills,
    get_guardrails,
    get_plots_dir
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
        3. Inspect the raw financial statement structure before computing metrics.
        4. Preserve or recover the relevant row labels and use fallback values from the ticker info payload when statement rows are missing.
        5. Produce executable Python code.
        6. Execute the code using Python REPL when needed.
        7. Explain the result.
        8. Save the `plot` using the `save_plot` tool when needed.
        9. Report which metrics you recovered and which remain unavailable.
        
        You MUST obey following guardrails below:
        {get_guardrails()}
        Generate and execute Python code.
        """.strip(),
        tools=[PythonREPLTool, FunctionTool(read_skills), FunctionTool(save_plot), FunctionTool(get_plots_dir)],
        # The result of this agent will be stored in the session state
        #  with this key.
        output_key="analytics_results",
        description="Agent specialized in analytics workflows: reads skills, executes Python code, and saves plots."
)