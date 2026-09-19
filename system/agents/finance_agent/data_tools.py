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

def build_and_save_plot(
    x: Optional[Sequence[float]] = None,
    y: Optional[Sequence[float]] = None,
    fig: Optional[Figure] = None,
    key: Optional[str] = None,
    plot_kwargs: Optional[Dict[str, Any]] = None
) -> str:
    """
    Build a matplotlib Figure from x and y (or accept an existing Figure)
    and save it to the in-memory `plot_store`.

    Args:
        x: Sequence of x values (required if fig is None).
        y: Sequence of y values (required if fig is None).
        fig: An existing matplotlib Figure to save (optional).
        key: Optional storage key. If not provided a UUID key is generated.
        plot_kwargs: Optional dict passed to ax.plot and for title/xlabel/ylabel:
            e.g. {"color":"C0", "title":"Price", "xlabel":"Date", "ylabel":"Price"}.

    Returns:
        str: On success returns the storage key (e.g. "a1b2...").
             On failure returns "failed: <error message>".
    """
    try:
        plot_kwargs = plot_kwargs or {}

        # Build a new figure if none provided
        if fig is None:
            if x is None or y is None:
                return "failed: either provide an existing Figure or both x and y data"
            fig, ax = plt.subplots()
            ax.plot(x, y, **{k: v for k, v in plot_kwargs.items() if k not in ("title", "xlabel", "ylabel")})
            if "title" in plot_kwargs:
                ax.set_title(plot_kwargs["title"])
            if "xlabel" in plot_kwargs:
                ax.set_xlabel(plot_kwargs["xlabel"])
            if "ylabel" in plot_kwargs:
                ax.set_ylabel(plot_kwargs["ylabel"])
            fig.tight_layout()

        # Generate a unique key if not supplied
        if key is None:
            key = str(uuid.uuid4())

        # Save to in-memory store
        plot_store[key] = fig
        return key
    except Exception as err:
        return f"failed: {err}"

def get_guardrails() -> str:
    return read_skills('standard guide')

def clear_plots() -> None:
    """Clear all stored plots from the in-memory plot_store."""
    plot_store.clear()


