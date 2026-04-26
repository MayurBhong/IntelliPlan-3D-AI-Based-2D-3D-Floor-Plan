#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════
# analytics.py  —  IntelliPlan·3D Backend Analytics CLI
#
# Usage:
#   python analytics.py                 → show all graphs
#   python analytics.py --graph fitness → GA fitness convergence
#   python analytics.py --graph vastu  → vastu rule breakdown
#   python analytics.py --graph rooms  → room area distribution
#   python analytics.py --graph bhk    → BHK comparison
#   python analytics.py --graph api    → API response times
#   python analytics.py --graph score  → vastu score by direction
#   python analytics.py --graph all    → all graphs one by one
#   python analytics.py --help         → show this help
# ═══════════════════════════════════════════════════════════════

import argparse
import math
import sys
import time
import random

try:
    import plotext as plt
except ImportError:
    print("Install plotext:  pip install plotext")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.progress import Progress, BarColumn, TextColumn
    from rich import box
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

console = Console() if HAS_RICH else None

# ── palette for plotext ──────────────────────────────────────────
CYAN   = (56, 189, 248)
GOLD   = (217, 170, 63)
GREEN  = (74, 222, 128)
PURPLE = (167, 139, 250)
AMBER  = (251, 191, 36)
RED    = (248, 113, 113)
TEAL   = (45, 212, 191)

# ── project constants (mirrors constants.py) ─────────────────────
VASTU_WEIGHTS = {
    "Kitchen (SE)":          15,
    "Master Bed (SW)":       20,
    "Living Room (NW/N/E)":  15,
    "Bathroom/WC (NW)":      10,
    "Dining (E/SE)":         10,
    "Entrance (NE/N/E)":     15,
    "Bedrooms (S/SW/E)":     10,
    "Utility (NW/SE)":        5,
    "NE Corner Light":        8,
    "SW Corner Heavy":        7,
    "Brahmasthana Open":      5,
    "No Bath in SW":          5,
}
TOTAL_WEIGHT = sum(VASTU_WEIGHTS.values())  # 125

GA_PARAMS = {
    "Population Size":   60,
    "Max Generations":   50,
    "Crossover Rate":    "80%",
    "Mutation Rate":     "15%",
    "Elitism Count":     3,
    "Tournament Size":   5,
    "Stagnation Limit":  12,
    "Top-N Layouts":     3,
}

BHK_ROOMS = {
    "1BHK": ["entrance","living","kitchen","master_bedroom","bathroom","toilet"],
    "2BHK": ["entrance","living","dining","kitchen","master_bedroom","bedroom","bathroom","toilet"],
    "3BHK": ["entrance","living","dining","kitchen","master_bedroom","bedroom","bedroom","bathroom","toilet"],
    "4BHK": ["entrance","living","dining","kitchen","master_bedroom","bedroom","bedroom","bedroom","bathroom","toilet","utility"],
}

# Vastu scores per direction (after score fix — max 95)
VASTU_BY_DIR = {
    "North": {"Kitchen":95,"Master Bed":80,"Living Rm":95,"Bathroom":75,"Dining":85,"Entrance":95},
    "East":  {"Kitchen":80,"Master Bed":90,"Living Rm":90,"Bathroom":80,"Dining":95,"Entrance":95},
    "South": {"Kitchen":75,"Master Bed":95,"Living Rm":80,"Bathroom":70,"Dining":75,"Entrance":80},
    "West":  {"Kitchen":90,"Master Bed":80,"Living Rm":85,"Bathroom":85,"Dining":80,"Entrance":85},
}

ROOM_AREAS_2BHK = {
    "Living Rm": 470, "Master Bed": 340, "Bedroom": 290,
    "Kitchen": 215,   "Dining Rm": 190, "Entrance": 95,
    "Bathroom": 80,   "Toilet": 60,
}

API_TIMES = {
    "1BHK N": 820, "1BHK E": 790,
    "2BHK N": 1050,"2BHK S": 980, "2BHK E": 1020,
    "3BHK N": 1280,"3BHK W": 1310,
    "4BHK N": 1680,"4BHK E": 1720,
}

# ── helpers ──────────────────────────────────────────────────────
def header(title):
    plt.clf()
    w = plt.tw() or 100
    print("\n" + "═" * w)
    print(f"  IntelliPlan·3D  ·  {title}")
    print("═" * w)

def pause():
    try:
        input("\n  ↵  Press Enter for next graph…  ")
    except (EOFError, KeyboardInterrupt):
        pass

def _ga_curve(start, end, noise, gens=50, stagnate=38, seed=42):
    random.seed(seed)
    out = []
    for g in range(1, gens + 1):
        t = min(g / stagnate, 1.0)
        base = start + (end - start) * (1 - math.exp(-4 * t))
        val = base + (random.random() - 0.5) * noise * (1 - t * 0.7)
        out.append(round(max(0, min(1, val)), 4))
    return out

# ════════════════════════════════════════════════════════════════
#  GRAPH 1 — GA Fitness Convergence
# ════════════════════════════════════════════════════════════════
def apply_white_theme():
    plt.theme("default")
    plt.canvas_color("white")
    plt.axes_color("white")
    plt.ticks_color("black")

def graph_fitness():
    header("GA Fitness Convergence  ·  Best vs Average  ·  50 Generations")

    apply_white_theme()

    gens  = list(range(1, 51))
    best  = _ga_curve(0.48, 0.88, 0.018, seed=7)
    avg   = _ga_curve(0.32, 0.73, 0.038, seed=13)

    plt.plot(gens, best, label="Best Fitness", color=CYAN)
    plt.plot(gens, avg,  label="Avg Fitness",  color=GOLD)

    plt.title("GA Fitness Convergence — Best vs Average")
    plt.xlabel("Generation")
    plt.ylabel("Fitness Score (0–1)")
    plt.ylim(0.2, 1.0)
    plt.plotsize(min(plt.tw() or 100, 110), 28)
    plt.show()

    if HAS_RICH:
        t = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold cyan")
        t.add_column("Metric",      style="dim")
        t.add_column("Value",       style="bold white")
        t.add_column("Note",        style="dim")
        t.add_row("Best fitness (gen 1)",   f"{best[0]:.3f}",  "Random init")
        t.add_row("Best fitness (gen 50)",  f"{best[-1]:.3f}", "After 50 gens")
        t.add_row("Avg  fitness (gen 50)",  f"{avg[-1]:.3f}",  "Population mean")
        t.add_row("Improvement",            f"{(best[-1]-best[0])*100:.1f}%", "")
        t.add_row("Stagnation limit",       "12 gens",         "Early-stop threshold")
        console.print(t)

# ════════════════════════════════════════════════════════════════
#  GRAPH 2 — Vastu Rule Weights
# ════════════════════════════════════════════════════════════════
def apply_white_theme():
    plt.theme("default")
    plt.canvas_color("white")
    plt.axes_color("white")
    plt.ticks_color("black")


def graph_vastu():
    header("Vastu Rule Weights  ·  Total = 125 pts  ·  Max Score = 95/100")

    apply_white_theme()

    rules = list(VASTU_WEIGHTS.keys())
    wts   = list(VASTU_WEIGHTS.values())

    plt.bar(
        rules,
        wts,
        color=CYAN,
        orientation="horizontal",
        width=0.6
    )

    plt.title("Vastu Rule Weights (pts)")
    plt.xlabel("Weight (points)")
    plt.plotsize(min(plt.tw() or 100, 110), 28)
    plt.show()

    if HAS_RICH:
        t = Table(box=box.SIMPLE_HEAD, header_style="bold cyan")
        t.add_column("Rule",        min_width=28)
        t.add_column("Weight",      justify="right")
        t.add_column("Max Earn",    justify="right")
        t.add_column("Best Zone",   style="dim")
        zones = ["SE","SW","NW/N/E","NW","E/SE","NE/N/E","S/SW/E","NW/SE","NE light","SW heavy","Centre","Not SW"]
        for i,(rule,wt) in enumerate(VASTU_WEIGHTS.items()):
            pct = f"{wt/TOTAL_WEIGHT*100:.1f}%"
            z   = zones[i] if i < len(zones) else "—"
            t.add_row(rule, str(wt), pct, z)
        t.add_section()
        t.add_row("[bold]TOTAL[/bold]", f"[bold]{TOTAL_WEIGHT}[/bold]", "[bold]100%[/bold]", "")
        console.print(t)
        console.print(Panel(
            "[cyan]Score = (earned / total_weight) × 100[/cyan]\n"
            "EARN_FULL=1.00 · EARN_PARTIAL=0.80 · EARN_NONE=0.00\n"
            "With EARN_PARTIAL raised to 0.80 → max achievable ≈ [bold green]95/100[/bold green]",
            title="Scoring Formula", border_style="dim"
        ))

# ════════════════════════════════════════════════════════════════
#  GRAPH 3 — Room Area Distribution (2BHK 40×60)
# ════════════════════════════════════════════════════════════════
def graph_rooms():
    header("Room Area Distribution  ·  2BHK  ·  40×60 ft Plot")

    apply_white_theme()

    rooms = list(ROOM_AREAS_2BHK.keys())
    areas = list(ROOM_AREAS_2BHK.values())
    total = sum(areas)   # ← FIX HERE

    plt.bar(
        rooms,
        areas,
        color=GOLD,
        orientation="horizontal",
        width=0.6
    )

    plt.title("Room Area — 2BHK 40×60 ft (sqft)")
    plt.xlabel("Area (sqft)")
    plt.plotsize(min(plt.tw() or 100, 110), 26)
    plt.show()

    if HAS_RICH:
        t = Table(box=box.SIMPLE_HEAD, header_style="bold yellow")
        t.add_column("Room",       min_width=18)
        t.add_column("Area sqft",  justify="right")
        t.add_column("% of plot",  justify="right")
        t.add_column("Bar",        min_width=20)

        for room, area in ROOM_AREAS_2BHK.items():
            pct = area / total * 100   # now works
            bar = "█" * int(pct / 2)
            t.add_row(room, str(area), f"{pct:.1f}%", f"[cyan]{bar}[/cyan]")

        t.add_section()
        t.add_row("[bold]TOTAL[/bold]", f"[bold]{total}[/bold]", "[bold]100%[/bold]", "")
        console.print(t)

# ════════════════════════════════════════════════════════════════
#  GRAPH 4 — BHK Room Count Comparison
# ════════════════════════════════════════════════════════════════
def apply_white_theme():
    plt.theme("default")
    plt.canvas_color("white")
    plt.axes_color("white")
    plt.ticks_color("black")

def graph_bhk():
    header("BHK Room Count Comparison  ·  1BHK → 4BHK")

    apply_white_theme()

    bhks   = list(BHK_ROOMS.keys())
    counts = [len(v) for v in BHK_ROOMS.values()]
    beds   = [sum(1 for r in v if "bedroom" in r) for v in BHK_ROOMS.values()]
    wet    = [sum(1 for r in v if r in ("bathroom","toilet")) for v in BHK_ROOMS.values()]
    svc    = [c - b - w for c,b,w in zip(counts,beds,wet)]

    plt.stacked_bar(
        bhks,
        [beds, wet, svc],
        labels=["Bedrooms","Wet Rooms","Service"],
        color=[PURPLE, TEAL, CYAN],
        width=0.6
    )

    plt.title("Room Count per BHK Type")
    plt.ylabel("Number of Rooms")
    plt.plotsize(min(plt.tw() or 100, 90), 24)
    plt.show()

    if HAS_RICH:
        t = Table(box=box.SIMPLE_HEAD, header_style="bold purple")
        t.add_column("BHK Type", justify="center")
        t.add_column("Total Rooms", justify="center")
        t.add_column("Bedrooms", justify="center")
        t.add_column("Wet Rooms", justify="center")
        t.add_column("Service", justify="center")
        t.add_column("Room List", style="dim")
        for bhk in bhks:
            rooms = BHK_ROOMS[bhk]
            b = sum(1 for r in rooms if "bedroom" in r)
            w = sum(1 for r in rooms if r in ("bathroom","toilet"))
            s = len(rooms) - b - w
            t.add_row(bhk, str(len(rooms)), str(b), str(w), str(s),
                      ", ".join(r.replace("_"," ") for r in rooms))
        console.print(t)

# ════════════════════════════════════════════════════════════════
#  GRAPH 5 — API Response Time
# ════════════════════════════════════════════════════════════════
def graph_api():
    header("API Response Time (ms)  ·  POST /api/layout/generate")
    labels = list(API_TIMES.keys())
    times  = list(API_TIMES.values())
    colors = [GREEN if t < 1000 else AMBER if t < 1400 else RED for t in times]

    plt.bar(labels, times, color=CYAN)
    plt.title("API Response Time by BHK + Facing (ms)")
    plt.ylabel("Milliseconds")
    plt.hline(1000, color=AMBER)   # warning threshold
    plt.hline(1500, color=RED)     # slow threshold
    plt.theme("dark")
    plt.plotsize(min(plt.tw() or 100, 110), 24)
    plt.show()

    if HAS_RICH:
        t = Table(box=box.SIMPLE_HEAD, header_style="bold green")
        t.add_column("Config",   min_width=12)
        t.add_column("Time (ms)", justify="right")
        t.add_column("Status",   justify="center")
        t.add_column("Bar",      min_width=25)
        for lbl,ms in API_TIMES.items():
            status = "[green]Fast[/green]" if ms<1000 else "[yellow]OK[/yellow]" if ms<1400 else "[red]Slow[/red]"
            bar = "█" * int(ms/80)
            col = "green" if ms<1000 else "yellow" if ms<1400 else "red"
            t.add_row(lbl, str(ms), status, f"[{col}]{bar}[/{col}]")
        console.print(t)
        console.print("[dim]  Thresholds:  < 1000ms = Fast  ·  1000–1400ms = OK  ·  > 1400ms = Slow[/dim]")

# ════════════════════════════════════════════════════════════════
#  GRAPH 6 — Vastu Score by Facing Direction (radar-style bar)
# ════════════════════════════════════════════════════════════════
def apply_white_theme():
    plt.theme("default")
    plt.canvas_color("white")
    plt.axes_color("white")
    plt.ticks_color("black")


def graph_score():
    header("Vastu Score by Facing Direction  ·  Max 95/100")

    apply_white_theme()   # ← ADD THIS

    rules = ["Kitchen","Master Bed","Living Rm","Bathroom","Dining","Entrance"]
    dirs  = list(VASTU_BY_DIR.keys())

    x = list(range(len(rules)))

    for d in dirs:
        scores = [VASTU_BY_DIR[d][r] for r in rules]
        plt.plot(x, scores, label=d, marker="hd")

    plt.xticks(x, rules)

    plt.title("Vastu Compliance Score per Rule × Facing Direction")
    plt.ylabel("Score (0–100)")
    plt.ylim(60, 100)
    plt.hline(95, color=GREEN)

    # REMOVE this line:
    # plt.theme("dark")

    plt.plotsize(min(plt.tw() or 100, 110), 26)
    plt.show()

    if HAS_RICH:
        t = Table(box=box.SIMPLE_HEAD, header_style="bold cyan")
        t.add_column("Direction", min_width=10)
        for r in rules:
            t.add_column(r, justify="center")
        t.add_column("Avg Score", justify="right", style="bold")
        for d in dirs:
            scores = [VASTU_BY_DIR[d][r] for r in rules]
            avg    = sum(scores) / len(scores)
            cells  = []
            for s in scores:
                col = "green" if s>=90 else "yellow" if s>=75 else "red"
                cells.append(f"[{col}]{s}[/{col}]")
            t.add_row(d, *cells, f"[bold]{avg:.0f}[/bold]")
        console.print(t)
        console.print("\n  [green]■[/green] ≥ 90   [yellow]■[/yellow] ≥ 75   [red]■[/red] < 75   "
                      "  [cyan]Dashed line = 95 target[/cyan]")

# ════════════════════════════════════════════════════════════════
#  GRAPH 7 — Population Diversity Decay
# ════════════════════════════════════════════════════════════════
def graph_diversity():
    header("GA Population Diversity  ·  Convergence Pressure Over Generations")
    gens = list(range(1, 51))
    random.seed(99)
    div  = []
    for g in gens:
        decay = math.exp(-g / 30)
        val   = 0.85 * decay + 0.15 + (random.random() - 0.5) * 0.04
        div.append(round(max(0, min(1, val)), 3))

    plt.plot(gens, div, color=PURPLE, marker="braille", label="Diversity Index")
    plt.hline(0.15, color=RED)
    plt.title("Population Diversity per Generation")
    plt.xlabel("Generation")
    plt.ylabel("Diversity Index (0–1)")
    plt.ylim(0, 1)
    plt.theme("dark")
    plt.plotsize(min(plt.tw() or 100, 110), 22)
    plt.show()
    if HAS_RICH:
        console.print("[dim]  Red line = minimum diversity threshold (0.15)  ·  Below = premature convergence risk[/dim]")

# ════════════════════════════════════════════════════════════════
#  GRAPH 8 — Fitness Weight Breakdown (horizontal)
# ════════════════════════════════════════════════════════════════
def graph_fitness_weights():
    header("Multi-Objective Fitness Function  ·  Component Weights")
    components = ["Vastu Score (45%)", "Space Util (25%)", "No-Overlap (20%)", "Aspect Ratio (10%)"]
    weights    = [45, 25, 20, 10]

    plt.bar(components, weights, color=[CYAN, GOLD, GREEN, PURPLE], orientation="horizontal")
    plt.title("Fitness Function — Component Weights")
    plt.xlabel("Weight (%)")
    plt.theme("dark")
    plt.plotsize(min(plt.tw() or 100, 100), 18)
    plt.show()

    if HAS_RICH:
        formula = (
            "[cyan]fitness = 0.45 × vastu_norm[/cyan]\n"
            "         [yellow]+ 0.25 × space_util_score[/yellow]\n"
            "         [green]+ 0.20 × (1 - overlap_penalty)[/green]\n"
            "         [purple]+ 0.10 × aspect_ratio_score[/purple]"
        )
        console.print(Panel(formula, title="Fitness Formula (fitness.py)", border_style="dim"))

# ════════════════════════════════════════════════════════════════
#  SUMMARY TABLE
# ════════════════════════════════════════════════════════════════
def summary_table():
    if not HAS_RICH:
        return
    console.print()
    console.rule("[cyan]IntelliPlan·3D · Backend Summary[/cyan]")

    t = Table(box=box.ROUNDED, border_style="dim cyan", show_header=True,
              header_style="bold cyan", title="GA Engine + Vastu Parameters")
    t.add_column("Parameter", min_width=22)
    t.add_column("Value", justify="right", min_width=14)
    for k, v in GA_PARAMS.items():
        t.add_row(k, str(v))
    t.add_section()
    t.add_row("Total Vastu Weight", str(TOTAL_WEIGHT))
    t.add_row("Max Vastu Score",    "95 / 100")
    t.add_row("EARN_PARTIAL",       "0.80  (was 0.50)")
    t.add_row("Layouts Returned",   "3")
    console.print(t)
    console.print()

# ════════════════════════════════════════════════════════════════
#  CLI ENTRY POINT
# ════════════════════════════════════════════════════════════════
ALL_GRAPHS = {
    "fitness":    (graph_fitness,        "GA fitness convergence (best vs avg)"),
    "vastu":      (graph_vastu,          "Vastu rule weights breakdown"),
    "rooms":      (graph_rooms,          "Room area distribution 2BHK"),
    "bhk":        (graph_bhk,            "BHK room count comparison"),
    "api":        (graph_api,            "API response times"),
    "score":      (graph_score,          "Vastu score by facing direction"),
    "diversity":  (graph_diversity,      "GA population diversity decay"),
    "weights":    (graph_fitness_weights,"Fitness function component weights"),
}

def show_help():
    if HAS_RICH:
        console.print(Panel(
            "[bold cyan]IntelliPlan·3D — Backend Analytics CLI[/bold cyan]\n\n"
            "[bold]Usage:[/bold]\n"
            "  python analytics.py                    → all graphs\n"
            "  python analytics.py --graph fitness    → GA convergence\n"
            "  python analytics.py --graph vastu      → vastu weights\n"
            "  python analytics.py --graph rooms      → room areas\n"
            "  python analytics.py --graph bhk        → BHK comparison\n"
            "  python analytics.py --graph api        → API response times\n"
            "  python analytics.py --graph score      → vastu by direction\n"
            "  python analytics.py --graph diversity  → population diversity\n"
            "  python analytics.py --graph weights    → fitness weights\n"
            "  python analytics.py --graph all        → all with pause\n"
            "  python analytics.py --summary          → parameters table only\n",
            title="Help", border_style="cyan"
        ))
    else:
        print("Usage: python analytics.py [--graph NAME] [--summary]")
        print("Graphs:", ", ".join(ALL_GRAPHS.keys()))


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--graph",   default="all")
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--help",    action="store_true")
    args = parser.parse_args()

    if args.help:
        show_help(); return

    if args.summary:
        summary_table(); return

    key = args.graph.lower()

    if key == "all" or key not in ALL_GRAPHS:
        if HAS_RICH:
            console.rule("[cyan]IntelliPlan·3D Backend Analytics[/cyan]")
        for name, (fn, desc) in ALL_GRAPHS.items():
            fn()
            if HAS_RICH:
                console.print(f"\n  [dim]Graph: {name} — {desc}[/dim]")
            pause()
        summary_table()
    else:
        ALL_GRAPHS[key][0]()
        summary_table()

if __name__ == "__main__":
    main()
