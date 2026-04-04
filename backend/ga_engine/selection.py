# ═══════════════════════════════════════════════════════════════
# ga_engine/selection.py
# Selection strategies: tournament selection + elitism
# ═══════════════════════════════════════════════════════════════

import numpy as np
from typing import Tuple
from utils.constants import GA_TOURNAMENT_SIZE, GA_ELITISM_COUNT


def tournament_select(
    population: np.ndarray,
    fitnesses: np.ndarray,
    rng: np.random.Generator,
    tournament_size: int = GA_TOURNAMENT_SIZE,
) -> np.ndarray:
    """
    Tournament selection: randomly pick `tournament_size` individuals,
    return the one with the highest fitness.
    """
    n = len(population)
    candidates = rng.choice(n, size=tournament_size, replace=False)
    best_idx = candidates[np.argmax(fitnesses[candidates])]
    return population[best_idx].copy()


def select_parents(
    population: np.ndarray,
    fitnesses: np.ndarray,
    rng: np.random.Generator,
    tournament_size: int = GA_TOURNAMENT_SIZE,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Select two distinct parents via tournament selection.
    Returns (parent1, parent2).
    """
    p1 = tournament_select(population, fitnesses, rng, tournament_size)
    p2 = tournament_select(population, fitnesses, rng, tournament_size)
    return p1, p2


def elitism_indices(
    fitnesses: np.ndarray,
    elitism_count: int = GA_ELITISM_COUNT,
) -> np.ndarray:
    """
    Return indices of the top `elitism_count` chromosomes
    sorted by descending fitness (best first).
    """
    return np.argsort(fitnesses)[::-1][:elitism_count]


def rank_population(
    population: np.ndarray,
    fitnesses: np.ndarray,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Return (population, fitnesses) sorted by descending fitness.
    """
    order = np.argsort(fitnesses)[::-1]
    return population[order], fitnesses[order]
