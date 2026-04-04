# ═══════════════════════════════════════════════════════════════
# vastu_engine/direction_utils.py
# Plot zone detection and directional utilities for Vastu analysis
# ═══════════════════════════════════════════════════════════════

from typing import Tuple
from geometry.room import Room


# ── Cardinal zone fractions of the plot ────────────────────────
#   The plot is divided into a 3×3 Vastu Mandala grid.
#   Each zone spans 1/3 of the plot width/height.
#
#   NW  | N   | NE
#   ────+─────+────
#   W   | C   | E
#   ────+─────+────
#   SW  | S   | SE
#
ZONE_THIRD = 1 / 3


def get_room_zone(
    room: Room, plot_w: float, plot_h: float, facing: str
) -> str:
    """
    Determine which Vastu zone (N/NE/E/SE/S/SW/W/NW/C) a room
    primarily occupies based on its centre point.

    The coordinate system is:
      x=0, y=0 → top-left corner of the plot (facing side)
      x increases to the right (East of the facing side)
      y increases downward (South of the facing side)

    The zone labels are ABSOLUTE (North/South/East/West) and depend
    on the plot's facing direction.
    """
    cx_rel = room.center_x / plot_w   # 0–1 left to right
    cy_rel = room.center_y / plot_h   # 0–1 top to bottom

    # Raw zone in local coordinates (top=front)
    if cy_rel < ZONE_THIRD:
        row = "front"
    elif cy_rel < 2 * ZONE_THIRD:
        row = "mid"
    else:
        row = "back"

    if cx_rel < ZONE_THIRD:
        col = "left"
    elif cx_rel < 2 * ZONE_THIRD:
        col = "centre"
    else:
        col = "right"

    return _local_to_cardinal(row, col, facing)


def _local_to_cardinal(row: str, col: str, facing: str) -> str:
    """
    Map local (front/mid/back × left/centre/right) coordinates
    to cardinal Vastu zones based on the facing direction.

    facing=North  → front=North, right=East
    facing=East   → front=East,  right=South
    facing=South  → front=South, right=West
    facing=West   → front=West,  right=North
    """
    # (row, col) → (lat_axis, lon_axis)
    # lat_axis: front→+N, back→+S  (for North-facing)
    # We rotate by facing direction.

    MAPPING = {
        # facing: { (row, col): zone }
        "North": {
            ("front",  "left"):    "NW",
            ("front",  "centre"):  "N",
            ("front",  "right"):   "NE",
            ("mid",    "left"):    "W",
            ("mid",    "centre"):  "C",
            ("mid",    "right"):   "E",
            ("back",   "left"):    "SW",
            ("back",   "centre"):  "S",
            ("back",   "right"):   "SE",
        },
        "East": {
            ("front",  "left"):    "NE",
            ("front",  "centre"):  "E",
            ("front",  "right"):   "SE",
            ("mid",    "left"):    "N",
            ("mid",    "centre"):  "C",
            ("mid",    "right"):   "S",
            ("back",   "left"):    "NW",
            ("back",   "centre"):  "W",
            ("back",   "right"):   "SW",
        },
        "South": {
            ("front",  "left"):    "SE",
            ("front",  "centre"):  "S",
            ("front",  "right"):   "SW",
            ("mid",    "left"):    "E",
            ("mid",    "centre"):  "C",
            ("mid",    "right"):   "W",
            ("back",   "left"):    "NE",
            ("back",   "centre"):  "N",
            ("back",   "right"):   "NW",
        },
        "West": {
            ("front",  "left"):    "SW",
            ("front",  "centre"):  "W",
            ("front",  "right"):   "NW",
            ("mid",    "left"):    "S",
            ("mid",    "centre"):  "C",
            ("mid",    "right"):   "N",
            ("back",   "left"):    "SE",
            ("back",   "centre"):  "E",
            ("back",   "right"):   "NE",
        },
    }

    facing_cap = facing.capitalize()
    return MAPPING.get(facing_cap, MAPPING["North"]).get((row, col), "C")


def is_in_zone(room: Room, plot_w: float, plot_h: float,
               facing: str, target_zones: Tuple[str, ...]) -> bool:
    """
    Returns True if the room's zone is one of the target_zones.
    """
    zone = get_room_zone(room, plot_w, plot_h, facing)
    return zone in target_zones


def cardinal_to_description(zone: str) -> str:
    """Human-readable zone description."""
    return {
        "N":  "North zone",    "NE": "North-East corner",
        "E":  "East zone",     "SE": "South-East zone",
        "S":  "South zone",    "SW": "South-West zone",
        "W":  "West zone",     "NW": "North-West zone",
        "C":  "Centre",
    }.get(zone, zone)
