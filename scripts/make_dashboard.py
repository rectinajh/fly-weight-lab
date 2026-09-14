"""Generate a polished evolution dashboard from real swarm/agent runs.

Run from the repository root:
    .venv/bin/python scripts/make_dashboard.py

Output:
    assets/evolution_dashboard.png
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flylab.agent_loop import WeightLossAgent
from flylab.connectome import load_params
from flylab.evolution import Swarm
from flylab.genotype import Fly
from flylab.twin import BehavioralTwin, UserProfile


OUT = ROOT / "assets" / "evolution_dashboard.png"

COLORS = {
    "bg": "#07111f",
    "panel": "#0e1c30",
    "grid": "#1d3148",
    "text": "#eaf2fb",
    "muted": "#8aa0b8",
    "green": "#35d07f",
    "red": "#ff5c7a",
    "cyan": "#4cc9f0",
    "yellow": "#ffd166",
}


def build_data():
    profile = UserProfile(
        name="plateau_prone",
        start_weight_kg=88.0,
        adherence_base=0.6,
        binge_sensitivity=0.6,
        metabolic_adaptation=0.5,
        water_noise_kg=0.4,
        maintenance_kcal=2300.0,
    )
    params = load_params()
    grounded_twin = BehavioralTwin(profile, connectome=params)

    swarm = Swarm(grounded_twin, population_size=600, generations=50, seed=7).run()

    current = Fly(
        calorie_target=1500,
        protein_pct=0.40,
        carb_pct=0.25,
        meal_window=8,
        meal_count=3,
        late_night_rule=False,
        workout_freq=5,
        workout_type="cardio",
        sleep_target=7.0,
        refeed_schedule="none",
        step_target=10000,
    )
    observed = BehavioralTwin(profile, connectome=params)
    curve = observed.simulate(current, 12)
    agent = WeightLossAgent(profile, current, connectome=params)

    surfaced = []
    for week in range(1, 13):
        agent.ingest(float(curve[week]))
        decision = agent.tick(week)
        if decision is not None:
            surfaced.append(week)

    return profile, params, grounded_twin, swarm, current, curve, surfaced


def style_axis(ax, title, subtitle=None):
    ax.set_facecolor(COLORS["panel"])
    ax.set_title(title, color=COLORS["text"], loc="left", fontsize=13, fontweight="bold", pad=10)
    if subtitle:
        ax.text(
            0.0,
            1.045,
            subtitle,
            transform=ax.transAxes,
            color=COLORS["muted"],
            fontsize=9,
            va="bottom",
        )
    for spine in ax.spines.values():
        spine.set_color(COLORS["grid"])
    ax.tick_params(colors=COLORS["muted"], labelsize=9)
    ax.grid(True, color=COLORS["grid"], linewidth=0.7, alpha=0.55)


def plot_dashboard(data):
    profile, params, twin, swarm, current, curve, surfaced = data

    fig = plt.figure(figsize=(18, 10), facecolor=COLORS["bg"])
    gs = GridSpec(
        2,
        2,
        figure=fig,
        left=0.055,
        right=0.965,
        top=0.855,
        bottom=0.075,
        wspace=0.17,
        hspace=0.34,
        width_ratios=[1.12, 1],
        height_ratios=[1, 1],
    )

    fig.suptitle(
        "Fly Weight-Lab — Background Evolution Dashboard",
        color=COLORS["text"],
        fontsize=22,
        fontweight="bold",
        x=0.055,
        ha="left",
    )
    fig.text(
        0.055,
        0.925,
        "Real Janelia MaleCNS mushroom-body prior · quiet background agent · one decision at a time",
        color=COLORS["muted"],
        fontsize=11,
    )

    # A: evolution history
    ax_a = fig.add_subplot(gs[0, 0])
    gens = [row[0] for row in swarm.history]
    best = [row[1] for row in swarm.history]
    mean = [row[2] for row in swarm.history]
    style_axis(ax_a, "1 · Swarm evolution", "best vs mean fitness across 50 generations")
    ax_a.plot(gens, best, color=COLORS["green"], linewidth=2.2, label="best fitness")
    ax_a.plot(gens, mean, color=COLORS["cyan"], linewidth=1.6, alpha=0.85, label="population mean")
    ax_a.fill_between(gens, mean, best, color=COLORS["green"], alpha=0.08)
    ax_a.legend(loc="lower right", facecolor=COLORS["panel"], labelcolor=COLORS["text"], framealpha=0.9)
    ax_a.set_xlabel("generation", color=COLORS["muted"])
    ax_a.set_ylabel("fitness", color=COLORS["muted"])

    # B: agent timeline
    ax_b = fig.add_subplot(gs[0, 1])
    style_axis(ax_b, "2 · Background agent", "12 weeks · quiet unless a real decision appears")
    weeks = list(range(1, 13))
    y = [1] * len(weeks)
    ax_b.scatter(
        [w for w in weeks if w in surfaced],
        [1] * len(surfaced),
        s=170,
        color=COLORS["yellow"],
        edgecolor="white",
        linewidth=0.7,
        zorder=3,
        label="surfaced decision",
    )
    ax_b.scatter(
        [w for w in weeks if w not in surfaced],
        [1] * (12 - len(surfaced)),
        s=60,
        color=COLORS["green"],
        alpha=0.6,
        zorder=3,
        label="quiet",
    )
    ax_b.set_xlim(0, 13)
    ax_b.set_ylim(0.82, 1.18)
    ax_b.set_yticks([])
    ax_b.set_xticks(weeks)
    ax_b.axhline(1, color=COLORS["grid"], linewidth=0.8, zorder=1)
    ax_b.legend(loc="upper right", facecolor=COLORS["panel"], labelcolor=COLORS["text"], framealpha=0.9)
    ax_b.set_xlabel("week", color=COLORS["muted"])

    # C: weight curve with surfaced markers
    ax_c = fig.add_subplot(gs[1, 0])
    style_axis(ax_c, "3 · Observed weight response", "aggressive starting protocol · grounded twin")
    ax_c.plot(range(13), curve, color=COLORS["cyan"], linewidth=2.2, marker="o", markersize=4)
    for w in surfaced:
        ax_c.axvline(w, color=COLORS["yellow"], linewidth=0.9, linestyle="--", alpha=0.75)
        ax_c.plot(w, curve[w], marker="*", markersize=14, color=COLORS["yellow"], zorder=4)
    ax_c.set_xlabel("week", color=COLORS["muted"])
    ax_c.set_ylabel("weight (kg)", color=COLORS["muted"])

    # D: champion / connectome card
    ax_d = fig.add_subplot(gs[1, 1])
    ax_d.axis("off")
    ax_d.set_facecolor(COLORS["panel"])
    champion = swarm.best_fly
    lines = [
        ("Champion protocol", 15, COLORS["text"], "bold"),
        (f"{champion.calorie_target} kcal/day", 20, COLORS["green"], "bold"),
        (f"late-night snack: {'yes' if champion.late_night_rule else 'no'}", 11, COLORS["text"], "normal"),
        (f"refeed: {champion.refeed_schedule}", 11, COLORS["text"], "normal"),
        (f"sleep target: {champion.sleep_target}h", 11, COLORS["text"], "normal"),
        (f"meal window: {champion.meal_window}h", 11, COLORS["text"], "normal"),
        ("", 8, COLORS["muted"], "normal"),
        ("Real connectome prior", 13, COLORS["yellow"], "bold"),
        (f"reward : punishment = {params.reward_punishment_ratio:.2f} : 1", 11, COLORS["text"], "normal"),
        (f"{params.n_kenyon} KC -> {params.n_mbon} MBON decision units", 10, COLORS["muted"], "normal"),
        ("", 8, COLORS["muted"], "normal"),
        ("Agent behavior", 13, COLORS["cyan"], "bold"),
        (f"{len(surfaced)} decisions surfaced / 12 weeks", 12, COLORS["text"], "normal"),
    ]
    y = 0.96
    for text, size, color, weight in lines:
        ax_d.text(0.05, y, text, color=color, fontsize=size, fontweight=weight, va="top")
        y -= 0.09 if text else 0.03

    fig.savefig(OUT, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)
    return OUT


def main() -> Path:
    data = build_data()
    path = plot_dashboard(data)
    print(f"dashboard written: {path}")
    return path


if __name__ == "__main__":
    main()
