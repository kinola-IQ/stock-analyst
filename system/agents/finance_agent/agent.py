"""module to configure the main root agent"""

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
# from google.adk.tools.google_search_tool import GoogleSearchTool
from langchain_community.tools import DuckDuckGoSearchRun

from system.agents.finance_agent.prompts import root_agent_prompt

# custom modules
from ..finance_agent.sub_agents import foreign_stocks_agent, local_stocks_agent


# model serving
from ...utility import model
from .data_tools import build_and_save_plot

google_search = FunctionTool(DuckDuckGoSearchRun)

def root_agent() -> LlmAgent:
    """Create the root Research Coordinator agent that orchestrates stock analysis.
    
    This function initializes and returns a root LLM agent that coordinates the
    entire research and analysis workflow. The agent acts as a Research Coordinator,
    making autonomous decisions about research strategy, invoking appropriate tools,
    and synthesizing findings into actionable investment recommendations.
    
    The agent has access to tools:
    1. `build_and_save_plot`: A tool for creating and saving plots based on analyzed data.
    2. `google_search`: A tool for performing web searches to gather qualitative information and identify if the stock is foreign or local.
    
    The agent is instructed to:
    - Maintain autonomy in choosing research approach and depth
    - Synthesize information into clear, factual summaries
    - Document any data gaps or ambiguities
    - Prioritize accuracy, transparency, and reproducibility
    
    Returns:
        LlmAgent: A fully configured Research Coordinator agent instance that can:
                 - Receive ticker symbols as input
                 - Execute multi-step research workflows
                 - Call available tools with appropriate parameters
                 - Return structured analysis results with investment verdicts
    
    Raises:
        RuntimeError: If the LLM model cannot be loaded or API keys are not set.
    
    Example:
        agent = root_agent()
        # The agent can then be used in workflows to analyze stocks
    """

    instruction = root_agent_prompt()

    try:
        AGENT_MODEL = model.get_model()
    except Exception as exc:
        # Surface a clearer error when model is not available
        raise RuntimeError(
            "LLM model not loaded; ensure API KEY is set and load_model() succeeded"
        ) from exc

    return LlmAgent(
        name="ResearchCoordinator",
        model=AGENT_MODEL,
        instruction=instruction,
        # wrapping subagent to make it a callable tool for the root agent
        tools=[build_and_save_plot, google_search],
        output_key="root_verdict",
        sub_agents=[foreign_stocks_agent(), local_stocks_agent()],
        description="Coordinator agent that orchestrates sub-agents and produces a final summary."
    )
