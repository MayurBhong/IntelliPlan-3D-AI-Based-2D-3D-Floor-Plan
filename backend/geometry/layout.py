# ═══════════════════════════════════════════════════════════════
# geometry/layout.py
# Layout container — holds all rooms + metadata for one solution
# ═══════════════════════════════════════════════════════════════

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from .room import Room
from utils.helpers import new_layout_id


@dataclass
class Layout:
    """
    A complete floor plan: a set of rooms placed within a plot.
    Fitness and Vastu scores are populated by the GA fitness function.
    """

    plot_width:  float
    plot_height: float
    facing:      str
    bhk_type:    str
    rooms:       List[Room]         = field(default_factory=list)
    layout_id:   str                = field(default_factory=new_layout_id)

    # Scores — filled in by fitness.py / vastu_score.py
    fitness:     float              = 0.0
    vastu_score: float              = 0.0   # 0-100
    space_util:  float              = 0.0   # 0-100
    vastu_rules: List[Dict]         = field(default_factory=list)

    # ── Derived properties ─────────────────────────────────────

    @property
    def usable_area(self) -> float:
        from utils.constants import PLOT_MARGIN as M
        iw = max(0.0, self.plot_width  - 2 * M)
        ih = max(0.0, self.plot_height - 2 * M)
        return round(iw * ih, 2)

    @property
    def total_room_area(self) -> float:
        return round(sum(r.area for r in self.rooms), 2)

    # ── Serialisation ──────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        """
        Produce the exact JSON shape the frontend expects.
        See buildLocalPlan() in script.js for the reference schema.
        """
        return {
            "layout_id":       self.layout_id,
            "rooms":           [r.to_dict() for r in self.rooms],
            "vastu_score":     round(self.vastu_score, 2),
            "fitness":         round(self.fitness, 6),
            "space_util":      round(self.space_util, 2),
            "total_room_area": self.total_room_area,
            "vastu_rules":     self.vastu_rules,
            "plot_shape":      getattr(self, "plot_shape",   "rect"),
            "plot_polygon":    getattr(self, "plot_polygon", None),
            "plot_zones":      getattr(self, "plot_zones",   None),
            "plot": {
                "width":       self.plot_width,
                "height":      self.plot_height,
                "facing":      self.facing,
                "bhk_type":    self.bhk_type,
                "usable_area": self.usable_area,
            },
        }

    def clone(self) -> "Layout":
        """Deep-copy this layout (used by GA operators)."""
        import copy
        new = Layout(
            plot_width  = self.plot_width,
            plot_height = self.plot_height,
            facing      = self.facing,
            bhk_type    = self.bhk_type,
            rooms       = [copy.copy(r) for r in self.rooms],
        )
        return new

    def __repr__(self) -> str:
        return (
            f"Layout({self.bhk_type}, {self.plot_width}×{self.plot_height}ft, "
            f"rooms={len(self.rooms)}, vastu={self.vastu_score:.1f}%, "
            f"fitness={self.fitness:.4f})"
        )