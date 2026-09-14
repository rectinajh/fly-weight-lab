"""ASCII and (optional) chart visualization for the swarm."""

from __future__ import annotations

GREEN = "\033[32m"
RED = "\033[31m"
BOLD = "\033[1m"
RESET = "\033[0m"


def render_population(scores: list[float], width: int = 44) -> str:
    if not scores:
        return ""
    ordered = sorted(scores)
    median = ordered[len(ordered) // 2]
    cells: list[str] = []
    for i in range(width):
        idx = min(len(scores) - 1, int(i * (len(scores) - 1) / max(1, width - 1)))
        alive = scores[idx] >= median
        cells.append(f"{GREEN}▮{RESET}" if alive else f"{RED}▮{RESET}")
    return "".join(cells)


def print_evolution(result, farm_every: int | None = None) -> None:
    print(f"\n{BOLD}Evolution history (gen | best | mean | population farm){RESET}")
    print(f"{'gen':>4} {'best':>8} {'mean':>8}  farm")
    last_gen = result.history[-1][0]
    for gen, best, mean, scores in result.history:
        show = farm_every and (gen == 0 or gen == last_gen or gen % farm_every == 0)
        farm = render_population(scores) if show else ""
        print(f"{gen:>4} {best:>8.2f} {mean:>8.2f}  {farm}")
    print(f"\nLegend: {GREEN}▮ alive (top half){RESET}  {RED}▮ dead (bottom half){RESET}")


def chart(result, out_path: str | None = None) -> str | None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    generations = [row[0] for row in result.history]
    best = [row[1] for row in result.history]
    mean = [row[2] for row in result.history]

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(generations, best, label="best", color="#2e7d32")
    ax.plot(generations, mean, label="mean", color="#90a4ae")
    ax.set_xlabel("generation")
    ax.set_ylabel("fitness")
    ax.set_title("Fly Weight-Lab swarm evolution")
    ax.legend()
    path = out_path or "/tmp/flylab_evolution.png"
    fig.savefig(path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return path
