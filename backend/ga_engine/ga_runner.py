# ═══════════════════════════════════════════════════════════════
# ga_engine/ga_runner.py
# Full Genetic Algorithm execution pipeline for IntelliPlan·3D
#
# Pipeline per generation:
#   1. Initialise population (grid-seeded chromosomes)
#   2. Evaluate fitness (Vastu + space util + overlap + aspect ratio)
#   3. Elitism  — carry top-N chromosomes unchanged
#   4. Tournament selection → parents
#   5. Adaptive crossover   → offspring
#   6. Composite mutation   → mutated offspring
#   7. Re-evaluate fitness
#   8. Early-stop on stagnation
#   9. Return top-K distinct Layout objects (sorted best→worst)
#
# CHANGE vs original:
#   Layout decoding now uses layout_generator.generate_layout()
#   instead of chromosome.decode(). This produces proper structured
#   floor plans (zero overlaps, realistic room sizes) while keeping
#   the entire GA engine (chromosome, population, operators) intact.
#   The chromosome genes are passed as split_ratios to drive variation.
# ═══════════════════════════════════════════════════════════════

import numpy as np
from typing import List, Optional
from utils.logger import get_logger
from utils.constants import (
    GA_POPULATION_SIZE,
    GA_MAX_GENERATIONS,
    GA_CROSSOVER_RATE,
    GA_MUTATION_RATE,
    GA_ELITISM_COUNT,
    GA_TOP_LAYOUTS_RETURN,
    BHK_ROOM_COMPOSITIONS,
)
from ga_engine.chromosome import chromosome_length
from ga_engine.population import initialise_population, population_diversity
from ga_engine.fitness import evaluate_fitness
from ga_engine.selection import tournament_select, elitism_indices, rank_population
from ga_engine.operators import crossover, mutate
from ga_engine.layout_generator import generate_layout   # NEW import
from geometry.layout import Layout

logger = get_logger(__name__)

# ── Stagnation early-stop ────────────────────────────────────────
_STAGNATION_LIMIT   = 12    # generations without improvement → stop
_IMPROVEMENT_THRESH = 1e-4  # min improvement to reset stagnation counter


def run_ga(
    plot_w:          float,
    plot_h:          float,
    bhk_type:        str,
    facing:          str,
    pop_size:        int   = GA_POPULATION_SIZE,
    max_generations: int   = GA_MAX_GENERATIONS,
    crossover_rate:  float = GA_CROSSOVER_RATE,
    mutation_rate:   float = GA_MUTATION_RATE,
    elitism_count:   int   = GA_ELITISM_COUNT,
    top_n:           int   = GA_TOP_LAYOUTS_RETURN,
    seed:            Optional[int] = None,
) -> List[Layout]:
    """
    Run the Genetic Algorithm and return the top-N floor plan layouts.

    Args:
        plot_w, plot_h   — plot dimensions in feet
        bhk_type         — "1BHK" | "2BHK" | "3BHK" | "4BHK"
        facing           — "North" | "East" | "South" | "West"
        pop_size         — chromosomes in the population
        max_generations  — maximum GA generations to run
        crossover_rate   — crossover probability [0,1]
        mutation_rate    — gene mutation probability [0,1]
        elitism_count    — elites carried forward each generation
        top_n            — number of distinct layouts to return
        seed             — optional RNG seed (reproducibility)

    Returns:
        List[Layout] sorted by descending fitness (index 0 = best).
    """
    rng        = np.random.default_rng(seed)
    room_types = BHK_ROOM_COMPOSITIONS.get(bhk_type, BHK_ROOM_COMPOSITIONS["2BHK"])
    n_rooms    = len(room_types)

    logger.info(
        "GA start | %s | %.0f×%.0f ft | %s facing | "
        "pop=%d | gen=%d | rooms=%d",
        bhk_type, plot_w, plot_h, facing,
        pop_size, max_generations, n_rooms,
    )

    # ── 1. Initialise population ─────────────────────────────────
    population = initialise_population(pop_size, room_types, plot_w, plot_h, seed)
    fitnesses  = _evaluate_population(population, room_types, plot_w, plot_h,
                                       bhk_type, facing, rng)

    best_fitness  = float(np.max(fitnesses))
    stagnation    = 0

    # ── 2. Evolution loop ─────────────────────────────────────────
    for gen in range(max_generations):
        new_pop = np.empty_like(population)
        cursor  = 0

        # ── a. Elitism ──────────────────────────────────────────
        for ei in elitism_indices(fitnesses, elitism_count):
            if cursor < pop_size:
                new_pop[cursor] = population[ei]
                cursor += 1

        # ── b-d. Selection → Crossover → Mutation ───────────────
        while cursor < pop_size:
            p1 = tournament_select(population, fitnesses, rng)
            p2 = tournament_select(population, fitnesses, rng)

            c1, c2 = crossover(p1, p2, rng, crossover_rate)
            c1 = mutate(c1, rng, mutation_rate)
            c2 = mutate(c2, rng, mutation_rate)

            new_pop[cursor] = c1
            cursor += 1
            if cursor < pop_size:
                new_pop[cursor] = c2
                cursor += 1

        # ── e. Evaluate new generation ──────────────────────────
        population = new_pop
        fitnesses  = _evaluate_population(population, room_types, plot_w, plot_h,
                                           bhk_type, facing, rng)

        # ── f. Convergence tracking ──────────────────────────────
        gen_best = float(np.max(fitnesses))
        if gen_best > best_fitness + _IMPROVEMENT_THRESH:
            best_fitness = gen_best
            stagnation   = 0
        else:
            stagnation  += 1

        if (gen + 1) % 10 == 0 or gen == max_generations - 1:
            div = population_diversity(population)
            logger.debug(
                "  Gen %3d/%d | best=%.4f | avg=%.4f | div=%.3f | stag=%d",
                gen + 1, max_generations,
                gen_best, float(np.mean(fitnesses)),
                div, stagnation,
            )

        if stagnation >= _STAGNATION_LIMIT:
            logger.info("  Early stop at gen %d — stagnation limit reached", gen + 1)
            break

    # ── 3. Extract top-N distinct layouts ────────────────────────
    population, fitnesses = rank_population(population, fitnesses)
    layouts = _extract_top_layouts(
        population, fitnesses,
        room_types, plot_w, plot_h, bhk_type, facing,
        top_n, rng,
    )

    logger.info(
        "GA done | returned %d layouts | best vastu=%.1f%% | best fitness=%.4f",
        len(layouts),
        layouts[0].vastu_score if layouts else 0.0,
        layouts[0].fitness     if layouts else 0.0,
    )
    return layouts


# ════════════════════════════════════════════════════════════════
#  PRIVATE HELPERS
# ════════════════════════════════════════════════════════════════

def _evaluate_population(
    population: np.ndarray,
    room_types: List[str],
    plot_w:     float,
    plot_h:     float,
    bhk_type:   str,
    facing:     str,
    rng:        np.random.Generator,
) -> np.ndarray:
    """
    Evaluate fitness for every chromosome using generate_layout().
    Every layout is guaranteed overlap-free with proper room proportions.
    """
    fitnesses = np.zeros(len(population), dtype=np.float32)
    for i, chrom in enumerate(population):
        try:
            # Use template encoded in chromosome gene[0] for consistent evaluation
            from ga_engine.layout_generator import generate_layout as _gen
            layout = _gen(
                plot_w, plot_h, bhk_type, facing,
                split_ratios=chrom,
                rng=np.random.default_rng(int(rng.integers(1_000_000))),
            )
            fit, _, _, _ = evaluate_fitness(layout.rooms, plot_w, plot_h, facing)
            fitnesses[i] = float(fit)
        except Exception:
            fitnesses[i] = 0.0
    return fitnesses


def _extract_top_layouts(
    population:  np.ndarray,
    fitnesses:   np.ndarray,
    room_types:  List[str],
    plot_w:      float,
    plot_h:      float,
    bhk_type:    str,
    facing:      str,
    top_n:       int,
    rng:         np.random.Generator,
) -> List[Layout]:
    """
    Decode the best chromosomes into Layout objects via generate_layout().
    Enforces diversity: skips chromosomes too similar to already-selected ones.
    """
    layouts:     List[Layout]     = []
    seen_chroms: List[np.ndarray] = []
    MIN_DISTANCE = 0.03           # diversity threshold (lower = more variety)

    for chrom in population:
        if len(layouts) >= top_n:
            break
        if _too_similar(chrom, seen_chroms, MIN_DISTANCE):
            continue
        try:
            # Force different template index for each layout slot
            tidx = len(layouts) % 3
            layout = generate_layout(
                plot_w, plot_h, bhk_type, facing,
                split_ratios=chrom,
                rng=np.random.default_rng(int(rng.integers(1_000_000))),
                template_idx=tidx,
            )
            fit, vastu_pct, space_util, vastu_rules = evaluate_fitness(
                layout.rooms, plot_w, plot_h, facing
            )
            layout.fitness     = round(float(fit),        6)
            layout.vastu_score = round(float(vastu_pct),  2)
            layout.space_util  = round(float(space_util), 2)
            layout.vastu_rules = vastu_rules
            layouts.append(layout)
            seen_chroms.append(chrom)
        except Exception as e:
            logger.debug("Layout decode error: %s", e)

    # Fallback if diversity filter was too aggressive
    if len(layouts) < top_n:
        for chrom in population:
            if len(layouts) >= top_n:
                break
            try:
                layout = generate_layout(
                    plot_w, plot_h, bhk_type, facing,
                    split_ratios=chrom,
                    rng=np.random.default_rng(int(rng.integers(1_000_000))),
                )
                fit, vastu_pct, space_util, vastu_rules = evaluate_fitness(
                    layout.rooms, plot_w, plot_h, facing
                )
                layout.fitness     = round(float(fit),        6)
                layout.vastu_score = round(float(vastu_pct),  2)
                layout.space_util  = round(float(space_util), 2)
                layout.vastu_rules = vastu_rules
                if not any(l.layout_id == layout.layout_id for l in layouts):
                    layouts.append(layout)
            except Exception as e:
                logger.debug("Layout decode error (fallback): %s", e)

    return layouts


def _too_similar(
    chrom:  np.ndarray,
    others: List[np.ndarray],
    thresh: float,
) -> bool:
    """Returns True if chrom is within thresh distance of any in others."""
    for other in others:
        if float(np.linalg.norm(chrom - other)) < thresh:
            return True
    return False