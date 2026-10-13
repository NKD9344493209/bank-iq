"""Shared helpers for the experiment scripts: paths, plotting style, JSON writing."""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
FIG = RESULTS / "figures"
FIG.mkdir(parents=True, exist_ok=True)

# validated default palette (light mode)
C = {"blue": "#2a78d6", "orange": "#eb6834", "aqua": "#1baf7a", "yellow": "#eda100", "magenta": "#e87ba4",
     "green": "#008300", "violet": "#4a3aa7", "red": "#e34948", "grey": "#b8b7b1", "ink": "#0b0b0b", "ink2": "#52514e"}
SERIES = [C["blue"], C["orange"], C["aqua"], C["yellow"], C["magenta"], C["green"], C["violet"], C["red"]]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": "#d9d8d3", "axes.linewidth": 0.8,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": "#ececea",
                     "grid.linewidth": 0.6, "axes.axisbelow": True, "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
                     "text.color": C["ink"], "axes.labelcolor": C["ink2"], "xtick.color": C["ink2"], "ytick.color": C["ink2"],
                     "figure.dpi": 150, "legend.frameon": False})


def save_fig(fig, name: str):
    fig.tight_layout()
    fig.savefig(FIG / f"{name}.png", bbox_inches="tight")
    plt.close(fig)
    print("  saved", name)


def save_json(obj, name: str):
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"{name}.json").write_text(json.dumps(obj, indent=2, default=_default))
    print("  wrote", name + ".json")


def _default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def bar_with_labels(ax, labels, values, color=None, fmt="{:.3f}", ylim=None, horizontal=False):
    color = color or C["blue"]
    if horizontal:
        bars = ax.barh(labels, values, color=color, height=0.6)
        for b, v in zip(bars, values):
            ax.text(b.get_width() + (max(values) * 0.01), b.get_y() + b.get_height() / 2, fmt.format(v), va="center", fontsize=8, color=C["ink2"])
        ax.grid(axis="y", visible=False)
    else:
        bars = ax.bar(labels, values, color=color, width=0.6)
        for b, v in zip(bars, values):
            ax.text(b.get_x() + b.get_width() / 2, v + (max(values) * 0.01), fmt.format(v), ha="center", fontsize=8, color=C["ink2"])
        ax.grid(axis="x", visible=False)
    if ylim:
        ax.set_ylim(*ylim)
    return bars
