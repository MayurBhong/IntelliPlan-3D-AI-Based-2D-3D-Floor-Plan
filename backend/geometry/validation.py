# ═══════════════════════════════════════════════════════════════
# geometry/validation.py
# Boundary & constraint validation for rooms and layouts
# ═══════════════════════════════════════════════════════════════

from typing import List, Tuple
from .room import Room
from utils.constants import ROOM_MIN_SIZES, PLOT_MARGIN


def room_within_bounds(room: Room, plot_w: float, plot_h: float) -> bool:
    """True if the room fits entirely within the plot boundary."""
    return (
        room.x >= 0 and
        room.y >= 0 and
        room.right  <= plot_w and
        room.bottom <= plot_h
    )


def room_meets_min_size(room: Room) -> bool:
    """True if the room meets the minimum size requirement for its type."""
    min_w, min_h = ROOM_MIN_SIZES.get(room.type, (3.0, 3.0))
    return room.width >= min_w and room.height >= min_h


def layout_boundary_violations(
    rooms: List[Room], plot_w: float, plot_h: float
) -> List[int]:
    """Return indices of rooms that exceed plot boundaries."""
    return [
        i for i, r in enumerate(rooms)
        if not room_within_bounds(r, plot_w, plot_h)
    ]


def layout_size_violations(rooms: List[Room]) -> List[int]:
    """Return indices of rooms that are below minimum size."""
    return [i for i, r in enumerate(rooms) if not room_meets_min_size(r)]


def space_utilisation(rooms: List[Room], plot_w: float, plot_h: float) -> float:
    """
    Fraction of the plot area covered by rooms, clamped to [0, 1].
    (Does not subtract PLOT_MARGIN — raw utilisation.)
    """
    plot_area = plot_w * plot_h
    if plot_area <= 0:
        return 0.0
    covered = sum(r.area for r in rooms)
    return min(1.0, covered / plot_area)


def aspect_ratio_score(rooms: List[Room]) -> float:
    """
    Average aspect-ratio quality score across all rooms [0, 1].
    A perfect square = 1.0; extreme elongation → approaches 0.
    """
    if not rooms:
        return 0.0
    scores = []
    for r in rooms:
        ar = r.aspect_ratio   # >= 1
        # Penalise ratios > 3:1 heavily; ideal is 1–2
        if ar <= 2.0:
            score = 1.0
        elif ar <= 3.5:
            score = 1.0 - (ar - 2.0) / 3.0
        else:
            score = 0.0
        scores.append(score)
    return round(sum(scores) / len(scores), 4)


def is_valid_layout(
    rooms: List[Room], plot_w: float, plot_h: float
) -> Tuple[bool, str]:
    """
    Full validity check. Returns (is_valid, reason_string).
    """
    if not rooms:
        return False, "No rooms in layout"
    bv = layout_boundary_violations(rooms, plot_w, plot_h)
    if bv:
        return False, f"{len(bv)} room(s) out of bounds"
    sv = layout_size_violations(rooms)
    if sv:
        return False, f"{len(sv)} room(s) below minimum size"
    return True, "OK"
