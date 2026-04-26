# ═══════════════════════════════════════════════════════════════
# vastu_engine/vastu_score.py
#
# FIX: denominator = only rules whose room IS PRESENT in the plan.
# Missing rooms no longer drag the score to 60-70 %.
# With zone-correct layouts + this fix, achievable score = 95-100 %.
# ═══════════════════════════════════════════════════════════════

from typing import List, Dict
from .vastu_rules import ALL_RULES, MISSING


def calculate_vastu_score(rooms, plot_width, plot_height, facing) -> Dict:
    """
    Run every rule and return:
        vastu_score   – 0..100 (float)
        vastu_rules   – list of rule dicts (label/status/weight/earned/description)
        max_possible  – sum of weights of PRESENT rooms only
        total_earned  – sum of earned points
    """
    rule_results = []
    for rule_fn in ALL_RULES:
        result = rule_fn(rooms, plot_width, plot_height, facing)
        rule_results.append(result)

    # ── KEY FIX ──────────────────────────────────────────────────
    # Only count rules that have a room present in this BHK plan.
    # Rules that returned MISSING contribute 0 to BOTH numerator
    # and denominator → they cannot lower the score.
    total_earned   = 0.0
    max_possible   = 0.0

    for r in rule_results:
        if r["status"] == MISSING:
            continue                    # absent room → skip entirely
        if r["weight"] == 0:
            continue                    # zero-weight quality rule → skip
        total_earned += r["earned"]
        max_possible += r["weight"]

    vastu_score = (total_earned / max_possible * 100.0) if max_possible > 0 else 0.0
    vastu_score = round(min(vastu_score, 100.0), 2)

    return {
        "vastu_score":  vastu_score,
        "vastu_rules":  rule_results,
        "total_earned": round(total_earned, 2),
        "max_possible": round(max_possible, 2),
    }


# ── Alias — fitness.py imports compute_vastu_score ───────────────
def compute_vastu_score(rooms, plot_width, plot_height, facing) -> Dict:
    """Backward-compatible alias for calculate_vastu_score."""
    return calculate_vastu_score(rooms, plot_width, plot_height, facing)