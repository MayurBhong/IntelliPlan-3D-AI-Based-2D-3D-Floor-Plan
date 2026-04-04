# ═══════════════════════════════════════════════════════════════
# services/layout_service.py
# Orchestration layer — connects GA engine + Vastu engine
#
# Responsibilities:
#   ▸ Validate & normalise incoming request parameters
#   ▸ Parse plot size string  ("40x60" → width=40, height=60)
#   ▸ Invoke the GA runner
#   ▸ Re-score layouts with the Vastu engine (already done inside
#     fitness.py, but exposed here for re-scoring on demand)
#   ▸ Build the final API response dict
#   ▸ Cache the last N results in memory for PDF export
# ═══════════════════════════════════════════════════════════════

import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

import os
import sys

# ── Ensure backend/ is on path when imported as a module ────────
_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from utils.logger   import get_logger
from utils.helpers  import parse_plot_size, validate_bhk, validate_facing, Timer
from utils.constants import (
    GA_POPULATION_SIZE,
    GA_MAX_GENERATIONS,
    GA_TOP_LAYOUTS_RETURN,
)
from ga_engine.ga_runner        import run_ga
from vastu_engine.vastu_score   import compute_vastu_score
from geometry.layout            import Layout

logger = get_logger(__name__)

# ── In-memory layout store  (layout_id → Layout) ────────────────
# Holds recently generated layouts so the export endpoint can
# fetch them by ID without re-running the GA.
_layout_cache: Dict[str, Layout] = {}
_CACHE_MAX = 50   # evict oldest when limit reached


# ════════════════════════════════════════════════════════════════
#  REQUEST / RESULT DATA CLASSES
# ════════════════════════════════════════════════════════════════

@dataclass
class GenerateRequest:
    """
    Parsed and validated input from POST /api/layout/generate.

    Matches the JSON body sent by the frontend:
        { plot_size, bhk_type, facing_direction }
    """
    plot_size:         str    # raw string e.g. "40x60"
    bhk_type:          str    # "1BHK" | "2BHK" | "3BHK" | "4BHK"
    facing_direction:  str    # "North" | "East" | "South" | "West"

    # Optional GA tuning (not exposed in the current frontend UI)
    pop_size:          int   = GA_POPULATION_SIZE
    max_generations:   int   = GA_MAX_GENERATIONS
    top_n:             int   = GA_TOP_LAYOUTS_RETURN
    seed:              Optional[int] = None

    # ── Derived (populated by LayoutService.validate) ────────────
    plot_w: float = field(init=False, default=0.0)
    plot_h: float = field(init=False, default=0.0)


@dataclass
class GenerateResult:
    """
    Service-layer result returned by LayoutService.generate().
    The Flask route converts this to a JSON response.
    """
    success:       bool
    layouts:       List[Layout]
    count:         int
    elapsed_ms:    int
    error:         Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Produce the exact JSON shape the frontend expects:
            {
              success, count, elapsed_ms,
              layouts: [ { layout_id, rooms, vastu_score, ... }, ... ]
            }
        """
        return {
            "success":    self.success,
            "count":      self.count,
            "elapsed_ms": self.elapsed_ms,
            "layouts":    [l.to_dict() for l in self.layouts],
            "error":      self.error,
        }


# ════════════════════════════════════════════════════════════════
#  LAYOUT SERVICE
# ════════════════════════════════════════════════════════════════

class LayoutService:
    """
    Orchestrates floor plan generation.

    Usage:
        svc = LayoutService()
        result = svc.generate(plot_size="40x60",
                              bhk_type="2BHK",
                              facing_direction="East")
        response_dict = result.to_dict()
    """

    # ── Public API ────────────────────────────────────────────────

    def generate(
        self,
        plot_size:        str,
        bhk_type:         str,
        facing_direction: str,
        pop_size:         int            = GA_POPULATION_SIZE,
        max_generations:  int            = GA_MAX_GENERATIONS,
        top_n:            int            = GA_TOP_LAYOUTS_RETURN,
        seed:             Optional[int]  = None,
    ) -> GenerateResult:
        """
        Validate inputs, run the GA, cache results, return GenerateResult.

        Raises nothing — errors are captured into GenerateResult.error
        so the Flask route can return a clean 400/500 JSON response.
        """
        timer = Timer()

        # ── 1. Validate ──────────────────────────────────────────
        try:
            req = self._validate(
                plot_size, bhk_type, facing_direction,
                pop_size, max_generations, top_n, seed,
            )
        except ValueError as exc:
            logger.warning("Validation error: %s", exc)
            return GenerateResult(
                success=False, layouts=[], count=0,
                elapsed_ms=timer.elapsed_ms(), error=str(exc),
            )

        # ── 2. Run GA ────────────────────────────────────────────
        logger.info(
            "Generate | %s | %s | %s facing | pop=%d gen=%d top=%d",
            req.plot_size, req.bhk_type, req.facing_direction,
            req.pop_size, req.max_generations, req.top_n,
        )
        try:
            layouts = run_ga(
                plot_w          = req.plot_w,
                plot_h          = req.plot_h,
                bhk_type        = req.bhk_type,
                facing          = req.facing_direction,
                pop_size        = req.pop_size,
                max_generations = req.max_generations,
                top_n           = req.top_n,
                seed            = req.seed,
            )
        except Exception as exc:
            logger.exception("GA runner failed: %s", exc)
            return GenerateResult(
                success=False, layouts=[], count=0,
                elapsed_ms=timer.elapsed_ms(),
                error=f"GA engine error: {exc}",
            )

        if not layouts:
            return GenerateResult(
                success=False, layouts=[], count=0,
                elapsed_ms=timer.elapsed_ms(),
                error="GA returned no layouts",
            )

        # ── 3. Cache results ─────────────────────────────────────
        for layout in layouts:
            self._cache_put(layout)

        elapsed = timer.elapsed_ms()
        logger.info(
            "Done | %d layouts | best=%.4f | vastu=%.1f%% | %dms",
            len(layouts),
            layouts[0].fitness,
            layouts[0].vastu_score,
            elapsed,
        )

        return GenerateResult(
            success    = True,
            layouts    = layouts,
            count      = len(layouts),
            elapsed_ms = elapsed,
        )

    def get_layout(self, layout_id: str) -> Optional[Layout]:
        """Retrieve a previously generated layout by ID (for PDF export)."""
        return _layout_cache.get(layout_id)

    def rescore_vastu(self, layout: Layout) -> Layout:
        """
        Re-run the Vastu engine on a layout in-place.
        Useful if rules are updated without re-running the GA.
        """
        score, rules = compute_vastu_score(
            layout.rooms, layout.plot_width, layout.plot_height, layout.facing
        )
        layout.vastu_score = score
        layout.vastu_rules = rules
        return layout

    def list_cached_ids(self) -> List[str]:
        """Return all currently cached layout IDs."""
        return list(_layout_cache.keys())

    # ── Private helpers ───────────────────────────────────────────

    @staticmethod
    def _validate(
        plot_size: str, bhk_type: str, facing_direction: str,
        pop_size: int, max_generations: int, top_n: int,
        seed: Optional[int],
    ) -> GenerateRequest:
        """
        Parse and validate all inputs.  Raises ValueError on bad input.
        """
        # Parse plot size
        plot_w, plot_h = parse_plot_size(plot_size)

        # Sanity-check plot dimensions
        if plot_w < 10 or plot_h < 10:
            raise ValueError(
                f"Plot too small ({plot_w}×{plot_h} ft). Minimum 10×10 ft."
            )
        if plot_w > 500 or plot_h > 500:
            raise ValueError(
                f"Plot too large ({plot_w}×{plot_h} ft). Maximum 500×500 ft."
            )

        # Validate enums
        bhk     = validate_bhk(bhk_type)
        facing  = validate_facing(facing_direction)

        # GA parameter bounds
        pop_size        = max(10, min(200,  int(pop_size)))
        max_generations = max(5,  min(500,  int(max_generations)))
        top_n           = max(1,  min(10,   int(top_n)))

        req         = GenerateRequest(
            plot_size        = plot_size,
            bhk_type         = bhk,
            facing_direction = facing,
            pop_size         = pop_size,
            max_generations  = max_generations,
            top_n            = top_n,
            seed             = seed,
        )
        req.plot_w = plot_w
        req.plot_h = plot_h
        return req

    @staticmethod
    def _cache_put(layout: Layout) -> None:
        """Insert layout into the in-memory cache; evict oldest if needed."""
        global _layout_cache
        if len(_layout_cache) >= _CACHE_MAX:
            # Evict the oldest entry (first inserted — dict preserves order)
            oldest_key = next(iter(_layout_cache))
            del _layout_cache[oldest_key]
        _layout_cache[layout.layout_id] = layout