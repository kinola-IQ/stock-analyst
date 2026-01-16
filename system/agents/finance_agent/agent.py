"""module to configure the main root agent"""

# from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.agents import LlmAgent
from google.adk.models.google_llm import Gemini
from google.adk.tools import AgentTool


# custom modules
from ..finance_agent.tools import (
    research_agent,
    log_tool,
    analyse_ticker
)
from ...utility.utils import retry_config


def root_agent() -> LlmAgent:
    """Return a root LLM agent that coordinates the research workflow."""

    instruction_lines = [
        "You are a research coordinator.",
        "Use the ResearchAgent tool to find relevant information for the",
        "provided ticker.",
        "After research, create a concise summary.",
        "Then call the analyse_ticker tool to obtain financial analysis.",
        "Combine research and analysis into a final summary for the user.",
        "Use log_tool to record progress when appropriate.",
    ]

    instruction = "\n".join(instruction_lines)

    return LlmAgent(
        name="ResearchCoordinator",
        model=Gemini(
            model="gemini-2.5-flash-lite",
            retry_options=retry_config(),
        ),
        instruction=instruction,
        # wrapping subagent to make it a callable tool for the root agent
        tools=[AgentTool(research_agent()), log_tool, analyse_ticker],
        output_key="final_summary",
    )
