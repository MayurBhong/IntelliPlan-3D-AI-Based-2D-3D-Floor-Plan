# ═══════════════════════════════════════════════════════════════
# utils/helpers.py
# Shared utility functions
# ═══════════════════════════════════════════════════════════════

import uuid
import time
from typing import Tuple


def new_layout_id() -> str:
    """Generate a short unique layout identifier."""
    return f"layout-{uuid.uuid4().hex[:12]}"


def parse_plot_size(plot_size: str) -> Tuple[float, float]:
    """
    Parse a plot size string like '40x60' into (width, height) floats.
    Raises ValueError on bad input.
    """
    try:
        parts = plot_size.lower().split("x")
        if len(parts) != 2:
            raise ValueError
        w, h = float(parts[0]), float(parts[1])
        if w <= 0 or h <= 0:
            raise ValueError
        return w, h
    except (ValueError, AttributeError):
        raise ValueError(
            f"Invalid plot_size '{plot_size}'. Expected format: '40x60'"
        )


def validate_bhk(bhk_type: str) -> str:
    """Validate and normalise BHK type string. Returns uppercase string."""
    valid = {"1BHK", "2BHK", "3BHK", "4BHK"}
    normalised = bhk_type.strip().upper()
    if normalised not in valid:
        raise ValueError(
            f"Invalid bhk_type '{bhk_type}'. Must be one of {sorted(valid)}"
        )
    return normalised


def validate_facing(facing: str) -> str:
    """Validate and normalise facing direction. Returns title-case string."""
    valid = {"North", "East", "South", "West"}
    normalised = facing.strip().capitalize()
    if normalised not in valid:
        raise ValueError(
            f"Invalid facing_direction '{facing}'. Must be one of {sorted(valid)}"
        )
    return normalised


def clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a value between lo and hi."""
    return max(lo, min(hi, value))


def round2(val: float) -> float:
    """Round to 2 decimal places."""
    return round(float(val), 2)


class Timer:
    """Simple wall-clock timer for profiling GA runs."""

    def __init__(self):
        self._start = time.perf_counter()

    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self._start) * 1000)

    def reset(self):
        self._start = time.perf_counter()
