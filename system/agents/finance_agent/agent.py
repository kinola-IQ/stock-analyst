"""module to configure the main root agent"""

# from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool


# custom modules
from ..finance_agent.tools import (

    analyse_ticker,
)
from ..finance_agent.sub_agents import research_agent, coding_agent


# model serving
from ...utility import model


def root_agent() -> LlmAgent:
    """Create the root Research Coordinator agent that orchestrates stock analysis.
    
    This function initializes and returns a root LLM agent that coordinates the
    entire research and analysis workflow. The agent acts as a Research Coordinator,
    making autonomous decisions about research strategy, invoking appropriate tools,
    and synthesizing findings into actionable investment recommendations.
    
    The agent has access to four main tools:
    1. ResearchAgent - A specialized web search agent for gathering company information
    2. log_tool - For recording progress, milestones, and debugging information
    3. analyse_ticker - For running comprehensive quantitative financial analysis
    4. save_summary - For persisting research findings and summaries
    
    The agent is instructed to:
    - Maintain autonomy in choosing research approach and depth
    - Use the research agent to gather qualitative information
    - Use analyse_ticker to get quantitative financial metrics
    - Synthesize both into clear, factual summaries
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

    # guiding principles for model behaviour
    instruction_lines = [
        "You are a Research Coordinator responsible for independent, accurate research on the provided ticker.",
        "Maintain autonomy: choose the research approach, order of steps, and depth of investigation needed to meet the objective.",
        "Use the ResearchAgent sub agent to gather relevant primary and secondary information about the ticker.",
        "Use the CodingAgent sub agent to perform analysis required if available tools return null or incomplete values",
        "Invoke the analyse_ticker tool to produce a quantitative financial analysis and key metrics.",
        "Synthesize research and analysis into a single, clear final summary for the user, highlighting conclusions and any important caveats.",
        "If data gaps or ambiguous results remain, note them explicitly in the final summary and recommend next steps.",
        "Prioritize accuracy, transparency, and reproducibility; avoid making unsupported claims or speculative forecasts."
    ]

    instruction = "\n".join(instruction_lines)

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
        tools=[FunctionTool(analyse_ticker),],
        output_key="final_summary",
        sub_agents=[research_agent(), coding_agent()]
    )
