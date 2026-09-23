""" module to configure agent tools"""
from pathlib import Path

from typing import Optional, Dict, Any, Sequence
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import uuid



# accessing skills
def read_skills(skill: str) -> str:
    """
    Extract instructions that serve as guiding skills.

    Args:
        skill (str): The skill name to retrieve.
            Available skills include:
            - visualizations
            - financial_analysis
    Raises:
        ValueError: May raise value error exception if a non-existent skill is requested.
        These are logged but may propagate up.
    Returns:
        str: The full text of the requested skill instructions.
    """
    if skill.lower() not in ['financial_analysis', 'standard guide']:
        raise ValueError('invalid input, available skills are:' \
                                        'financial_analysis')
    path = Path("system") / "agents" / "finance_agent" / "skills" / f"{skill.lower()}.md"
    return path.read_text(encoding="utf-8")

# In-memory storage for plots: key -> matplotlib.figure.Figure
plot_store: Dict[str, Figure] = {}

def save_figure(fig: Figure, key: str | None = None) -> str:
    if key is None:
        key = str(uuid.uuid4())

    plot_store[key] = fig
    return key

def build_and_save_plot(
    x: list[float],
    y: list[float],
    key: Optional[str] = None,
    plot_kwargs: Optional[dict[str, Any]] = None,
) -> str:
    """
    Create a matplotlib plot from x and y values and save the figure
    into the in-memory plot_store.

    Args:
        x: X-axis values.
        y: Y-axis values.
        key: Optional storage key. A UUID is generated if omitted.
        plot_kwargs: Optional plotting configuration.

    Returns:
        str: Storage key on success, otherwise an error message.
    """
    try:
        if len(x) != len(y):
            return "failed: x and y must have the same length"

        plot_kwargs = plot_kwargs or {}

        fig, ax = plt.subplots()

        plot_args = {
            k: v
            for k, v in plot_kwargs.items()
            if k not in ("title", "xlabel", "ylabel")
        }

        ax.plot(x, y, **plot_args)

        if "title" in plot_kwargs:
            ax.set_title(plot_kwargs["title"])

        if "xlabel" in plot_kwargs:
            ax.set_xlabel(plot_kwargs["xlabel"])

        if "ylabel" in plot_kwargs:
            ax.set_ylabel(plot_kwargs["ylabel"])

        fig.tight_layout()
        save_figure(fig, key)

        return "success: plot saved with key {}".format(key)

    except Exception as err:
        return f"failed: {str(err)}"

def get_guardrails() -> str:
    return read_skills('standard guide')

def clear_plots() -> None:
    """Clear all stored plots from the in-memory plot_store."""
    plot_store.clear()


