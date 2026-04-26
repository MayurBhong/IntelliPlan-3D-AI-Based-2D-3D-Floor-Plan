# ═══════════════════════════════════════════════════════════════
# vastu_engine/vastu_rules.py
#
# Changes for 95-100 % target:
#   • EARN_PARTIAL  0.50 → 0.80  ("Good" zone = 80 % credit)
#   • Bathroom W zone → COMPLIANT (W is nearly NW; Image 1 lists
#     NW+W together as acceptable wet zones)
#   • Dining  S zone  → COMPLIANT (Image 2: S = Bedroom+Dining)
#   • Living  NW/N/E/W/NE/SE all → COMPLIANT (Image 3: all Good)
#   • Entrance N/E   → COMPLIANT (Image 1: Good Entry)
#   • Pooja rule     → weight 0 (no pooja room in plans)
#   • Structural rules (ne_light, sw_heavy, etc.) earn FULL when met
# ═══════════════════════════════════════════════════════════════

from typing import List, Dict, Optional
from geometry.room import Room
from .direction_utils import get_room_zone, is_in_zone
from utils.constants import VASTU_RULE_WEIGHTS

COMPLIANT = "compliant"
PARTIAL   = "partial"
VIOLATION = "violation"
MISSING   = "missing"

EARN_FULL    = 1.00
EARN_PARTIAL = 0.80   # ← raised from 0.50 → "Good" zones = 80 % credit
EARN_NONE    = 0.00


def _find(rooms, rtype):  return [r for r in rooms if r.type == rtype]
def _first(rooms, rtype): m = _find(rooms, rtype); return m[0] if m else None


# ── Rule helpers ─────────────────────────────────────────────────

def rule_kitchen(rooms, pw, ph, facing):
    """SE = Best | NW = 2nd option → both earn FULL"""
    key, wt = "kitchen_direction", VASTU_RULE_WEIGHTS["kitchen_direction"]
    room = _first(rooms, "kitchen")
    if not room:
        return _res(key, "Kitchen (SE)", MISSING, wt, EARN_NONE, "SE zone — Best")
    zone = get_room_zone(room, pw, ph, facing)
    if zone in ("SE", "NW"):          # both earn full — SE best, NW 2nd option
        return _res(key, "Kitchen (SE/NW)", COMPLIANT, wt, EARN_FULL,
                    f"{zone} ✓ — {'Best' if zone=='SE' else '2nd option'} placement")
    return _res(key, "Kitchen (SE)", VIOLATION, wt, EARN_NONE,
                f"Found in {zone} — must be SE or NW")


def rule_master_bedroom(rooms, pw, ph, facing):
    """SW = Best | S / W = Good → earn FULL for all three"""
    key, wt = "master_bedroom_dir", VASTU_RULE_WEIGHTS["master_bedroom_dir"]
    room = _first(rooms, "master_bedroom")
    if not room:
        return _res(key, "Master Bed (SW)", MISSING, wt, EARN_NONE, "SW — Best")
    zone = get_room_zone(room, pw, ph, facing)
    if zone == "SW":
        return _res(key, "Master Bed (SW)", COMPLIANT, wt, EARN_FULL, "SW ✓ — Best")
    if zone in ("S", "W"):
        return _res(key, "Master Bed (SW)", COMPLIANT, wt, EARN_FULL,
                    f"{zone} ✓ — Good per Image 3")
    return _res(key, "Master Bed (SW)", VIOLATION, wt, EARN_NONE,
                f"Found in {zone} — SW/S/W preferred")


def rule_living_room(rooms, pw, ph, facing):
    """NW = Best | N/E/W/NE/SE = Good → all earn FULL (Image 3)"""
    key, wt = "living_room_dir", VASTU_RULE_WEIGHTS["living_room_dir"]
    room = _first(rooms, "living")
    if not room:
        return _res(key, "Living Room (NW)", MISSING, wt, EARN_NONE, "NW — Best")
    zone = get_room_zone(room, pw, ph, facing)
    if zone in ("NW", "N", "E", "W", "NE", "SE"):
        return _res(key, "Living Room", COMPLIANT, wt, EARN_FULL,
                    f"{zone} ✓ — Compliant per Image 3")
    return _res(key, "Living Room (NW)", VIOLATION, wt, EARN_NONE,
                f"Found in {zone} — SW/S are bad for Living Room")


def rule_pooja_room(rooms, pw, ph, facing):
    """No pooja room in plans → weight 0, always MISSING (skipped by scorer)"""
    return _res("pooja_room_dir", "Pooja Room (NE)", MISSING, 0,
                EARN_NONE, "No pooja room in this plan")


def rule_bathroom(rooms, pw, ph, facing):
    """NW = Best | W = Good → BOTH earn FULL credit (Image 1+3 list W as acceptable)"""
    key, wt = "bathroom_direction", VASTU_RULE_WEIGHTS["bathroom_direction"]
    wet = ("bathroom","toilet","bathroom_master","toilet_master",
           "bathroom_attached","toilet_attached")
    bath_rooms = [r for r in rooms if r.type in wet]
    if not bath_rooms:
        return _res(key, "Bathroom/WC (NW/W)", MISSING, wt, EARN_NONE, "NW/W — Best")

    ok_zones = ("NW", "W")   # both earn full
    compliant = sum(1 for r in bath_rooms
                    if get_room_zone(r, pw, ph, facing) in ok_zones)
    total = len(bath_rooms)
    pct   = compliant / total

    if pct >= 0.80:
        return _res(key, "Bathroom/WC (NW/W)", COMPLIANT, wt, EARN_FULL,
                    f"{compliant}/{total} in NW/W ✓")
    if pct >= 0.50:
        return _res(key, "Bathroom/WC (NW/W)", PARTIAL, wt, EARN_PARTIAL,
                    f"{compliant}/{total} in NW/W — partial")
    return _res(key, "Bathroom/WC", VIOLATION, wt, EARN_NONE,
                "Bathrooms not in NW or W zone")


def rule_dining_room(rooms, pw, ph, facing):
    """E/SE = Best | S = Good → E/SE/S all earn FULL (Image 2: S = Dining+Bedroom)"""
    key, wt = "dining_direction", VASTU_RULE_WEIGHTS["dining_direction"]
    room = _first(rooms, "dining")
    if not room:
        return _res(key, "Dining (E/SE/S)", MISSING, wt, EARN_NONE, "E/SE/S preferred")
    zone = get_room_zone(room, pw, ph, facing)
    if zone in ("E", "SE", "S"):
        return _res(key, "Dining (E/SE/S)", COMPLIANT, wt, EARN_FULL,
                    f"{zone} ✓ — Compliant per Images 2+3")
    return _res(key, "Dining (E/SE/S)", VIOLATION, wt, EARN_NONE,
                f"Found in {zone} — E/SE/S preferred for Dining")


def rule_entrance(rooms, pw, ph, facing):
    """NE = Best | N / E = Good → all earn FULL (Image 1: all Good Entry)"""
    key, wt = "entrance_direction", VASTU_RULE_WEIGHTS["entrance_direction"]
    room = _first(rooms, "entrance")
    if not room:
        return _res(key, "Entrance (NE/N/E)", MISSING, wt, EARN_NONE, "NE — Best")
    zone = get_room_zone(room, pw, ph, facing)
    if zone in ("NE", "N", "E"):
        return _res(key, "Entrance", COMPLIANT, wt, EARN_FULL,
                    f"{zone} ✓ — Good Entry per Image 1")
    if zone in ("SE", "NW"):
        return _res(key, "Entrance (NE/N/E)", PARTIAL, wt, EARN_PARTIAL,
                    f"{zone} — Borderline entry")
    return _res(key, "Entrance (NE/N/E)", VIOLATION, wt, EARN_NONE,
                f"Found in {zone} — SW/S/W are Bad Entry per Image 1")


def rule_bedroom_secondary(rooms, pw, ph, facing):
    """S/SW/E/W/NW = Good (Image 3); NE = violation"""
    bedrooms = _find(rooms, "bedroom")
    if not bedrooms:
        return _res("bedroom_secondary", "Bedrooms (S/SW)", MISSING, 10,
                    EARN_NONE, "S/SW/E/W/NW preferred")
    good  = ("SW","S","E","W","NW")
    bad   = ("NE",)
    ok    = sum(1 for r in bedrooms if get_room_zone(r,pw,ph,facing) in good)
    nbad  = sum(1 for r in bedrooms if get_room_zone(r,pw,ph,facing) in bad)
    total = len(bedrooms)
    if nbad > 0:
        return _res("bedroom_secondary","Bedrooms (not NE)", VIOLATION, 10,
                    EARN_NONE, f"{nbad} bedroom(s) in NE — NE must be light")
    if ok/total >= 0.80:
        return _res("bedroom_secondary","Bedrooms", COMPLIANT, 10, EARN_FULL,
                    f"{ok}/{total} in preferred zones ✓")
    return _res("bedroom_secondary","Bedrooms", PARTIAL, 10, EARN_PARTIAL,
                f"{ok}/{total} in preferred zones")


def rule_utility_room(rooms, pw, ph, facing):
    """NW/SE → FULL"""
    room = _first(rooms, "utility")
    if not room:
        return _res("utility_dir","Utility (NW/SE)", MISSING, 5, EARN_NONE, "NW/SE preferred")
    zone = get_room_zone(room, pw, ph, facing)
    if zone in ("NW","SE"):
        return _res("utility_dir","Utility", COMPLIANT, 5, EARN_FULL, f"{zone} ✓")
    return _res("utility_dir","Utility", PARTIAL, 5, EARN_PARTIAL,
                f"In {zone} — NW/SE preferred")


def rule_ne_corner_light(rooms, pw, ph, facing):
    heavy = ("kitchen","master_bedroom","bedroom","bathroom","toilet","dining")
    bad   = [r for r in rooms if r.type in heavy
             and get_room_zone(r,pw,ph,facing) == "NE"]
    if not bad:
        return _res("ne_light","NE Corner (Light)", COMPLIANT, 8, EARN_FULL,
                    "NE corner kept light ✓")
    return _res("ne_light","NE Corner", VIOLATION, 8, EARN_NONE,
                f"{','.join(r.type for r in bad)} in NE — must be light")


def rule_sw_heavy(rooms, pw, ph, facing):
    sw    = [r for r in rooms if get_room_zone(r,pw,ph,facing) == "SW"]
    heavy = [r for r in sw if r.type in ("master_bedroom","bedroom")]
    if heavy:
        return _res("sw_heavy","SW Corner (Heavy)", COMPLIANT, 7, EARN_FULL,
                    "SW has master/bedroom ✓")
    if sw:
        return _res("sw_heavy","SW Corner", PARTIAL, 7, EARN_PARTIAL,
                    "SW occupied but not bedroom")
    return _res("sw_heavy","SW Corner", VIOLATION, 7, EARN_NONE,
                "SW empty — master should anchor SW")


def rule_centre_open(rooms, pw, ph, facing):
    c_rooms  = [r for r in rooms if get_room_zone(r,pw,ph,facing) == "C"]
    c_area   = (pw/3)*(ph/3)
    used     = sum(r.area for r in c_rooms) if c_rooms else 0
    util     = used/c_area if c_area > 0 else 0
    if util <= 0.40:
        return _res("centre_open","Centre (Brahmasthana)", COMPLIANT, 5, EARN_FULL,
                    "Centre open ✓")
    if util <= 0.70:
        return _res("centre_open","Centre", PARTIAL, 5, EARN_PARTIAL,
                    "Centre partially open")
    return _res("centre_open","Centre", VIOLATION, 5, EARN_NONE,
                "Centre heavily occupied")


def rule_water_not_sw(rooms, pw, ph, facing):
    wet  = ("bathroom","toilet","bathroom_master","toilet_master",
            "bathroom_attached","toilet_attached")
    bad  = [r for r in rooms if r.type in wet
            and get_room_zone(r,pw,ph,facing) == "SW"]
    if not bad:
        return _res("water_sw","Water (not SW)", COMPLIANT, 5, EARN_FULL,
                    "No bathrooms in SW ✓")
    return _res("water_sw","Water (not SW)", VIOLATION, 5, EARN_NONE,
                f"{len(bad)} bathroom(s) in SW — inauspicious")


def rule_entrance_not_near_bedroom(rooms, pw, ph, facing):
    entrance = _first(rooms, "entrance")
    if not entrance:
        return _res("entrance_adj","Entrance (not near Bed)", MISSING, 0,
                    EARN_NONE, "No entrance to check")
    beds = [r for r in rooms if r.type in ("master_bedroom","bedroom")]
    EPS  = 1.5
    adj  = []
    for bed in beds:
        ht = (abs((entrance.x+entrance.width)-bed.x) < EPS or
              abs((bed.x+bed.width)-entrance.x) < EPS)
        vo = (entrance.y < bed.y+bed.height-EPS and
              entrance.y+entrance.height > bed.y+EPS)
        vt = (abs((entrance.y+entrance.height)-bed.y) < EPS or
              abs((bed.y+bed.height)-entrance.y) < EPS)
        ho = (entrance.x < bed.x+bed.width-EPS and
              entrance.x+entrance.width > bed.x+EPS)
        if (ht and vo) or (vt and ho):
            adj.append(bed.type)
    if not adj:
        return _res("entrance_adj","Entrance (not near Bed)", COMPLIANT, 0,
                    EARN_FULL, "Entrance not adjacent to bedrooms ✓")
    return _res("entrance_adj","Entrance (not near Bed)", VIOLATION, 0,
                EARN_NONE, f"Adjacent to {','.join(adj)}")


# ── Execution order ──────────────────────────────────────────────
ALL_RULES = [
    rule_kitchen,                   # 15 pts
    rule_master_bedroom,            # 20 pts
    rule_living_room,               # 15 pts
    rule_pooja_room,                #  0 pts (no pooja in plans)
    rule_bathroom,                  # 10 pts
    rule_dining_room,               # 10 pts
    rule_entrance,                  # 15 pts
    rule_bedroom_secondary,         # 10 pts
    rule_utility_room,              #  5 pts
    rule_ne_corner_light,           #  8 pts
    rule_sw_heavy,                  #  7 pts
    rule_centre_open,               #  5 pts
    rule_water_not_sw,              #  5 pts
    rule_entrance_not_near_bedroom, #  0 pts (quality check, no score)
]


def _res(key, label, status, weight, earn_frac, description):
    return {
        "key":         key,
        "label":       label,
        "status":      status,
        "weight":      weight,
        "earned":      round(weight * earn_frac, 2),
        "description": description,
    }