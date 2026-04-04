# ═══════════════════════════════════════════════════════════════
# vastu_engine/vastu_score.py
# Aggregate Vastu scoring — runs all rules and computes 0-100 score
# ═══════════════════════════════════════════════════════════════

from typing import List, Dict, Any, Tuple
from geometry.room import Room
from .vastu_rules import ALL_RULES


def compute_vastu_score(
    rooms: List[Room],
    plot_w: float,
    plot_h: float,
    facing: str,
) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Run all Vastu rules against the given room set.

    Returns:
        vastu_score  — float in [0, 100]
        rule_results — list of rule dicts for the frontend
    """
    rule_results = [
        rule(rooms, plot_w, plot_h, facing) for rule in ALL_RULES
    ]

    total_weight = sum(r["weight"] for r in rule_results)
    total_earned = sum(r["earned"] for r in rule_results)

    if total_weight == 0:
        vastu_score = 0.0
    else:
        vastu_score = round((total_earned / total_weight) * 100, 2)

    # Clamp to [0, 100]
    vastu_score = max(0.0, min(100.0, vastu_score))

    return vastu_score, rule_results
