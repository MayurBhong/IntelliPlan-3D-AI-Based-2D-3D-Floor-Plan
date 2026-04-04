# ═══════════════════════════════════════════════════════════════
# vastu_engine/vastu_rules.py
#
# Vastu Shastra rule engine — rules derived from 3 reference images:
#   Image 1: Basics of Vasthu (zone assignments by compass direction)
#   Image 2: Room-to-zone mapping grid (9-zone)
#   Image 3: Ideal Placement table (Best / Good / x per room type)
#
# Zone summary from images:
#   Kitchen      → Best: SE  | 2nd option: NW
#   Bathroom/WC  → Best: NW  | Good: W
#   Master Bed   → Best: SW  | Good: S, W
#   Kids Bedroom → Good: S, E, W, NW, SW
#   Living Room  → Best: NW  | Good: N, E, W, NE, SE, Good
#   Pooja/Temple → Best: NE  | Good: N, E, W, NW
#   Entrance     → Best: NE  | Good: N, E  (NW/SW = Bad Entry)
#   Dining       → Good: E, SE, S
#   Utility      → NW or SE
#   NE corner    → Keep light (low, puja, entry only)
#   SW corner    → Heavy / high (master bed, water tank)
#   Brahmasthana → Centre — keep open
# ═══════════════════════════════════════════════════════════════

from typing import List, Dict, Any, Optional
from geometry.room import Room
from .direction_utils import get_room_zone, is_in_zone
from utils.constants import VASTU_RULE_WEIGHTS


COMPLIANT  = "compliant"
PARTIAL    = "partial"
VIOLATION  = "violation"
MISSING    = "missing"

EARN_FULL    = 1.00
EARN_PARTIAL = 0.50
EARN_NONE    = 0.00


def _find_rooms(rooms: List[Room], room_type: str) -> List[Room]:
    return [r for r in rooms if r.type == room_type]

def _first(rooms: List[Room], room_type: str) -> Optional[Room]:
    matches = _find_rooms(rooms, room_type)
    return matches[0] if matches else None


# ═══════════════════════════════════════════════════════════════
#   CORE VASTU RULES  (from reference images)
# ═══════════════════════════════════════════════════════════════

def rule_kitchen(rooms, pw, ph, facing) -> Dict:
    """
    Image 1 : SE = Kitchen (primary)  |  NW = Kitchen 2nd option
    Image 2 : SE = Kitchen
    Image 3 : Kitchen → Best: SE  |  all others: x
    """
    key, weight = "kitchen_direction", VASTU_RULE_WEIGHTS["kitchen_direction"]
    room = _first(rooms, "kitchen")
    if not room:
        return _result(key, "Kitchen (SE)", MISSING, weight, EARN_NONE,
                       "SE zone — Best as per Vastu")
    zone = get_room_zone(room, pw, ph, facing)
    if zone == "SE":
        return _result(key, "Kitchen (SE)", COMPLIANT, weight, EARN_FULL,
                       "SE zone ✓ — Best placement")
    if zone == "NW":
        return _result(key, "Kitchen (NW)", PARTIAL, weight, EARN_PARTIAL,
                       "NW — 2nd option as per Image 1")
    return _result(key, "Kitchen (SE)", VIOLATION, weight, EARN_NONE,
                   f"Found in {zone} — must be SE (Best) or NW (2nd option)")


def rule_master_bedroom(rooms, pw, ph, facing) -> Dict:
    """
    Image 1 : SW = High, Heavy, Master Bed
    Image 2 : SW = Bedroom
    Image 3 : Master Bedroom → Best: SW  |  Good: S, W
    """
    key, weight = "master_bedroom_dir", VASTU_RULE_WEIGHTS["master_bedroom_dir"]
    room = _first(rooms, "master_bedroom")
    if not room:
        return _result(key, "Master Bed (SW)", MISSING, weight, EARN_NONE,
                       "SW zone — Best as per Vastu")
    zone = get_room_zone(room, pw, ph, facing)
    if zone == "SW":
        return _result(key, "Master Bed (SW)", COMPLIANT, weight, EARN_FULL,
                       "SW zone ✓ — Best placement")
    if zone in ("S", "W"):
        return _result(key, "Master Bed (SW)", PARTIAL, weight, EARN_PARTIAL,
                       f"{zone} — Good as per Image 3")
    return _result(key, "Master Bed (SW)", VIOLATION, weight, EARN_NONE,
                   f"Found in {zone} — SW Best, S/W Good")


def rule_living_room(rooms, pw, ph, facing) -> Dict:
    """
    Image 3 : Living Room → Best: NW  |  Good: N, E, W, NE, SE
    (NW = Best per Image 3 table; SW = x)
    """
    key, weight = "living_room_dir", VASTU_RULE_WEIGHTS["living_room_dir"]
    room = _first(rooms, "living")
    if not room:
        return _result(key, "Living Room (NW)", MISSING, weight, EARN_NONE,
                       "NW — Best; N/E/W/NE/SE — Good")
    zone = get_room_zone(room, pw, ph, facing)
    if zone == "NW":
        return _result(key, "Living Room (NW)", COMPLIANT, weight, EARN_FULL,
                       "NW zone ✓ — Best placement")
    if zone in ("N", "E", "W", "NE", "SE"):
        return _result(key, "Living Room (NW)", PARTIAL, weight, EARN_PARTIAL,
                       f"{zone} — Good as per Image 3")
    return _result(key, "Living Room (NW)", VIOLATION, weight, EARN_NONE,
                   f"Found in {zone} — SW/S are bad for Living Room")


def rule_pooja_room(rooms, pw, ph, facing) -> Dict:
    """
    Image 1 : NE = Low, Light, Puja, Gate, Entry
    Image 2 : NE = Pooja, Verandah, Portico
    Image 3 : Temple/Pooja → Best: NE  |  Good: N, E, W, NW
    """
    key, weight = "pooja_room_dir", VASTU_RULE_WEIGHTS["pooja_room_dir"]
    room = _first(rooms, "pooja")
    if not room:
        return _result(key, "Pooja Room (NE)", MISSING, weight, EARN_NONE,
                       "NE — Best for Pooja/Temple")
    zone = get_room_zone(room, pw, ph, facing)
    if zone == "NE":
        return _result(key, "Pooja Room (NE)", COMPLIANT, weight, EARN_FULL,
                       "NE corner ✓ — Best as per Vastu")
    if zone in ("N", "E", "W", "NW"):
        return _result(key, "Pooja Room (NE)", PARTIAL, weight, EARN_PARTIAL,
                       f"{zone} — Good as per Image 3")
    return _result(key, "Pooja Room (NE)", VIOLATION, weight, EARN_NONE,
                   f"Found in {zone} — NE Best; avoid SE/SW/S for Pooja")


def rule_bathroom(rooms, pw, ph, facing) -> Dict:
    """
    Image 1 : NW = Toilets
    Image 3 : Bathroom/Toilet → Best: NW  |  Good: W
    (Covers all bathroom/toilet types)
    """
    key, weight = "bathroom_direction", VASTU_RULE_WEIGHTS["bathroom_direction"]
    wet_types = ("bathroom", "toilet",
                 "bathroom_master", "toilet_master",
                 "bathroom_attached", "toilet_attached")
    bath_rooms = [r for r in rooms if r.type in wet_types]
    if not bath_rooms:
        return _result(key, "Bathroom/WC (NW)", MISSING, weight, EARN_NONE,
                       "NW — Best for bathrooms & toilets")

    compliant = sum(1 for r in bath_rooms
                    if get_room_zone(r, pw, ph, facing) == "NW")
    good      = sum(1 for r in bath_rooms
                    if get_room_zone(r, pw, ph, facing) == "W")
    total     = len(bath_rooms)
    best_pct  = compliant / total
    good_pct  = (compliant + good) / total

    if best_pct >= 0.8:
        return _result(key, "Bathroom/WC (NW)", COMPLIANT, weight, EARN_FULL,
                       f"{compliant}/{total} in NW ✓ — Best placement")
    if good_pct >= 0.5:
        return _result(key, "Bathroom/WC (NW)", PARTIAL, weight, EARN_PARTIAL,
                       f"{compliant + good}/{total} in NW/W — Good placement")
    return _result(key, "Bathroom/WC (NW)", VIOLATION, weight, EARN_NONE,
                   "Bathrooms not in NW (Best) or W (Good)")


def rule_dining_room(rooms, pw, ph, facing) -> Dict:
    """
    Image 2 : E = Dining  |  S = Bedroom + Dining (shared zone)
    Image 3 : Dining acceptable in E, SE, S
    """
    key, weight = "dining_direction", VASTU_RULE_WEIGHTS["dining_direction"]
    room = _first(rooms, "dining")
    if not room:
        return _result(key, "Dining (E/SE/S)", MISSING, weight, EARN_NONE,
                       "E or SE — preferred for Dining")
    zone = get_room_zone(room, pw, ph, facing)
    if zone in ("E", "SE"):
        return _result(key, "Dining (E/SE)", COMPLIANT, weight, EARN_FULL,
                       f"{zone} ✓ — Best for Dining room")
    if zone in ("S", "NE"):
        return _result(key, "Dining (E/SE/S)", PARTIAL, weight, EARN_PARTIAL,
                       f"{zone} — Acceptable for Dining")
    return _result(key, "Dining (E/SE/S)", VIOLATION, weight, EARN_NONE,
                   f"Found in {zone} — E/SE preferred for Dining")


def rule_entrance(rooms, pw, ph, facing) -> Dict:
    """
    Image 1 :
      NE = Good Entry (Best)
      N  = Good Entry (NE side)
      E  = Good Entry
      NW = Bad Entry  (SW side = Bad Entry)
      SW = Bad Entry
      S  = Bad Entry
    Entrance MUST NOT be adjacent to bedrooms (enforced in layout_generator).
    """
    key, weight = "entrance_direction", VASTU_RULE_WEIGHTS["entrance_direction"]
    room = _first(rooms, "entrance")
    if not room:
        return _result(key, "Entrance (NE/N/E)", MISSING, weight, EARN_NONE,
                       "NE — Best entry; N/E — Good entry")
    zone = get_room_zone(room, pw, ph, facing)
    if zone == "NE":
        return _result(key, "Entrance (NE)", COMPLIANT, weight, EARN_FULL,
                       "NE ✓ — Best entry direction")
    if zone in ("N", "E"):
        return _result(key, "Entrance (NE/N/E)", PARTIAL, weight, EARN_PARTIAL,
                       f"{zone} — Good entry direction")
    if zone in ("SE", "NW"):
        # Borderline — not ideal but not the worst
        return _result(key, "Entrance (NE/N/E)", PARTIAL, weight, EARN_PARTIAL * 0.5,
                       f"{zone} — Acceptable but not ideal")
    # SW, S, W = Bad Entry per Image 1
    return _result(key, "Entrance (NE/N/E)", VIOLATION, weight, EARN_NONE,
                   f"Found in {zone} — SW/S/W are bad entry zones per Vastu")


# ═══════════════════════════════════════════════════════════════
#   STRUCTURAL QUALITY RULES
# ═══════════════════════════════════════════════════════════════

def rule_bedroom_secondary(rooms, pw, ph, facing) -> Dict:
    """
    Image 2 : SW = Bedroom  |  S = Bedroom
    Image 3 : Kids Bedroom → Good: S, E, W, NW, SW
    Secondary bedrooms must NOT be in NE (NE must stay light).
    """
    bedrooms = _find_rooms(rooms, "bedroom")
    if not bedrooms:
        return _result("bedroom_secondary", "Bedrooms (S/SW/E/W/NW)", MISSING, 10,
                       EARN_NONE, "S/SW/E/W/NW — Good zones for bedrooms")
    best_zones = ("SW", "S")
    good_zones = ("E", "W", "NW")
    bad_zones  = ("NE",)   # NE must be light — bedrooms here = violation

    compliant = sum(1 for r in bedrooms
                    if get_room_zone(r, pw, ph, facing) in best_zones)
    good      = sum(1 for r in bedrooms
                    if get_room_zone(r, pw, ph, facing) in good_zones)
    bad       = sum(1 for r in bedrooms
                    if get_room_zone(r, pw, ph, facing) in bad_zones)
    total     = len(bedrooms)
    score_pct = (compliant * 1.0 + good * 0.5) / total

    if bad > 0:
        return _result("bedroom_secondary", "Bedrooms (not NE)", VIOLATION, 10,
                       EARN_NONE, f"{bad} bedroom(s) in NE — NE must be light")
    if score_pct >= 0.8:
        return _result("bedroom_secondary", "Bedrooms (S/SW/E/W/NW)", COMPLIANT, 10,
                       EARN_FULL, f"{compliant + good}/{total} in preferred zones ✓")
    if score_pct >= 0.4:
        return _result("bedroom_secondary", "Bedrooms (S/SW/E/W/NW)", PARTIAL, 10,
                       EARN_PARTIAL, f"{compliant + good}/{total} in preferred zones")
    return _result("bedroom_secondary", "Bedrooms (S/SW/E/W/NW)", VIOLATION, 10,
                   EARN_NONE, "Bedrooms not in Vastu-recommended zones")


def rule_utility_room(rooms, pw, ph, facing) -> Dict:
    """Utility: NW or SE (consistent across Image 1 + Image 2)."""
    room = _first(rooms, "utility")
    if not room:
        return _result("utility_dir", "Utility (NW/SE)", MISSING, 5, EARN_NONE,
                       "NW or SE preferred")
    zone = get_room_zone(room, pw, ph, facing)
    if zone in ("NW", "SE"):
        return _result("utility_dir", "Utility (NW/SE)", COMPLIANT, 5, EARN_FULL,
                       f"{zone} ✓")
    return _result("utility_dir", "Utility (NW/SE)", PARTIAL, 5, EARN_PARTIAL,
                   f"In {zone} — NW or SE preferred")


def rule_ne_corner_light(rooms, pw, ph, facing) -> Dict:
    """
    Image 1 : NE = Low, Light, Water Sump, Gate, Entry, Puja
    Heavy / large rooms must NOT occupy NE corner.
    Entrance and Pooja are fine; kitchen/bedroom/bathroom are NOT.
    """
    heavy_types = ("kitchen", "master_bedroom", "bedroom",
                   "bathroom", "toilet", "dining")
    heavy_in_ne = [r for r in rooms
                   if r.type in heavy_types
                   and get_room_zone(r, pw, ph, facing) == "NE"]
    if not heavy_in_ne:
        return _result("ne_light", "NE Corner (Light/Open)", COMPLIANT, 8, EARN_FULL,
                       "NE (Ishaan) corner kept light ✓")
    names = ", ".join(r.type for r in heavy_in_ne)
    return _result("ne_light", "NE Corner (Light/Open)", VIOLATION, 8, EARN_NONE,
                   f"{names} in NE — NE must be light (Pooja/Entrance only)")


def rule_sw_heavy(rooms, pw, ph, facing) -> Dict:
    """
    Image 1 : SW = High, Heavy, Water Tank, Store, Master Bed
    Master bedroom or heavy rooms should anchor the SW corner.
    """
    sw_rooms  = [r for r in rooms if get_room_zone(r, pw, ph, facing) == "SW"]
    heavy_sw  = [r for r in sw_rooms if r.type in ("master_bedroom", "bedroom")]
    if heavy_sw:
        return _result("sw_heavy", "SW Corner (Heavy/Master)", COMPLIANT, 7, EARN_FULL,
                       "SW corner has master/bedroom ✓")
    if sw_rooms:
        return _result("sw_heavy", "SW Corner (Heavy/Master)", PARTIAL, 7, EARN_PARTIAL,
                       "SW corner occupied but not with bedroom")
    return _result("sw_heavy", "SW Corner (Heavy/Master)", VIOLATION, 7, EARN_NONE,
                   "SW corner empty — master bedroom should anchor SW")


def rule_centre_open(rooms, pw, ph, facing) -> Dict:
    """
    Image 2 : Brahmasthana (centre) = Courtyard — keep open.
    """
    centre_rooms = [r for r in rooms
                    if get_room_zone(r, pw, ph, facing) == "C"]
    total_centre = sum(r.area for r in centre_rooms)
    centre_area  = (pw / 3) * (ph / 3)
    util = total_centre / centre_area if centre_area > 0 else 1.0
    if util <= 0.40:
        return _result("centre_open", "Centre Brahmasthana", COMPLIANT, 5, EARN_FULL,
                       "Brahmasthana (centre) open ✓")
    if util <= 0.70:
        return _result("centre_open", "Centre Brahmasthana", PARTIAL, 5, EARN_PARTIAL,
                       "Centre partially open")
    return _result("centre_open", "Centre Brahmasthana", VIOLATION, 5, EARN_NONE,
                   "Brahmasthana heavily occupied — keep centre open")


def rule_water_not_sw(rooms, pw, ph, facing) -> Dict:
    """
    Image 1 : SW = Heavy/High — NOT for water or bathrooms.
    Bathrooms/toilets in SW are inauspicious.
    """
    wet_types  = ("bathroom", "toilet",
                  "bathroom_master", "toilet_master",
                  "bathroom_attached", "toilet_attached")
    water_rooms = [r for r in rooms if r.type in wet_types]
    sw_rooms    = [r for r in water_rooms
                   if get_room_zone(r, pw, ph, facing) == "SW"]
    if not sw_rooms:
        return _result("water_sw", "Water Rooms (not SW)", COMPLIANT, 5, EARN_FULL,
                       "No bathrooms in SW ✓")
    return _result("water_sw", "Water Rooms (not SW)", VIOLATION, 5, EARN_NONE,
                   f"{len(sw_rooms)} bathroom(s) in SW — inauspicious per Vastu")


def rule_entrance_not_near_bedroom(rooms, pw, ph, facing) -> Dict:
    """
    Vastu layout quality rule:
    Entrance must not be directly adjacent to bedrooms.
    Entrance should open into Living Room / Foyer zone.
    Checked geometrically — entrance and bedrooms must not share a wall.
    """
    entrance = _first(rooms, "entrance")
    if not entrance:
        return _result("entrance_adj", "Entrance (not near Bed)", MISSING, 0,
                       EARN_NONE, "No entrance to check")

    bed_types = ("master_bedroom", "bedroom")
    bedrooms  = [r for r in rooms if r.type in bed_types]
    EPS = 1.5   # ft tolerance for "shared wall"

    adjacent_beds = []
    for bed in bedrooms:
        # Check horizontal adjacency
        h_touch = (abs((entrance.x + entrance.width) - bed.x) < EPS or
                   abs((bed.x + bed.width) - entrance.x) < EPS)
        v_overlap = (entrance.y < bed.y + bed.height - EPS and
                     entrance.y + entrance.height > bed.y + EPS)
        # Check vertical adjacency
        v_touch = (abs((entrance.y + entrance.height) - bed.y) < EPS or
                   abs((bed.y + bed.height) - entrance.y) < EPS)
        h_overlap = (entrance.x < bed.x + bed.width - EPS and
                     entrance.x + entrance.width > bed.x + EPS)

        if (h_touch and v_overlap) or (v_touch and h_overlap):
            adjacent_beds.append(bed.type)

    if not adjacent_beds:
        return _result("entrance_adj", "Entrance (not near Bed)", COMPLIANT, 0,
                       EARN_FULL, "Entrance not adjacent to bedrooms ✓")
    return _result("entrance_adj", "Entrance (not near Bed)", VIOLATION, 0,
                   EARN_NONE,
                   f"Entrance directly adjacent to {', '.join(adjacent_beds)} — must open into living area")


# ── All rules in execution order ─────────────────────────────────
ALL_RULES = [
    rule_kitchen,                   # 15 pts — SE best
    rule_master_bedroom,            # 20 pts — SW best
    rule_living_room,               # 15 pts — NW best
    rule_pooja_room,                # 15 pts — NE best
    rule_bathroom,                  # 10 pts — NW best
    rule_dining_room,               # 10 pts — E/SE
    rule_entrance,                  # 15 pts — NE/N/E
    rule_bedroom_secondary,         # 10 pts — S/SW/E/W/NW (not NE)
    rule_utility_room,              #  5 pts — NW/SE
    rule_ne_corner_light,           #  8 pts — NE keep light
    rule_sw_heavy,                  #  7 pts — SW keep heavy
    rule_centre_open,               #  5 pts — Brahmasthana open
    rule_water_not_sw,              #  5 pts — no bathroom in SW
    rule_entrance_not_near_bedroom, #  0 pts (quality rule, no score weight)
]


def _result(key: str, label: str, status: str,
            weight: int, earn_frac: float, description: str) -> Dict:
    return {
        "key":         key,
        "label":       label,
        "status":      status,
        "weight":      weight,
        "earned":      round(weight * earn_frac, 2),
        "description": description,
    }