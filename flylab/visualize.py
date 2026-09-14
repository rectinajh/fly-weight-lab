"""ASCII and (optional) chart visualization for the swarm."""

from __future__ import annotations

GREEN = "\033[32m"
RED = "\033[31m"
BOLD = "\033[1m"
RESET = "\033[0m"


def render_population(scores: list[float], farm: str | None = None, width: int = 44) -> str:
    if farm:
        glyphs = []
        step = max(1, len(farm) // width)
        for i in range(0, len(farm), step):
            mark = farm[i]
            if mark == "2":
                glyphs.append(f"{GREEN}{BOLD}▮{RESET}")
            elif mark == "1":
                glyphs.append(f"{GREEN}▫{RESET}")
            else:
                glyphs.append(f"{RED}▮{RESET}")
            if len(glyphs) >= width:
                break
        return "".join(glyphs)
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
    for gen, best, mean, scores, farm in (
        (row[0], row[1], row[2], row[3], row[4] if len(row) > 4 else "")
        for row in result.history
    ):
        show = farm_every and (gen == 0 or gen == last_gen or gen % farm_every == 0)
        rendered = render_population(scores, farm) if show else ""
        print(f"{gen:>4} {best:>8.2f} {mean:>8.2f}  {rendered}")
    print(
        f"\nLegend: {GREEN}▮ elite{RESET}  {GREEN}▫ parent pool{RESET}  {RED}▮ culled{RESET}"
    )


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
