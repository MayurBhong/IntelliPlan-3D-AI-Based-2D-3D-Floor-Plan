# ═══════════════════════════════════════════════════════════════
# ga_engine/operators.py
# Genetic operators: crossover & mutation
#
# Crossover strategies:
#   - Uniform crossover (default) — each gene independently swapped
#   - Single-point crossover      — at gene-block boundaries
#   - Arithmetic crossover        — blend two parents
#
# Mutation strategies:
#   - Gaussian mutation  — add small normal noise to gene values
#   - Room shift         — nudge a random room's position
#   - Room resize        — change a random room's size
#   - Room swap          — swap positions of two rooms
# ═══════════════════════════════════════════════════════════════

import numpy as np
from typing import Tuple, List
from utils.constants import (
    GA_CROSSOVER_RATE,
    GA_MUTATION_RATE,
    ROOM_MIN_SIZES,
    PLOT_MARGIN,
)
from ga_engine.chromosome import GENES_PER_ROOM


# ════════════════════════════════════════
# CROSSOVER
# ════════════════════════════════════════

def uniform_crossover(
    parent1: np.ndarray,
    parent2: np.ndarray,
    rng: np.random.Generator,
    crossover_rate: float = GA_CROSSOVER_RATE,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Uniform crossover at the gene-BLOCK level
    (each room's 4 genes are kept together as a unit).
    """
    if rng.random() > crossover_rate:
        return parent1.copy(), parent2.copy()

    n_rooms = len(parent1) // GENES_PER_ROOM
    c1, c2  = parent1.copy(), parent2.copy()

    for i in range(n_rooms):
        if rng.random() < 0.5:
            base = i * GENES_PER_ROOM
            c1[base:base+GENES_PER_ROOM], c2[base:base+GENES_PER_ROOM] = (
                c2[base:base+GENES_PER_ROOM].copy(),
                c1[base:base+GENES_PER_ROOM].copy(),
            )

    return c1, c2


def single_point_crossover(
    parent1: np.ndarray,
    parent2: np.ndarray,
    rng: np.random.Generator,
    crossover_rate: float = GA_CROSSOVER_RATE,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Single-point crossover at a random room-block boundary.
    """
    if rng.random() > crossover_rate:
        return parent1.copy(), parent2.copy()

    n_rooms  = len(parent1) // GENES_PER_ROOM
    cut_room = rng.integers(1, n_rooms)
    cut_gene = cut_room * GENES_PER_ROOM

    c1 = np.concatenate([parent1[:cut_gene], parent2[cut_gene:]])
    c2 = np.concatenate([parent2[:cut_gene], parent1[cut_gene:]])
    return c1, c2


def arithmetic_crossover(
    parent1: np.ndarray,
    parent2: np.ndarray,
    rng: np.random.Generator,
    crossover_rate: float = GA_CROSSOVER_RATE,
) -> Tuple[np.ndarray, np.ndarray]:
    """Weighted blend crossover."""
    if rng.random() > crossover_rate:
        return parent1.copy(), parent2.copy()
    alpha = rng.uniform(0.3, 0.7)
    c1 = alpha * parent1 + (1.0 - alpha) * parent2
    c2 = (1.0 - alpha) * parent1 + alpha * parent2
    return c1.astype(np.float32), c2.astype(np.float32)


def crossover(
    parent1: np.ndarray,
    parent2: np.ndarray,
    rng: np.random.Generator,
    crossover_rate: float = GA_CROSSOVER_RATE,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Adaptive crossover — randomly chooses operator each time.
    Guarantees children differ from both parents to maintain diversity.
    """
    choice = rng.integers(0, 3)
    if choice == 0:
        c1, c2 = uniform_crossover(parent1, parent2, rng, crossover_rate)
    elif choice == 1:
        c1, c2 = single_point_crossover(parent1, parent2, rng, crossover_rate)
    else:
        c1, c2 = arithmetic_crossover(parent1, parent2, rng, crossover_rate)

    # Guarantee children differ from parents (handles identical-parent edge case)
    if np.array_equal(c1, parent1):
        alpha = rng.uniform(0.05, 0.25)
        c1 = (alpha * parent2 + (1.0 - alpha) * parent1).astype(np.float32)
    if np.array_equal(c2, parent2):
        alpha = rng.uniform(0.05, 0.25)
        c2 = (alpha * parent1 + (1.0 - alpha) * parent2).astype(np.float32)

    return c1, c2


# ════════════════════════════════════════
# MUTATION
# ════════════════════════════════════════

def gaussian_mutation(
    chromosome: np.ndarray,
    rng: np.random.Generator,
    mutation_rate: float = GA_MUTATION_RATE,
    sigma: float = 0.04,
) -> np.ndarray:
    """
    Apply Gaussian noise to each gene independently.
    Genes are clipped to [0, 1] after mutation.
    """
    mutant = chromosome.copy()
    mask   = rng.random(len(mutant)) < mutation_rate
    noise  = rng.normal(0, sigma, size=len(mutant)).astype(np.float32)
    mutant[mask] += noise[mask]
    return np.clip(mutant, 0.0, 1.0)


def room_shift_mutation(
    chromosome: np.ndarray,
    rng: np.random.Generator,
    mutation_rate: float = GA_MUTATION_RATE,
    max_shift: float = 0.12,
) -> np.ndarray:
    """
    Randomly shift one room's position (x, y genes only).
    """
    mutant  = chromosome.copy()
    n_rooms = len(chromosome) // GENES_PER_ROOM

    if rng.random() >= mutation_rate:
        return mutant

    room_idx = rng.integers(0, n_rooms)
    base     = room_idx * GENES_PER_ROOM
    dx = rng.uniform(-max_shift, max_shift)
    dy = rng.uniform(-max_shift, max_shift)
    mutant[base]     = float(np.clip(mutant[base]     + dx, 0.0, 1.0))
    mutant[base + 1] = float(np.clip(mutant[base + 1] + dy, 0.0, 1.0))
    return mutant


def room_resize_mutation(
    chromosome: np.ndarray,
    rng: np.random.Generator,
    mutation_rate: float = GA_MUTATION_RATE,
) -> np.ndarray:
    """
    Randomly resize one room (w, h genes).
    """
    mutant  = chromosome.copy()
    n_rooms = len(chromosome) // GENES_PER_ROOM

    if rng.random() >= mutation_rate:
        return mutant

    room_idx = rng.integers(0, n_rooms)
    base     = room_idx * GENES_PER_ROOM
    dw = rng.uniform(-0.08, 0.08)
    dh = rng.uniform(-0.08, 0.08)
    mutant[base + 2] = float(np.clip(mutant[base + 2] + dw, 0.01, 0.95))
    mutant[base + 3] = float(np.clip(mutant[base + 3] + dh, 0.01, 0.95))
    return mutant


def room_swap_mutation(
    chromosome: np.ndarray,
    rng: np.random.Generator,
    mutation_rate: float = GA_MUTATION_RATE,
) -> np.ndarray:
    """
    Swap the positions of two randomly chosen rooms.
    """
    mutant  = chromosome.copy()
    n_rooms = len(chromosome) // GENES_PER_ROOM

    if n_rooms < 2 or rng.random() >= mutation_rate:
        return mutant

    i, j = rng.choice(n_rooms, size=2, replace=False)
    bi, bj = i * GENES_PER_ROOM, j * GENES_PER_ROOM

    # Swap x, y only (keep sizes)
    mutant[bi], mutant[bj] = float(mutant[bj]), float(mutant[bi])
    mutant[bi+1], mutant[bj+1] = float(mutant[bj+1]), float(mutant[bi+1])
    return mutant


def mutate(
    chromosome: np.ndarray,
    rng: np.random.Generator,
    mutation_rate: float = GA_MUTATION_RATE,
) -> np.ndarray:
    """
    Apply a random combination of mutation operators.
    """
    mutant = gaussian_mutation(chromosome, rng, mutation_rate)
    mutant = room_shift_mutation(mutant, rng, mutation_rate)
    mutant = room_resize_mutation(mutant, rng, mutation_rate * 0.5)
    if rng.random() < 0.25:
        mutant = room_swap_mutation(mutant, rng, mutation_rate)
    return mutant
