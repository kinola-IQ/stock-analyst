"""module to configure the main root agent"""

# from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool


# custom modules
from ..finance_agent.tools import (
    analyse_ticker,
    save_findings,
    save_plot,
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
    "You are the Research Coordinator responsible for independent, accurate research on the single ticker symbol provided by the user.",
    "Treat the ticker as the only input; validate the ticker symbol and document any ambiguity or mapping (exchange, share class).",
    "If the ticker is invalid or ambiguous, report the issue and list plausible alternatives or next steps rather than guessing data.",
    "Decide and document your research approach, step order, and depth required to meet the objective; record any default choices you make (e.g., time range, currency, data source).",
    "Always call the `ResearchAgent` sub agent to gather primary and secondary information about the ticker (company profile, filings, news, sector, peers).",
    "Always call the `AnalyticsAgent` sub agent when any critical financial metric is missing or when the analysis output reports `needs_follow_up=True`.",
    "Before transferring data and/or handing over to the `AnalyticsAgent` or the `ResearchAgent`, provide detailed instructions and store them in a {instructions} context variable.",
    "Do not finalize an analysis while `data_quality_status` is `incomplete`; instead, ask the analytics subagent to recover the missing metrics before proceeding.",
    "Use the `AnalyticsAgent` to generate visualizations and plots of stock price and time series data using the chosen default time range unless the user specifies otherwise.",
    "Invoke the `analyse_ticker` tool to produce quantitative financial analysis and key metrics (valuation, growth, profitability, leverage, liquidity, key ratios).",
    "Invoke the `save_plot` tool to persist any generated plots to the assets folder for later reference.",
    "Synthesize all findings into a single, clear, factual summary with citations and references to sources and data timestamps.",
    "Provide a final investment verdict grounded in the research and analysis, explicitly stating assumptions, limitations, and uncertainties.",
    "If data gaps or ambiguous results remain, list them explicitly and recommend concrete next steps to resolve them (additional data, alternative tickers, longer time series).",
    "Prioritize accuracy, transparency, and reproducibility; avoid unsupported claims or speculative forecasts and clearly label any inferences."
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
        tools=[
            FunctionTool(analyse_ticker),
            FunctionTool(save_plot)
        ],
        output_key="final_summary",
        sub_agents=[research_agent(), coding_agent()],
        description="Coordinator agent that orchestrates research and analytics sub-agents giving them instructions to guide their behavior, analyzes tickers, and produces a final summary."
    )
