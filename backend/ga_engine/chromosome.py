# ═══════════════════════════════════════════════════════════════
# ga_engine/chromosome.py
# Chromosome representation for the GA
#
# Encoding strategy:
#   A chromosome is a flat list of floats, one "gene block" per room.
#   Each gene block = [x_frac, y_frac, w_frac, h_frac]  (fractions of plot)
#   so the chromosome length = num_rooms × 4.
# ═══════════════════════════════════════════════════════════════

import numpy as np
from typing import List, Tuple
from geometry.room import Room
from utils.constants import ROOM_MIN_SIZES, PLOT_MARGIN


GENES_PER_ROOM = 4   # x_frac, y_frac, w_frac, h_frac


def encode(rooms: List[Room], plot_w: float, plot_h: float) -> np.ndarray:
    """
    Encode a list of Room objects into a flat numpy float array.
    All values are in the range [0, 1] (fractions of plot dimensions).
    """
    genes = []
    for room in rooms:
        genes.extend([
            room.x      / plot_w,
            room.y      / plot_h,
            room.width  / plot_w,
            room.height / plot_h,
        ])
    return np.array(genes, dtype=np.float32)


def decode(
    chromosome: np.ndarray,
    room_types: List[str],
    plot_w: float,
    plot_h: float,
) -> List[Room]:
    """
    Decode a flat gene array back into Room objects.
    Applies minimum-size clamping so rooms never go below ROOM_MIN_SIZES.
    """
    rooms = []
    for i, room_type in enumerate(room_types):
        base = i * GENES_PER_ROOM
        x_frac = float(chromosome[base])
        y_frac = float(chromosome[base + 1])
        w_frac = float(chromosome[base + 2])
        h_frac = float(chromosome[base + 3])

        # De-normalise
        x = x_frac * plot_w
        y = y_frac * plot_h
        w = w_frac * plot_w
        h = h_frac * plot_h

        # Enforce minimum sizes
        min_w, min_h = ROOM_MIN_SIZES.get(room_type, (3.0, 3.0))
        w = max(w, min_w)
        h = max(h, min_h)

        # Clamp to plot
        x = np.clip(x, 0, plot_w - w)
        y = np.clip(y, 0, plot_h - h)

        rooms.append(Room(type=room_type, x=x, y=y, width=w, height=h))

    return rooms


def chromosome_length(num_rooms: int) -> int:
    return num_rooms * GENES_PER_ROOM


def random_chromosome(
    room_types: List[str],
    plot_w: float,
    plot_h: float,
    rng: np.random.Generator,
) -> np.ndarray:
    """
    Generate a random valid chromosome with rooms distributed across the plot.
    Uses a simple grid-based initialisation to avoid extreme overlaps.
    """
    from utils.constants import PLOT_MARGIN as M
    n = len(room_types)
    genes = np.zeros(n * GENES_PER_ROOM, dtype=np.float32)

    # Grid layout for initial placement
    cols = max(1, int(np.ceil(np.sqrt(n))))
    rows = max(1, int(np.ceil(n / cols)))

    cell_w = (plot_w - 2 * M) / cols
    cell_h = (plot_h - 2 * M) / rows

    for i, room_type in enumerate(room_types):
        row_idx = i // cols
        col_idx = i  % cols

        min_w, min_h = ROOM_MIN_SIZES.get(room_type, (3.0, 3.0))

        # Random size within cell, respecting minimums
        max_w = max(min_w, cell_w * rng.uniform(0.55, 0.92))
        max_h = max(min_h, cell_h * rng.uniform(0.55, 0.92))

        # Random position within the cell
        cell_x = M + col_idx * cell_w
        cell_y = M + row_idx * cell_h
        x = cell_x + rng.uniform(0, max(0, cell_w - max_w))
        y = cell_y + rng.uniform(0, max(0, cell_h - max_h))

        # Clamp to plot
        x = np.clip(x, 0, plot_w - max_w)
        y = np.clip(y, 0, plot_h - max_h)

        base = i * GENES_PER_ROOM
        genes[base]     = x      / plot_w
        genes[base + 1] = y      / plot_h
        genes[base + 2] = max_w  / plot_w
        genes[base + 3] = max_h  / plot_h

    return genes
