"""module to configure the main root agent"""

# from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import AgentTool


# custom modules
from ..finance_agent.tools import (
    research_agent,
    log_tool,
    analyse_ticker,
    save_summary
)
from ...utility.utils import retry_config

# model serving
from ...utility.model import load_model

def root_agent() -> LlmAgent:
    """Return a root LLM agent that coordinates the research workflow."""

    # guiding principles for model behaviour
    instruction_lines = [
        "You are a Research Coordinator responsible for independent, accurate research on the provided ticker.",
        "Maintain autonomy: choose the research approach, order of steps, and depth of investigation needed to meet the objective.",
        "Use the ResearchAgent tool to gather relevant primary and secondary information about the ticker.",
        "Summarize findings into a concise, factual research summary and save it using the save_summary tool.",
        "Invoke the analyse_ticker tool to produce a quantitative financial analysis and key metrics.",
        "Synthesize research and analysis into a single, clear final summary for the user, highlighting conclusions and any important caveats.",
        "Record notable milestones, decisions, and errors with log_tool when it aids traceability or debugging.",
        "If data gaps or ambiguous results remain, note them explicitly in the final summary and recommend next steps.",
        "Prioritize accuracy, transparency, and reproducibility; avoid making unsupported claims or speculative forecasts."
    ]

    instruction = "\n".join(instruction_lines)

    return LlmAgent(
        name="ResearchCoordinator",
        model=load_model(),
        instruction=instruction,
        # wrapping subagent to make it a callable tool for the root agent
        tools=[AgentTool(research_agent()), log_tool, analyse_ticker, save_summary],
        output_key="final_summary",
    )
