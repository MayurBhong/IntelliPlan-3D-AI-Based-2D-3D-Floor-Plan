# ═══════════════════════════════════════════════════════════════
# ga_engine/population.py
# Population initialisation for the GA
# ═══════════════════════════════════════════════════════════════

import numpy as np
from typing import List
from .chromosome import random_chromosome, chromosome_length


def initialise_population(
    pop_size: int,
    room_types: List[str],
    plot_w: float,
    plot_h: float,
    seed: int = None,
) -> np.ndarray:
    """
    Create an initial population of `pop_size` random chromosomes.

    Returns:
        population — shape (pop_size, chromosome_length)
    """
    rng = np.random.default_rng(seed)
    chrom_len = chromosome_length(len(room_types))
    population = np.zeros((pop_size, chrom_len), dtype=np.float32)

    for i in range(pop_size):
        population[i] = random_chromosome(room_types, plot_w, plot_h, rng)

    return population


def population_diversity(population: np.ndarray) -> float:
    """
    Measure population diversity as mean pairwise Euclidean distance.
    Higher = more diverse. Used for monitoring GA health.
    """
    if len(population) < 2:
        return 0.0
    # Sample up to 20 pairs to keep it fast
    n = min(20, len(population))
    idx = np.random.choice(len(population), n, replace=False)
    sample = population[idx]
    dists = []
    for i in range(n):
        for j in range(i + 1, n):
            dists.append(np.linalg.norm(sample[i] - sample[j]))
    return float(np.mean(dists)) if dists else 0.0
