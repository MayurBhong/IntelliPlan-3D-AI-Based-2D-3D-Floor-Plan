# ═══════════════════════════════════════════════════════════════
# ga_engine/fitness.py
# Multi-objective fitness function for IntelliPlan·3D GA
#
# Fitness = w_vastu      × vastu_score_normalised   (0-1)
#         + w_space_util × space_utilisation         (0-1)
#         + w_no_overlap × (1 - overlap_penalty)     (0-1)
#         + w_aspect     × aspect_ratio_score        (0-1)
#
# Weights are defined in utils/constants.py
# ═══════════════════════════════════════════════════════════════

import numpy as np
from typing import List, Dict, Any, Tuple

from geometry.room import Room
from geometry.overlap import overlap_penalty
from geometry.validation import space_utilisation, aspect_ratio_score
from vastu_engine.vastu_score import compute_vastu_score
from utils.constants import (
    FITNESS_W_VASTU,
    FITNESS_W_SPACE_UTIL,
    FITNESS_W_NO_OVERLAP,
    FITNESS_W_ASPECT_RATIO,
)


def evaluate_fitness(
    rooms: List[Room],
    plot_w: float,
    plot_h: float,
    facing: str,
) -> Tuple[float, float, float, List[Dict[str, Any]]]:
    """
    Compute the multi-objective fitness for one chromosome.

    Returns:
        fitness      — combined score in [0, 1]
        vastu_score  — Vastu compliance score in [0, 100]
        space_util   — space utilisation percentage [0, 100]
        vastu_rules  — list of rule dicts for frontend display
    """
    plot_area = plot_w * plot_h

    # ── Objective 1: Vastu compliance ──────────────────────────
    vastu_pct, vastu_rules = compute_vastu_score(rooms, plot_w, plot_h, facing)
    vastu_norm = vastu_pct / 100.0

    # ── Objective 2: Space utilisation ─────────────────────────
    util_frac = space_utilisation(rooms, plot_w, plot_h)
    # Ideal utilisation is ~75-85%; penalise extremes
    util_score = _util_score(util_frac)

    # ── Objective 3: No-overlap ─────────────────────────────────
    ov_penalty = overlap_penalty(rooms, plot_area)
    no_overlap_score = 1.0 - ov_penalty

    # ── Objective 4: Aspect-ratio quality ──────────────────────
    ar_score = aspect_ratio_score(rooms)

    # ── Combined fitness ────────────────────────────────────────
    fitness = (
        FITNESS_W_VASTU        * vastu_norm       +
        FITNESS_W_SPACE_UTIL   * util_score        +
        FITNESS_W_NO_OVERLAP   * no_overlap_score  +
        FITNESS_W_ASPECT_RATIO * ar_score
    )

    # Strong penalty for any overlaps (hard constraint)
    if ov_penalty > 0.01:
        fitness *= (1.0 - ov_penalty * 0.6)

    fitness     = float(np.clip(fitness, 0.0, 1.0))
    space_util  = round(util_frac * 100, 2)

    return fitness, vastu_pct, space_util, vastu_rules


def _util_score(util_frac: float) -> float:
    """
    Reward layouts with 65-88% space utilisation.
    Below 55% or above 95%: penalised.
    """
    if util_frac < 0.40:
        return util_frac / 0.40 * 0.5          # 0 → 0.5 ramp
    if util_frac <= 0.65:
        return 0.5 + (util_frac - 0.40) / 0.25 * 0.5   # 0.5 → 1.0
    if util_frac <= 0.88:
        return 1.0                               # sweet spot
    if util_frac <= 0.95:
        return 1.0 - (util_frac - 0.88) / 0.07 * 0.4   # 1.0 → 0.6
    return 0.5                                   # over-packed


def evaluate_population(
    population: np.ndarray,
    room_types: List[str],
    plot_w: float,
    plot_h: float,
    facing: str,
) -> np.ndarray:
    """
    Vectorised fitness evaluation for all chromosomes in the population.
    Returns a 1-D numpy array of fitness values (one per chromosome).
    """
    from ga_engine.chromosome import decode

    n = len(population)
    fitnesses = np.zeros(n, dtype=np.float32)

    for i in range(n):
        rooms = decode(population[i], room_types, plot_w, plot_h)
        fit, _, _, _ = evaluate_fitness(rooms, plot_w, plot_h, facing)
        fitnesses[i] = fit

    return fitnesses
