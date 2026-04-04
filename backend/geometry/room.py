# ═══════════════════════════════════════════════════════════════
# geometry/room.py
# Room data class — the atomic building block of a floor plan
# ═══════════════════════════════════════════════════════════════

from dataclasses import dataclass, field
from typing import Dict, Any
from utils.constants import ROOM_LABELS


@dataclass
class Room:
    """
    Represents a single rectangular room placed on a plot.

    Coordinates are in feet, measured from the top-left corner of the plot.
    x, y → top-left corner of the room
    width, height → dimensions in ft
    """

    type:   str         # e.g. "kitchen", "master_bedroom"
    x:      float       # left edge (ft from plot origin)
    y:      float       # top edge  (ft from plot origin)
    width:  float       # ft
    height: float       # ft

    @property
    def label(self) -> str:
        """Human-readable room label."""
        return ROOM_LABELS.get(self.type, self.type.replace("_", " ").title())

    @property
    def area(self) -> float:
        return round(self.width * self.height, 2)

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2

    @property
    def aspect_ratio(self) -> float:
        """width / height, always >= 1."""
        if self.height == 0:
            return 999.0
        r = self.width / self.height
        return r if r >= 1.0 else 1.0 / r

    def overlaps(self, other: "Room", tol: float = 0.1) -> bool:
        """
        Returns True if this room overlaps with another.
        tol = tolerance in ft to allow shared walls.
        """
        return (
            self.x + tol   < other.right  and
            other.x + tol  < self.right   and
            self.y + tol   < other.bottom and
            other.y + tol  < self.bottom
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialise to the JSON structure expected by the frontend.
        Matches exactly what buildLocalPlan() returns in script.js.
        """
        return {
            "type":   self.type,
            "label":  self.label,
            "x":      round(self.x,      2),
            "y":      round(self.y,      2),
            "w":      round(self.width,  2),   # kept for backward compat
            "h":      round(self.height, 2),   # kept for backward compat
            "width":  round(self.width,  2),
            "height": round(self.height, 2),
            "area":   self.area,
        }

    def __repr__(self) -> str:
        return (
            f"Room({self.type!r}, x={self.x:.1f}, y={self.y:.1f}, "
            f"w={self.width:.1f}, h={self.height:.1f})"
        )
