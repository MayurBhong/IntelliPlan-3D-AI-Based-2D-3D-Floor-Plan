# ═══════════════════════════════════════════════════════════════
# ga_engine/layout_generator.py  v9
#
# Architectural + Vastu rules enforced:
#   1.  Living room (hall) is LARGEST — ~30% of usable area
#   2.  NO balcony, NO store room in any plan
#   3.  Kitchen + Dining always adjacent (same band, side by side)
#   4.  Pooja room is SMALL — corner of NE band
#   5.  Bathroom + Toilet are SMALL — grouped in wet zone
#   6.  Entrance placed in NE corner — opens into Living, NOT bedroom
#   7.  Master Bedroom in SW zone (heavy corner per Vastu Image 1)
#   8.  Kitchen in SE zone (Best per Vastu Image 3)
#   9.  Entrance is NEVER adjacent to bedrooms (structural separation)
#  10.  3BHK: 1 common bath+toilet + 1 attached to master
#  11.  4BHK: 1 common bath+toilet + 1 attached master + 1 attached bedroom2
#  12.  Attached bathrooms placed directly next to their bedroom
# ═══════════════════════════════════════════════════════════════

import numpy as np
from typing import List, Optional, Tuple, Dict
from geometry.room import Room
from geometry.layout import Layout
from utils.constants import (
    PLOT_MARGIN as M,
    ROOM_MIN_SIZES,
    BHK_ROOM_COMPOSITIONS,
)
from utils.logger import get_logger

logger = get_logger(__name__)

# ── Area weights — living is the LARGEST room ───────────────────
# Pooja, toilet, bathroom are intentionally SMALL
ROOM_WEIGHTS = {
    "living":              0.30,   # LARGEST — ~30% of usable area (hall)
    "master_bedroom":      0.17,
    "bedroom":             0.13,
    "kitchen":             0.11,
    "dining":              0.09,
    "entrance":            0.05,
    "bathroom":            0.03,   # small
    "toilet":              0.02,   # small
    "bathroom_master":     0.03,   # small — attached to master
    "toilet_master":       0.02,   # small — attached to master
    "bathroom_attached":   0.03,   # small — attached to bedroom
    "toilet_attached":     0.02,   # small — attached to bedroom
    "pooja":               0.02,   # small corner room
    "utility":             0.04,
}

# ── Target sizes (ft) for aspect-ratio guidance ─────────────────
ROOM_TARGET = {
    "entrance":            ( 7,  8),
    "living":              (20, 18),   # large hall
    "dining":              (12, 11),
    "kitchen":             (11, 12),
    "master_bedroom":      (13, 14),
    "bedroom":             (12, 12),
    "bathroom":            ( 5,  6),   # small
    "toilet":              ( 4,  5),   # small
    "bathroom_master":     ( 5,  6),   # small
    "toilet_master":       ( 4,  5),   # small
    "bathroom_attached":   ( 5,  6),   # small
    "toilet_attached":     ( 4,  5),   # small
    "pooja":               ( 4,  4),   # small corner
    "utility":             ( 6,  7),
}

# ── Vastu zone preferences (Image 1 + 2 + 3) ────────────────────
VASTU_PREFS = {
    "entrance":            ["NE", "N", "E"],
    "living":              ["NW", "N", "E", "W", "NE", "SE"],
    "dining":              ["E", "SE", "S"],
    "kitchen":             ["SE", "NW"],
    "master_bedroom":      ["SW", "S", "W"],
    "bedroom":             ["SW", "S", "E", "W", "NW"],
    "bathroom":            ["NW", "W"],
    "toilet":              ["NW", "W"],
    "bathroom_master":     ["SW", "W"],   # near master bedroom (SW)
    "toilet_master":       ["SW", "W"],
    "bathroom_attached":   ["W", "NW"],   # near bedroom
    "toilet_attached":     ["W", "NW"],
    "pooja":               ["NE", "N", "E", "W", "NW"],
    "utility":             ["NW", "SE"],
}

# 9-zone compass map (row=0→N, col=0→W)
_ZM  = {(0,0):"NW",(0,1):"N",(0,2):"NE",
        (1,0):"W", (1,1):"C",(1,2):"E",
        (2,0):"SW",(2,1):"S",(2,2):"SE"}
_ZO  = ["N","NE","E","SE","S","SW","W","NW"]
_ZR  = {"North":0, "East":1, "South":2, "West":3}

def _rzn(z, rot):
    return "C" if z == "C" else _ZO[(_ZO.index(z) + rot * 2) % 8]

def _mw(types):
    return max(ROOM_MIN_SIZES.get(t, (3, 3))[0] for t in types)

def _mh(types):
    return max(ROOM_MIN_SIZES.get(t, (3, 3))[1] for t in types)

def _w(t):
    return ROOM_WEIGHTS.get(t, 0.03)


# ════════════════════════════════════════════════════════════════
#  BSP PACKER — zero-overlap room placement
# ════════════════════════════════════════════════════════════════

def _bsp(types: List[str], weights: List[float],
         x0: float, y0: float, x1: float, y1: float) -> List[Tuple]:
    n = len(types)
    cw = x1 - x0
    ch = y1 - y0
    if n == 0 or cw < 0.5 or ch < 0.5:
        return []
    if n == 1:
        return [(types[0], x0, y0, x1, y1)]
    sp = n // 2
    wa = sum(weights[:sp])
    wb = sum(weights[sp:])
    fa = wa / (wa + wb) if (wa + wb) > 0 else 0.5
    can_h = cw >= _mw(types[:sp]) + _mw(types[sp:])
    can_v = ch >= _mh(types[:sp]) + _mh(types[sp:])
    if not can_h and not can_v:
        s = cw / n
        return [(t, x0 + i*s, y0, x0 + (i+1)*s, y1)
                for i, t in enumerate(types)]
    if (cw >= ch and can_h) or not can_v:
        mid = max(x0 + _mw(types[:sp]),
                  min(x1 - _mw(types[sp:]), x0 + cw * fa))
        return (_bsp(types[:sp], weights[:sp], x0, y0, mid, y1) +
                _bsp(types[sp:], weights[sp:], mid, y0, x1, y1))
    else:
        mid = max(y0 + _mh(types[:sp]),
                  min(y1 - _mh(types[sp:]), y0 + ch * fa))
        return (_bsp(types[:sp], weights[:sp], x0, y0, x1, mid) +
                _bsp(types[sp:], weights[sp:], x0, mid, x1, y1))


# ════════════════════════════════════════════════════════════════
#  VASTU-AWARE 4-BAND LAYOUT
#
#  Band structure (North-facing reference):
#
#  ┌────────────────────────────────────────────┐  ← North (y = M)
#  │  Band 0 (14%) : NE — Pooja + Entrance      │  small, light, NE corner
#  ├────────────────────────────────────────────┤
#  │  Band 1 (28%) : NW — Living Room (LARGEST) │  full width, hall
#  ├────────────────────────────────────────────┤
#  │  Band 2 (22%) : SE/E — Kitchen | Dining    │  adjacent, kitchen left
#  ├────────────────────────────────────────────┤
#  │  Band 3 (36%) : SW/S — Bedrooms + Wet zone │  master SW, wet NW-right
#  └────────────────────────────────────────────┘  ← South (y = ph-M)
#
#  Within Band 3 (left → right):
#    [Master Bedroom][attached bath+toilet] [Bedroom(s)][Common bath+toilet]
#                     ↑ directly adjacent ↑
#
#  Entrance (Band 0) is 3 bands away from bedrooms (Band 3) —
#  it is STRUCTURALLY IMPOSSIBLE for entrance to touch a bedroom.
# ════════════════════════════════════════════════════════════════

def _place_rooms_vastu(
    room_types: List[str],
    pw: float, ph: float,
    facing: str,
    genes: Optional[np.ndarray] = None,
) -> List[Tuple]:
    """
    Place all rooms following Vastu band structure.
    Returns list of (room_type, x0, y0, x1, y1).
    """
    x0, y0 = M, M
    x1, y1 = pw - M, ph - M
    uw = x1 - x0   # usable width
    uh = y1 - y0   # usable height

    result: List[Tuple] = []

    # ── Separate rooms by category ───────────────────────────────
    rooms = list(room_types)

    def pull(t):
        found = [r for r in rooms if r == t]
        for r in found:
            rooms.remove(r)
        return found

    living             = pull("living")
    kitchen            = pull("kitchen")
    dining             = pull("dining")
    master             = pull("master_bedroom")
    bedrooms           = pull("bedroom")
    bath_common        = pull("bathroom")
    toilet_common      = pull("toilet")
    bath_master        = pull("bathroom_master")
    toilet_master      = pull("toilet_master")
    bath_attached      = pull("bathroom_attached")
    toilet_attached_rm = pull("toilet_attached")
    entrance           = pull("entrance")
    pooja              = pull("pooja")
    utility            = pull("utility")
    rest               = rooms[:]

    # ════════════════════════════════════════════════════════════
    #  BAND 0 — NE strip: Pooja (small) + Entrance
    #  Both are SMALL rooms in the NE corner.
    #  Pooja gets its own small slot; entrance next to it.
    # ════════════════════════════════════════════════════════════
    b0_h = max(uh * 0.14, 6.0)   # at least 6 ft high for entrance/pooja
    b0_y0 = y0
    b0_y1 = y0 + b0_h

    band0 = pooja + entrance
    if band0:
        # Pooja is smallest — give it a fixed small width (max 6 ft)
        # Entrance gets the rest of the band
        if pooja and entrance:
            pjw = max(ROOM_MIN_SIZES["pooja"][0], min(6.0, uw * 0.15))
            enw = max(ROOM_MIN_SIZES["entrance"][0], uw * 0.20)
            # Both right-aligned in NE corner
            pj_x0 = x1 - pjw
            en_x0 = pj_x0 - enw
            result.append(("pooja",    pj_x0, b0_y0, x1,      b0_y1))
            result.append(("entrance", en_x0, b0_y0, pj_x0,   b0_y1))
        elif pooja:
            pjw = max(ROOM_MIN_SIZES["pooja"][0], min(7.0, uw * 0.18))
            result.append(("pooja", x1 - pjw, b0_y0, x1, b0_y1))
        elif entrance:
            enw = max(ROOM_MIN_SIZES["entrance"][0], min(10.0, uw * 0.25))
            result.append(("entrance", x1 - enw, b0_y0, x1, b0_y1))

    # ════════════════════════════════════════════════════════════
    #  BAND 1 — Living Room (LARGEST room, NW zone)
    #  Full usable width so it is always the widest room.
    # ════════════════════════════════════════════════════════════
    b1_h  = max(uh * 0.28, 16.0)   # at least 16 ft for living room
    b1_y0 = b0_y1
    b1_y1 = b1_y0 + b1_h

    if living:
        result.append(("living", x0, b1_y0, x1, b1_y1))

    # ════════════════════════════════════════════════════════════
    #  BAND 2 — Kitchen (left=SE) + Dining (right=E)
    #  They are ALWAYS placed side by side in this band.
    # ════════════════════════════════════════════════════════════
    b2_h  = max(uh * 0.22, 11.0)
    b2_y0 = b1_y1
    b2_y1 = b2_y0 + b2_h

    kd = kitchen + dining
    if kd:
        kw = [_w(t) for t in kd]
        sw = sum(kw) or 1
        kw = [w / sw for w in kw]
        rects = _bsp(kd, kw, x0, b2_y0, x1, b2_y1)
        result.extend(rects)

    # ════════════════════════════════════════════════════════════
    #  BAND 3 — Bedrooms + Wet zone (SW / S zone)
    #
    #  Layout (left → right):
    #    [Master Bed][M.Bath][M.Toilet] | [Bedroom2][B.Bath][B.Toilet] |
    #    [Bedroom3 …]                   | [Common Bath][Common Toilet]
    #
    #  Master bedroom always at left/SW (heaviest corner).
    #  Attached bathrooms placed DIRECTLY next to their bedroom.
    #  Common wet zone at far right (NW direction within band).
    # ════════════════════════════════════════════════════════════
    b3_y0 = b2_y1
    b3_y1 = y1

    # Build bedroom groups with their attached bathrooms
    # Group 0: master + attached bath (placed left/SW)
    master_group: List[str] = master + bath_master + toilet_master
    # Group 1: bedroom 2 + attached bath (if any)
    bedroom2_group: List[str] = []
    remaining_beds: List[str] = list(bedrooms)
    if remaining_beds and (bath_attached or toilet_attached_rm):
        bedroom2_group = [remaining_beds.pop(0)] + bath_attached + toilet_attached_rm
    # Group 2: remaining bedrooms (no attached bath)
    other_beds: List[str] = remaining_beds
    # Common wet zone: bathroom + toilet + utility + rest (placed right/NW)
    common_wet: List[str] = bath_common + toilet_common + utility + rest

    # Collect all band-3 groups in left→right order
    b3_groups = []
    if master_group:   b3_groups.append(master_group)
    if bedroom2_group: b3_groups.append(bedroom2_group)
    if other_beds:
        for bed in other_beds:
            b3_groups.append([bed])
    if common_wet:     b3_groups.append(common_wet)

    if b3_groups:
        # Calculate width fraction per group based on weights
        g_weights = [sum(_w(t) for t in g) for g in b3_groups]
        total_gw  = sum(g_weights) or 1
        g_fracs   = [gw / total_gw for gw in g_weights]

        # Enforce master bedroom gets at least 30% of band-3 width
        if master_group and len(b3_groups) > 1:
            g_fracs[0] = max(g_fracs[0], 0.30)
            # Re-normalise remaining groups
            remaining = 1.0 - g_fracs[0]
            rest_sum  = sum(g_fracs[1:]) or 1
            g_fracs[1:] = [f / rest_sum * remaining for f in g_fracs[1:]]

        # Enforce common wet zone is SMALL (max 20% of band-3 width)
        if common_wet and len(b3_groups) > 1:
            last = len(b3_groups) - 1
            g_fracs[last] = min(g_fracs[last], 0.22)
            # Re-normalise remaining groups
            remaining = 1.0 - g_fracs[last]
            rest_sum  = sum(g_fracs[:last]) or 1
            g_fracs[:last] = [f / rest_sum * remaining
                               for f in g_fracs[:last]]

        # Place each group as a vertical slice in band 3
        cur_x = x0
        bw    = x1 - x0
        for gi, (grp, frac) in enumerate(zip(b3_groups, g_fracs)):
            is_last = (gi == len(b3_groups) - 1)
            gx0 = cur_x
            gx1 = (x1 if is_last
                   else max(cur_x + _mw(grp),
                            min(x1 - _mw(b3_groups[gi+1]),
                                cur_x + bw * frac)))

            # Within each group, stack rooms top→bottom using BSP
            gw_list = [_w(t) for t in grp]
            gsw = sum(gw_list) or 1
            gw_list = [w / gsw for w in gw_list]
            rects = _bsp(grp, gw_list, gx0, b3_y0, gx1, b3_y1)
            result.extend(rects)
            cur_x = gx1

    return result


# ════════════════════════════════════════════════════════════════
#  GENE PERTURBATION — small size variations per GA individual
# ════════════════════════════════════════════════════════════════

def _perturb(rects: List[Tuple],
             genes: Optional[np.ndarray],
             pw: float, ph: float) -> List[Tuple]:
    """Apply tiny gene-driven variations while respecting minimums."""
    if genes is None or len(rects) == 0:
        return rects
    perturbed = []
    for i, (rt, rx0, ry0, rx1, ry1) in enumerate(rects):
        if i + 3 < len(genes):
            dx = float(genes[i])     * 0.6 - 0.3
            dy = float(genes[i + 1]) * 0.6 - 0.3
            dw = float(genes[i + 2]) * 0.6 - 0.3
            dh = float(genes[i + 3]) * 0.6 - 0.3 if i + 3 < len(genes) else 0.0
        else:
            dx = dy = dw = dh = 0.0

        mw, mh = ROOM_MIN_SIZES.get(rt, (3, 3))
        nx0 = rx0 + dx
        ny0 = ry0 + dy
        nx1 = rx1 + dw
        ny1 = ry1 + dh

        if nx1 - nx0 < mw: nx1 = nx0 + mw
        if ny1 - ny0 < mh: ny1 = ny0 + mh
        nx0 = max(M, min(nx0, pw - M - mw))
        ny0 = max(M, min(ny0, ph - M - mh))
        nx1 = min(pw - M, max(nx1, nx0 + mw))
        ny1 = min(ph - M, max(ny1, ny0 + mh))

        perturbed.append((rt, nx0, ny0, nx1, ny1))
    return perturbed


# ════════════════════════════════════════════════════════════════
#  PUBLIC API
# ════════════════════════════════════════════════════════════════

def generate_layout(
    plot_w: float,
    plot_h: float,
    bhk_type: str,
    facing: str,
    split_ratios: Optional[np.ndarray] = None,
    rng: Optional[np.random.Generator] = None,
    template_idx: Optional[int] = None,
) -> Layout:
    """
    Generate a Vastu-compliant floor plan layout.

    Room size hierarchy (largest → smallest):
      Living Room > Master Bedroom > Bedroom > Kitchen > Dining >
      Entrance > Utility > Bathroom > Toilet > Pooja

    Bathroom placement:
      1BHK/2BHK : 1 common bathroom + toilet (NW wet zone)
      3BHK       : bathroom_master+toilet_master next to master bedroom
                   + common bathroom+toilet in NW wet zone
      4BHK       : bathroom_master+toilet_master next to master
                   + bathroom_attached+toilet_attached next to bedroom 2
                   + common bathroom+toilet in NW wet zone
    """
    if rng is None:
        rng = np.random.default_rng()

    all_rooms = list(
        BHK_ROOM_COMPOSITIONS.get(bhk_type, BHK_ROOM_COMPOSITIONS["2BHK"])
    )

    # Template variation
    if template_idx is None:
        if split_ratios is not None and len(split_ratios) >= 1:
            template_idx = int(float(split_ratios[0]) * 3) % 3
        else:
            template_idx = 0

    if split_ratios is None:
        jitter_rng   = np.random.default_rng(template_idx * 137)
        split_ratios = jitter_rng.uniform(0.42, 0.58, size=60).astype(np.float32)
    else:
        offset       = np.full(len(split_ratios),
                               template_idx * 0.04, dtype=np.float32)
        split_ratios = np.clip(split_ratios + offset, 0.0, 1.0)

    # Place rooms using Vastu band structure
    rects = _place_rooms_vastu(all_rooms, plot_w, plot_h, facing, split_ratios)

    # Apply small gene-based size variation
    rects = _perturb(rects, split_ratios, plot_w, plot_h)

    # Build Room objects
    rooms: List[Room] = []
    for (rt, rx0, ry0, rx1, ry1) in rects:
        mw, mh = ROOM_MIN_SIZES.get(rt, (3, 3))
        w = max(rx1 - rx0, mw)
        h = max(ry1 - ry0, mh)
        rooms.append(Room(type=rt, x=rx0, y=ry0, width=w, height=h))

    shape_polygon = [
        [M,        M],
        [plot_w-M, M],
        [plot_w-M, plot_h-M],
        [M,        plot_h-M],
    ]

    layout = Layout(
        plot_width=plot_w, plot_height=plot_h,
        facing=facing, bhk_type=bhk_type, rooms=rooms,
    )
    layout.__dict__['plot_shape']   = 'rect'
    layout.__dict__['plot_polygon'] = shape_polygon
    layout.__dict__['plot_zones']   = [{
        'x0': M, 'y0': M,
        'x1': plot_w - M, 'y1': plot_h - M,
    }]
    return layout


def _make_polygon(zones: List[Dict], pw: float, ph: float) -> List[List[float]]:
    all_x = [z['x0'] for z in zones] + [z['x1'] for z in zones]
    all_y = [z['y0'] for z in zones] + [z['y1'] for z in zones]
    return [
        [min(all_x), min(all_y)], [max(all_x), min(all_y)],
        [max(all_x), max(all_y)], [min(all_x), max(all_y)],
    ]