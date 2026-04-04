# ═══════════════════════════════════════════════════════════════
# geometry/overlap.py
# Collision / overlap detection between rooms
# ═══════════════════════════════════════════════════════════════

from typing import List, Tuple
from .room import Room


def overlap_area(a: Room, b: Room) -> float:
    """
    Return the overlapping rectangular area (in sq-ft) between rooms a and b.
    Returns 0.0 if they don't overlap.
    """
    x_overlap = max(0.0, min(a.right, b.right) - max(a.x, b.x))
    y_overlap = max(0.0, min(a.bottom, b.bottom) - max(a.y, b.y))
    return round(x_overlap * y_overlap, 4)


def total_overlap_area(rooms: List[Room]) -> float:
    """
    Sum of all pairwise overlap areas among a list of rooms.
    Used as a penalty term in the fitness function.
    """
    total = 0.0
    n = len(rooms)
    for i in range(n):
        for j in range(i + 1, n):
            total += overlap_area(rooms[i], rooms[j])
    return round(total, 4)


def has_any_overlap(rooms: List[Room], tol: float = 0.1) -> bool:
    """Quick check: returns True if any two rooms overlap beyond tolerance."""
    n = len(rooms)
    for i in range(n):
        for j in range(i + 1, n):
            if rooms[i].overlaps(rooms[j], tol):
                return True
    return False


def overlapping_pairs(rooms: List[Room], tol: float = 0.1) -> List[Tuple[int, int]]:
    """Return list of (i, j) index pairs for overlapping rooms."""
    pairs = []
    n = len(rooms)
    for i in range(n):
        for j in range(i + 1, n):
            if rooms[i].overlaps(rooms[j], tol):
                pairs.append((i, j))
    return pairs


def overlap_penalty(rooms: List[Room], plot_area: float) -> float:
    """
    Normalised overlap penalty in [0, 1].
    0 = no overlaps (best), 1 = entire plot is overlapping (worst).
    """
    if plot_area <= 0:
        return 0.0
    oa = total_overlap_area(rooms)
    return min(1.0, oa / plot_area)
