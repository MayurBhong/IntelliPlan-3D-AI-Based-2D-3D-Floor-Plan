# ═══════════════════════════════════════════════════════════════
# ga_engine/layout_generator.py  v12
#
# ENTRANCE + LIVING ROOM RULES (enforced in every template):
#   • Entrance is ALWAYS at a corner of the plot
#   • Entrance is ALWAYS adjacent (shares a wall) with Living Room
#   • They are NEVER separated by other rooms
#
# T0 — HORIZONTAL BANDS
#   Top-left corner:  [Entrance(small)] [Living Room (big, rest of top band)]
#   Middle band:      [Kitchen] [Dining]
#   Bottom band:      Bedrooms + Bathrooms
#
# T1 — LEFT COLUMN LIVING  (fixed: entrance top-left corner)
#   Left column top:  [Entrance(small)] immediately above [Living Room(big)]
#   Left column mid:  [Kitchen][Dining] side by side
#   Right column:     Master + Baths + Bedrooms
#
# T2 — BEDROOMS TOP / LIVING BOTTOM  (fixed: entrance bottom-left corner)
#   Top band:         Bedrooms + Bathrooms
#   Bottom band:      [Entrance(small, bottom-left corner)] [Living Room(big)] | [Kitchen][Dining]
#
# All rows sum exactly to 1.0 width, all columns sum to 1.0 height → zero gaps/overlaps.
# rng varies proportions each call → different plan on every Regenerate.
# NO pooja, NO balcony, NO store room.
# ═══════════════════════════════════════════════════════════════

import numpy as np
from typing import List, Optional, Dict
from geometry.room import Room
from geometry.layout import Layout
from utils.constants import PLOT_MARGIN as M, ROOM_MIN_SIZES
from utils.logger import get_logger

logger = get_logger(__name__)

ROOM_WEIGHTS = {
    "living":             0.28,
    "master_bedroom":     0.18,
    "bedroom":            0.14,
    "kitchen":            0.12,
    "dining":             0.10,
    "entrance":           0.06,
    "bathroom":           0.05,
    "toilet":             0.03,
    "bathroom_master":    0.04,
    "toilet_master":      0.03,
    "bathroom_attached":  0.04,
    "toilet_attached":    0.03,
    "utility":            0.04,
}

VASTU_PREFS = {
    "entrance":          ["NE", "N", "E"],
    "living":            ["NW", "N", "E", "W", "NE", "SE"],
    "dining":            ["E",  "SE", "S"],
    "kitchen":           ["SE", "NW"],
    "master_bedroom":    ["SW", "S",  "W"],
    "bedroom":           ["SW", "S",  "E", "W", "NW"],
    "bathroom":          ["NW", "W"],
    "toilet":            ["NW", "W"],
    "bathroom_master":   ["NW", "W"],
    "toilet_master":     ["NW", "W"],
    "bathroom_attached": ["NW", "W"],
    "toilet_attached":   ["NW", "W"],
    "utility":           ["NW", "SE"],
}


def _r(t, lbl, x, y, w, h):
    return {"type": t, "label": lbl,
            "x": float(x), "y": float(y),
            "w": float(w), "h": float(h)}

def _mw(ft, uw): return max(ft / uw, 0.01)
def _mh(ft, uh): return max(ft / uh, 0.01)


# ════════════════════════════════════════════════════════════════
#  1 BHK  — entrance, living, kitchen, master_bedroom,
#            bathroom, toilet
# ════════════════════════════════════════════════════════════════

def _1bhk_t0(rng, uw, uh):
    """
    T0 BANDS:
      [Entrance(small,corner)] [Living Room(big)]   ← top band, entrance top-left
      [Kitchen] [Bathroom] [Toilet]
      [Master Bedroom — full width]
    """
    h_top = rng.uniform(0.20, 0.28)   # entrance+living share this height
    h_mid = rng.uniform(0.18, 0.24)
    h_bot = 1.0 - h_top - h_mid

    # Top band: entrance occupies left slice, living fills the rest
    w_e = max(_mw(5.0, uw), rng.uniform(0.18, 0.26))
    w_l = 1.0 - w_e                   # living fills rest → no gap ✓

    # Mid band: kitchen | bathroom | toilet
    w_b = max(_mw(5.0, uw), rng.uniform(0.15, 0.20))
    w_t = max(_mw(4.0, uw), rng.uniform(0.12, 0.16))
    w_k = 1.0 - w_b - w_t

    return [
        # top band — entrance top-left corner, living adjacent right ✓
        _r("entrance",       "Entrance",       0,       0,     w_e, h_top),
        _r("living",         "Living Room",    w_e,     0,     w_l, h_top),
        # mid band
        _r("kitchen",        "Kitchen",        0,       h_top, w_k, h_mid),
        _r("bathroom",       "Bathroom",       w_k,     h_top, w_b, h_mid),
        _r("toilet",         "Toilet",         w_k+w_b, h_top, w_t, h_mid),
        # bottom
        _r("master_bedroom", "Master Bedroom", 0,       h_top+h_mid, 1.0, h_bot),
    ]


def _1bhk_t1(rng, uw, uh):
    """
    T1 LEFT COLUMN:
      Left col:  [Entrance(small, TOP-LEFT corner)]
                 [Living Room(big)]
                 [Kitchen]
      Right col: [Master Bedroom]
                 [Bathroom]
                 [Toilet]
    Entrance at top-left corner, immediately above Living → adjacent ✓
    """
    w_L = rng.uniform(0.50, 0.58); w_R = 1.0 - w_L

    # Left col heights (sum = 1.0)
    h_e = rng.uniform(0.12, 0.18)     # entrance — small, top
    h_k = rng.uniform(0.22, 0.28)
    h_l = 1.0 - h_e - h_k             # living fills rest

    # Right col heights (sum = 1.0)
    h_b = max(_mh(5.0, uh), rng.uniform(0.20, 0.26))
    h_t = max(_mh(4.0, uh), rng.uniform(0.16, 0.21))
    h_m = 1.0 - h_b - h_t

    return [
        # Left col — entrance TOP-LEFT, living directly below ✓
        _r("entrance",       "Entrance",       0,   0,       w_L, h_e),
        _r("living",         "Living Room",    0,   h_e,     w_L, h_l),
        _r("kitchen",        "Kitchen",        0,   h_e+h_l, w_L, h_k),
        # Right col
        _r("master_bedroom", "Master Bedroom", w_L, 0,       w_R, h_m),
        _r("bathroom",       "Bathroom",       w_L, h_m,     w_R, h_b),
        _r("toilet",         "Toilet",         w_L, h_m+h_b, w_R, h_t),
    ]


def _1bhk_t2(rng, uw, uh):
    """
    T2 BEDROOMS TOP / SERVICE BOTTOM:
      Top band:    [Master Bedroom] [Bathroom] [Toilet]  side-by-side
      Bottom band: [Entrance(small, BOTTOM-LEFT corner)] [Living Room(big)] [Kitchen]
    Entrance bottom-left corner, Living immediately right → adjacent ✓
    """
    h_top = rng.uniform(0.36, 0.44)
    h_bot = 1.0 - h_top

    # Top band widths
    w_b = max(_mw(5.0, uw), rng.uniform(0.16, 0.22))
    w_t = max(_mw(4.0, uw), rng.uniform(0.13, 0.18))
    w_m = 1.0 - w_b - w_t

    # Bottom band: entrance(left corner) | living | kitchen
    w_e = max(_mw(5.0, uw), rng.uniform(0.16, 0.24))
    w_k = rng.uniform(0.26, 0.34)
    w_l = 1.0 - w_e - w_k             # living fills between entrance and kitchen

    yb = h_top

    return [
        # Top
        _r("master_bedroom", "Master Bedroom", 0,       0,  w_m, h_top),
        _r("bathroom",       "Bathroom",       w_m,     0,  w_b, h_top),
        _r("toilet",         "Toilet",         w_m+w_b, 0,  w_t, h_top),
        # Bottom — entrance BOTTOM-LEFT corner, living adjacent right ✓
        _r("entrance",       "Entrance",       0,       yb, w_e, h_bot),
        _r("living",         "Living Room",    w_e,     yb, w_l, h_bot),
        _r("kitchen",        "Kitchen",        w_e+w_l, yb, w_k, h_bot),
    ]


# ════════════════════════════════════════════════════════════════
#  2 BHK  — entrance, living, dining, kitchen,
#            master_bedroom, bedroom, bathroom, toilet
# ════════════════════════════════════════════════════════════════

def _2bhk_t0(rng, uw, uh):
    """
    T0 BANDS:
      [Entrance(corner)] [Living Room(big)]  ← top band
      [Kitchen] [Dining]
      [Master] [Bedroom] [Bathroom] [Toilet]
    """
    h_top = rng.uniform(0.20, 0.28)
    h_mid = rng.uniform(0.20, 0.26)
    h_bot = 1.0 - h_top - h_mid

    w_e = max(_mw(5.0, uw), rng.uniform(0.18, 0.26))
    w_l = 1.0 - w_e

    w_k = rng.uniform(0.42, 0.52); w_d = 1.0 - w_k

    w_bt = max(_mw(5.0, uw), rng.uniform(0.13, 0.17))
    w_tl = max(_mw(4.0, uw), rng.uniform(0.11, 0.15))
    w_m  = rng.uniform(0.28, 0.36)
    w_b2 = 1.0 - w_m - w_bt - w_tl

    return [
        _r("entrance",       "Entrance",       0,          0,     w_e,  h_top),
        _r("living",         "Living Room",    w_e,        0,     w_l,  h_top),
        _r("kitchen",        "Kitchen",        0,          h_top, w_k,  h_mid),
        _r("dining",         "Dining Room",    w_k,        h_top, w_d,  h_mid),
        _r("master_bedroom", "Master Bedroom", 0,          h_top+h_mid, w_m,  h_bot),
        _r("bedroom",        "Bedroom",        w_m,        h_top+h_mid, w_b2, h_bot),
        _r("bathroom",       "Bathroom",       w_m+w_b2,   h_top+h_mid, w_bt, h_bot),
        _r("toilet",         "Toilet",         w_m+w_b2+w_bt, h_top+h_mid, w_tl, h_bot),
    ]


def _2bhk_t1(rng, uw, uh):
    """
    T1 LEFT COLUMN:
      Left col: [Entrance(TOP-LEFT corner)] [Living(big)] [Kitchen+Dining]
      Right col: [Master] [Bedroom] [Bathroom+Toilet]
    """
    w_L = rng.uniform(0.44, 0.52); w_R = 1.0 - w_L

    h_e  = rng.uniform(0.12, 0.18)
    h_kd = rng.uniform(0.24, 0.30)
    h_l  = 1.0 - h_e - h_kd           # living fills rest
    w_k  = rng.uniform(0.52, 0.62); w_d = 1.0 - w_k

    h_m   = rng.uniform(0.34, 0.42)
    h_b2  = rng.uniform(0.28, 0.36)
    h_wt  = 1.0 - h_m - h_b2
    w_bt  = max(_mw(5.0, uw), rng.uniform(0.48, 0.56)); w_tl = 1.0 - w_bt

    yl = h_e; ykd = h_e + h_l
    ym = 0;   yb2 = h_m; yw = h_m + h_b2

    return [
        # Left col — entrance TOP-LEFT, living right below ✓
        _r("entrance",       "Entrance",           0,               0,   w_L,         h_e),
        _r("living",         "Living Room",        0,               yl,  w_L,         h_l),
        _r("kitchen",        "Kitchen",            0,               ykd, w_L*w_k,     h_kd),
        _r("dining",         "Dining Room",        w_L*w_k,         ykd, w_L*w_d,     h_kd),
        # Right col
        _r("master_bedroom", "Master Bedroom",     w_L,             ym,  w_R,         h_m),
        _r("bedroom",        "Bedroom",            w_L,             yb2, w_R,         h_b2),
        _r("bathroom",       "Bathroom",           w_L,             yw,  w_R*w_bt,    h_wt),
        _r("toilet",         "Toilet",             w_L+w_R*w_bt,    yw,  w_R*w_tl,   h_wt),
    ]


def _2bhk_t2(rng, uw, uh):
    """
    T2 BEDROOMS TOP / SERVICE BOTTOM:
      Top band:    [Master] [Bedroom] [Bathroom] [Toilet]
      Bottom band: [Entrance(BOTTOM-LEFT corner)] [Living(big)] | [Kitchen] [Dining]
    Entrance bottom-left corner, living immediately right → adjacent ✓
    """
    h_top = rng.uniform(0.36, 0.44)
    h_bot = 1.0 - h_top

    w_bt = max(_mw(5.0, uw), rng.uniform(0.13, 0.17))
    w_tl = max(_mw(4.0, uw), rng.uniform(0.11, 0.15))
    w_m  = rng.uniform(0.28, 0.36)
    w_b2 = 1.0 - w_m - w_bt - w_tl

    # Bottom: entrance left-corner | living | then kitchen+dining on right
    w_e  = max(_mw(5.0, uw), rng.uniform(0.16, 0.24))
    w_kd = rng.uniform(0.36, 0.46)    # kitchen+dining combined right portion
    w_l  = 1.0 - w_e - w_kd
    w_k  = rng.uniform(0.48, 0.58); w_d = 1.0 - w_k   # split kd internally

    yb = h_top

    return [
        # Top
        _r("master_bedroom", "Master Bedroom", 0,            0,  w_m,  h_top),
        _r("bedroom",        "Bedroom",        w_m,          0,  w_b2, h_top),
        _r("bathroom",       "Bathroom",       w_m+w_b2,     0,  w_bt, h_top),
        _r("toilet",         "Toilet",         w_m+w_b2+w_bt,0,  w_tl, h_top),
        # Bottom — entrance BOTTOM-LEFT ✓
        _r("entrance",       "Entrance",       0,            yb, w_e,        h_bot),
        _r("living",         "Living Room",    w_e,          yb, w_l,        h_bot),
        _r("kitchen",        "Kitchen",        w_e+w_l,      yb, w_kd*w_k,   h_bot),
        _r("dining",         "Dining Room",    w_e+w_l+w_kd*w_k, yb, w_kd*w_d, h_bot),
    ]


# ════════════════════════════════════════════════════════════════
#  3 BHK  — entrance, living, dining, kitchen,
#            master_bedroom, bedroom×2,
#            bathroom_master+toilet_master (attached to master)
#            bathroom+toilet (CENTER)
# ════════════════════════════════════════════════════════════════

def _3bhk_t0(rng, uw, uh):
    """
    T0 BANDS:
      [Entrance(corner)] [Living Room(big)]  ← top band
      [Kitchen] [Dining]
      [Master][BathM/ToilM stacked][Bath/Toil stacked][Bed2][Bed3]
    """
    h_top = rng.uniform(0.18, 0.26)
    h_mid = rng.uniform(0.20, 0.25)
    h_bed = 1.0 - h_top - h_mid

    w_e = max(_mw(5.0, uw), rng.uniform(0.18, 0.26)); w_l = 1.0 - w_e
    w_k = rng.uniform(0.42, 0.52); w_d = 1.0 - w_k

    w_m  = rng.uniform(0.26, 0.32)
    w_bm = max(_mw(5.0, uw), rng.uniform(0.10, 0.13))
    w_bt = max(_mw(5.0, uw), rng.uniform(0.10, 0.13))
    w_b2 = rng.uniform(0.22, 0.28)
    w_b3 = 1.0 - w_m - w_bm - w_bt - w_b2
    f  = rng.uniform(0.48, 0.54)
    xbm = w_m; xbt = w_m+w_bm; xb2 = w_m+w_bm+w_bt; xb3 = w_m+w_bm+w_bt+w_b2
    yb  = h_top + h_mid

    return [
        _r("entrance",        "Entrance",          0,   0,       w_e,  h_top),
        _r("living",          "Living Room",        w_e, 0,       w_l,  h_top),
        _r("kitchen",         "Kitchen",            0,   h_top,   w_k,  h_mid),
        _r("dining",          "Dining Room",        w_k, h_top,   w_d,  h_mid),
        _r("master_bedroom",  "Master Bedroom",     0,   yb,      w_m,  h_bed),
        _r("bathroom_master", "Bathroom (Master)",  xbm, yb,      w_bm, h_bed*f),
        _r("toilet_master",   "Toilet (Master)",    xbm, yb+h_bed*f, w_bm, h_bed*(1-f)),
        _r("bathroom",        "Bathroom",           xbt, yb,      w_bt, h_bed*f),
        _r("toilet",          "Toilet",             xbt, yb+h_bed*f, w_bt, h_bed*(1-f)),
        _r("bedroom",         "Bedroom 2",          xb2, yb,      w_b2, h_bed),
        _r("bedroom",         "Bedroom 3",          xb3, yb,      w_b3, h_bed),
    ]


def _3bhk_t1(rng, uw, uh):
    """
    T1 LEFT COLUMN:
      Left col: [Entrance(TOP-LEFT corner)] [Living(big)] [Kitchen][Dining]
      Right col: [Master] | [BathM][Bath] | [ToilM][Toil] | [Bed2][Bed3]
    """
    w_L = rng.uniform(0.42, 0.50); w_R = 1.0 - w_L

    h_e  = rng.uniform(0.12, 0.18)
    h_kd = rng.uniform(0.24, 0.30)
    h_l  = 1.0 - h_e - h_kd
    w_k  = rng.uniform(0.52, 0.62); w_d = 1.0 - w_k

    h_m   = rng.uniform(0.30, 0.38)
    h_bat = max(_mh(5.0, uh), rng.uniform(0.14, 0.18))
    h_tol = max(_mh(4.0, uh), rng.uniform(0.12, 0.16))
    h_beds= 1.0 - h_m - h_bat - h_tol
    hw = 0.5
    w_b2 = rng.uniform(0.52, 0.60); w_b3 = 1.0 - w_b2

    yl = h_e; ykd = h_e + h_l
    ym = 0; ybt = h_m; ytt = h_m+h_bat; ybd = h_m+h_bat+h_tol

    return [
        # Left col — entrance TOP-LEFT ✓
        _r("entrance",        "Entrance",          0,            0,   w_L,           h_e),
        _r("living",          "Living Room",        0,            yl,  w_L,           h_l),
        _r("kitchen",         "Kitchen",            0,            ykd, w_L*w_k,       h_kd),
        _r("dining",          "Dining Room",        w_L*w_k,      ykd, w_L*w_d,       h_kd),
        # Right col
        _r("master_bedroom",  "Master Bedroom",     w_L,          ym,  w_R,           h_m),
        _r("bathroom_master", "Bathroom (Master)",  w_L,          ybt, w_R*hw,        h_bat),
        _r("bathroom",        "Bathroom",           w_L+w_R*hw,   ybt, w_R*(1-hw),    h_bat),
        _r("toilet_master",   "Toilet (Master)",    w_L,          ytt, w_R*hw,        h_tol),
        _r("toilet",          "Toilet",             w_L+w_R*hw,   ytt, w_R*(1-hw),    h_tol),
        _r("bedroom",         "Bedroom 2",          w_L,          ybd, w_R*w_b2,      h_beds),
        _r("bedroom",         "Bedroom 3",          w_L+w_R*w_b2, ybd, w_R*w_b3,     h_beds),
    ]


def _3bhk_t2(rng, uw, uh):
    """
    T2 BEDROOMS TOP / SERVICE BOTTOM:
      Top band:    [Master][BathM/ToilM][Bath/Toil][Bed2][Bed3]
      Bottom band: [Entrance(BOTTOM-LEFT corner)] [Living(big)] | [Kitchen][Dining]
    """
    h_top = rng.uniform(0.36, 0.44)
    h_bot = 1.0 - h_top

    w_m  = rng.uniform(0.26, 0.32)
    w_bm = max(_mw(5.0, uw), rng.uniform(0.10, 0.13))
    w_bt = max(_mw(5.0, uw), rng.uniform(0.10, 0.13))
    w_b2 = rng.uniform(0.22, 0.28)
    w_b3 = 1.0 - w_m - w_bm - w_bt - w_b2
    f  = rng.uniform(0.48, 0.54)
    xbm = w_m; xbt = w_m+w_bm; xb2 = w_m+w_bm+w_bt; xb3 = w_m+w_bm+w_bt+w_b2

    # Bottom — entrance BOTTOM-LEFT corner, living adjacent right
    w_e  = max(_mw(5.0, uw), rng.uniform(0.16, 0.24))
    w_kd = rng.uniform(0.36, 0.46)
    w_l  = 1.0 - w_e - w_kd
    w_k  = rng.uniform(0.48, 0.58); w_d = 1.0 - w_k
    yb   = h_top

    return [
        # Top
        _r("master_bedroom",  "Master Bedroom",    0,    0,            w_m,  h_top),
        _r("bathroom_master", "Bathroom (Master)", xbm,  0,            w_bm, h_top*f),
        _r("toilet_master",   "Toilet (Master)",   xbm,  h_top*f,      w_bm, h_top*(1-f)),
        _r("bathroom",        "Bathroom",          xbt,  0,            w_bt, h_top*f),
        _r("toilet",          "Toilet",            xbt,  h_top*f,      w_bt, h_top*(1-f)),
        _r("bedroom",         "Bedroom 2",         xb2,  0,            w_b2, h_top),
        _r("bedroom",         "Bedroom 3",         xb3,  0,            w_b3, h_top),
        # Bottom — entrance BOTTOM-LEFT ✓
        _r("entrance",        "Entrance",          0,            yb, w_e,          h_bot),
        _r("living",          "Living Room",        w_e,          yb, w_l,          h_bot),
        _r("kitchen",         "Kitchen",            w_e+w_l,      yb, w_kd*w_k,    h_bot),
        _r("dining",          "Dining Room",        w_e+w_l+w_kd*w_k, yb, w_kd*w_d, h_bot),
    ]


# ════════════════════════════════════════════════════════════════
#  4 BHK  — entrance, living, dining, kitchen,
#            master_bedroom, bedroom×3,
#            bathroom_master+toilet_master (attached to master)
#            bathroom_attached+toilet_attached (attached to bed2)
#            bathroom+toilet (CENTER), utility
# ════════════════════════════════════════════════════════════════

def _4bhk_t0(rng, uw, uh):
    """
    T0 BANDS:
      [Entrance(corner)] [Living(big)]      ← top band
      [Kitchen] [Dining] [Utility]
      [Master][BathM/ToilM][Bath/Toil][Bed2] ← top bed row
      [Bed3][BathA/ToilA][Bed4]             ← bot bed row
    """
    h_top = rng.uniform(0.18, 0.26)
    h_kd  = rng.uniform(0.18, 0.24)
    h_b1  = rng.uniform(0.20, 0.26)
    h_b2  = 1.0 - h_top - h_kd - h_b1

    w_e = max(_mw(5.0, uw), rng.uniform(0.18, 0.26)); w_l = 1.0 - w_e
    w_k = rng.uniform(0.38, 0.48); w_u = rng.uniform(0.14, 0.20); w_d = 1.0 - w_k - w_u

    yb1 = h_top + h_kd; yb2 = yb1 + h_b1

    w_m  = rng.uniform(0.28, 0.34)
    w_bm = max(_mw(5.0, uw), rng.uniform(0.11, 0.14))
    w_bt = max(_mw(5.0, uw), rng.uniform(0.11, 0.14))
    w_b2r= 1.0 - w_m - w_bm - w_bt
    f1   = rng.uniform(0.48, 0.54)
    xbm  = w_m; xbt = w_m+w_bm; xb2r = w_m+w_bm+w_bt

    w_b3 = rng.uniform(0.38, 0.48)
    w_ba = max(_mw(5.0, uw), rng.uniform(0.11, 0.14))
    w_b4 = 1.0 - w_b3 - w_ba
    f2   = rng.uniform(0.48, 0.54)
    xba  = w_b3; xb4 = w_b3 + w_ba

    return [
        _r("entrance",          "Entrance",          0,    0,           w_e,  h_top),
        _r("living",            "Living Room",        w_e,  0,           w_l,  h_top),
        _r("kitchen",           "Kitchen",            0,    h_top,       w_k,  h_kd),
        _r("dining",            "Dining Room",        w_k,  h_top,       w_d,  h_kd),
        _r("utility",           "Utility Room",       w_k+w_d, h_top,   w_u,  h_kd),
        _r("master_bedroom",    "Master Bedroom",     0,    yb1,         w_m,  h_b1),
        _r("bathroom_master",   "Bathroom (Master)",  xbm,  yb1,         w_bm, h_b1*f1),
        _r("toilet_master",     "Toilet (Master)",    xbm,  yb1+h_b1*f1, w_bm, h_b1*(1-f1)),
        _r("bathroom",          "Bathroom",           xbt,  yb1,         w_bt, h_b1*f1),
        _r("toilet",            "Toilet",             xbt,  yb1+h_b1*f1, w_bt, h_b1*(1-f1)),
        _r("bedroom",           "Bedroom 2",          xb2r, yb1,         w_b2r,h_b1),
        _r("bedroom",           "Bedroom 3",          0,    yb2,         w_b3, h_b2),
        _r("bathroom_attached", "Bathroom (Att.)",    xba,  yb2,         w_ba, h_b2*f2),
        _r("toilet_attached",   "Toilet (Att.)",      xba,  yb2+h_b2*f2, w_ba, h_b2*(1-f2)),
        _r("bedroom",           "Bedroom 4",          xb4,  yb2,         w_b4, h_b2),
    ]


def _4bhk_t1(rng, uw, uh):
    """
    T1 LEFT COLUMN:
      Left col: [Entrance(TOP-LEFT)] [Living(big)] [Kitchen][Dining] [Utility strip]
      Right col: [Master][Bed4] | [BathM][Bath] | [ToilM][Toil] | [Bed2][BathA][ToilA][Bed3]
    """
    w_L = rng.uniform(0.40, 0.48); w_R = 1.0 - w_L

    h_e  = rng.uniform(0.12, 0.18)
    h_kd = rng.uniform(0.22, 0.28)
    h_u  = rng.uniform(0.08, 0.12)
    h_l  = 1.0 - h_e - h_kd - h_u
    w_k  = rng.uniform(0.52, 0.62); w_d = 1.0 - w_k

    h_rt  = rng.uniform(0.28, 0.36)
    h_bat = max(_mh(5.0, uh), rng.uniform(0.13, 0.17))
    h_tol = max(_mh(4.0, uh), rng.uniform(0.11, 0.15))
    h_mid = rng.uniform(0.20, 0.26)
    h_b4r = 1.0 - h_rt - h_bat - h_tol - h_mid
    w_m4  = rng.uniform(0.52, 0.62); hw = 0.5
    w_b2r = rng.uniform(0.32, 0.42)
    w_bar = max(_mw(5.0, uw), rng.uniform(0.12, 0.16))
    w_tar = max(_mw(4.0, uw), rng.uniform(0.10, 0.14))
    w_b3r = 1.0 - w_b2r - w_bar - w_tar

    yl = h_e; ykd = h_e+h_l; yu_ = h_e+h_l+h_kd
    ym = 0; ybt = h_rt; ytt = h_rt+h_bat; ymd = h_rt+h_bat+h_tol; yb4r = h_rt+h_bat+h_tol+h_mid

    return [
        # Left col — entrance TOP-LEFT ✓
        _r("entrance",          "Entrance",          0,               0,   w_L,            h_e),
        _r("living",            "Living Room",        0,               yl,  w_L,            h_l),
        _r("kitchen",           "Kitchen",            0,               ykd, w_L*w_k,        h_kd),
        _r("dining",            "Dining Room",        w_L*w_k,         ykd, w_L*w_d,        h_kd),
        _r("utility",           "Utility Room",       0,               yu_, w_L,            h_u),
        # Right col
        _r("master_bedroom",    "Master Bedroom",     w_L,             ym,  w_R*w_m4,       h_rt),
        _r("bedroom",           "Bedroom 4",          w_L+w_R*w_m4,    ym,  w_R*(1-w_m4),  h_rt),
        _r("bathroom_master",   "Bathroom (Master)",  w_L,             ybt, w_R*hw,         h_bat),
        _r("bathroom",          "Bathroom",           w_L+w_R*hw,      ybt, w_R*(1-hw),     h_bat),
        _r("toilet_master",     "Toilet (Master)",    w_L,             ytt, w_R*hw,         h_tol),
        _r("toilet",            "Toilet",             w_L+w_R*hw,      ytt, w_R*(1-hw),     h_tol),
        _r("bedroom",           "Bedroom 2",          w_L,             ymd, w_R*w_b2r,      h_mid),
        _r("bathroom_attached", "Bathroom (Att.)",    w_L+w_R*w_b2r,   ymd, w_R*w_bar,      h_mid),
        _r("toilet_attached",   "Toilet (Att.)",      w_L+w_R*(w_b2r+w_bar), ymd, w_R*w_tar, h_mid),
        _r("bedroom",           "Bedroom 3",          w_L+w_R*(w_b2r+w_bar+w_tar), ymd, w_R*w_b3r, h_mid),
        _r("bedroom",           "Bedroom 4",          w_L,             yb4r, w_R,           h_b4r),
    ]


def _4bhk_t2(rng, uw, uh):
    """
    T2 BEDROOMS TOP / SERVICE BOTTOM:
      Row A: [Master][BathM/ToilM][Bath/Toil][Bed2]
      Row B: [Bed3][BathA/ToilA][Bed4]
      Bottom band: [Entrance(BOTTOM-LEFT corner)] [Living(big)] | [Kitchen][Dining][Utility]
    """
    h_ba = rng.uniform(0.20, 0.26)
    h_bb = rng.uniform(0.18, 0.24)
    h_bot= 1.0 - h_ba - h_bb

    yba = 0.0; ybb = h_ba; yb = h_ba + h_bb

    # Row A
    w_m  = rng.uniform(0.28, 0.34)
    w_bm = max(_mw(5.0, uw), rng.uniform(0.11, 0.14))
    w_bt = max(_mw(5.0, uw), rng.uniform(0.11, 0.14))
    w_b2 = 1.0 - w_m - w_bm - w_bt
    f1   = rng.uniform(0.48, 0.54)
    xbm  = w_m; xbt = w_m+w_bm; xb2 = w_m+w_bm+w_bt

    # Row B
    w_b3  = rng.uniform(0.38, 0.48)
    w_ba_ = max(_mw(5.0, uw), rng.uniform(0.11, 0.14))
    w_b4  = 1.0 - w_b3 - w_ba_
    f2    = rng.uniform(0.48, 0.54)
    xba_  = w_b3; xb4_ = w_b3 + w_ba_

    # Bottom — entrance BOTTOM-LEFT corner, living adjacent right
    w_e   = max(_mw(5.0, uw), rng.uniform(0.16, 0.24))
    w_kdu = rng.uniform(0.38, 0.48)
    w_l   = 1.0 - w_e - w_kdu
    w_k   = rng.uniform(0.44, 0.56); w_u = rng.uniform(0.18, 0.28); w_d = 1.0 - w_k - w_u

    return [
        # Row A
        _r("master_bedroom",    "Master Bedroom",    0,    yba,          w_m,  h_ba),
        _r("bathroom_master",   "Bathroom (Master)", xbm,  yba,          w_bm, h_ba*f1),
        _r("toilet_master",     "Toilet (Master)",   xbm,  yba+h_ba*f1,  w_bm, h_ba*(1-f1)),
        _r("bathroom",          "Bathroom",          xbt,  yba,          w_bt, h_ba*f1),
        _r("toilet",            "Toilet",            xbt,  yba+h_ba*f1,  w_bt, h_ba*(1-f1)),
        _r("bedroom",           "Bedroom 2",         xb2,  yba,          w_b2, h_ba),
        # Row B
        _r("bedroom",           "Bedroom 3",         0,    ybb,          w_b3,  h_bb),
        _r("bathroom_attached", "Bathroom (Att.)",   xba_, ybb,          w_ba_, h_bb*f2),
        _r("toilet_attached",   "Toilet (Att.)",     xba_, ybb+h_bb*f2,  w_ba_, h_bb*(1-f2)),
        _r("bedroom",           "Bedroom 4",         xb4_, ybb,          w_b4,  h_bb),
        # Bottom — entrance BOTTOM-LEFT corner ✓
        _r("entrance",          "Entrance",          0,             yb, w_e,          h_bot),
        _r("living",            "Living Room",        w_e,           yb, w_l,          h_bot),
        _r("kitchen",           "Kitchen",            w_e+w_l,       yb, w_kdu*w_k,    h_bot),
        _r("dining",            "Dining Room",        w_e+w_l+w_kdu*w_k, yb, w_kdu*w_d, h_bot),
        _r("utility",           "Utility Room",       w_e+w_l+w_kdu*(w_k+w_d), yb, w_kdu*w_u, h_bot),
    ]


# ════════════════════════════════════════════════════════════════
#  DISPATCHER
# ════════════════════════════════════════════════════════════════

_BUILDERS = {
    "1BHK": [_1bhk_t0, _1bhk_t1, _1bhk_t2],
    "2BHK": [_2bhk_t0, _2bhk_t1, _2bhk_t2],
    "3BHK": [_3bhk_t0, _3bhk_t1, _3bhk_t2],
    "4BHK": [_4bhk_t0, _4bhk_t1, _4bhk_t2],
}


def _clean_spec(spec):
    return [s for s in spec if s['w'] > 0.005 and s['h'] > 0.005]


def _rooms_from_spec(spec, uw, uh):
    rooms = []
    for s in spec:
        x = M + s['x'] * uw
        y = M + s['y'] * uh
        w = max(s['w'] * uw, ROOM_MIN_SIZES.get(s['type'], (3.0, 3.0))[0])
        h = max(s['h'] * uh, ROOM_MIN_SIZES.get(s['type'], (3.0, 3.0))[1])
        rooms.append(Room(type=s['type'], x=x, y=y, width=w, height=h))
    return rooms


# ════════════════════════════════════════════════════════════════
#  PUBLIC API
# ════════════════════════════════════════════════════════════════

def generate_layout(
    plot_w: float,
    plot_h: float,
    bhk_type: str,
    facing: str,
    split_ratios=None,
    rng=None,
    template_idx: Optional[int] = None,
) -> "Layout":
    """
    Generate one layout.
    template_idx: 0=bands (entrance top-left),
                  1=left-col (entrance top-left),
                  2=beds-top (entrance bottom-left)
    Fresh rng → different proportions → different plan each regenerate.
    """
    if rng is None:
        rng = np.random.default_rng()

    if template_idx is not None:
        tidx = int(template_idx) % 3
    elif split_ratios is not None and len(split_ratios) >= 1:
        tidx = int(float(split_ratios[0]) * 3) % 3
    else:
        tidx = 0

    bhk = bhk_type if bhk_type in _BUILDERS else "2BHK"
    uw  = plot_w - 2 * M
    uh  = plot_h - 2 * M

    spec  = _clean_spec(_BUILDERS[bhk][tidx](rng, uw, uh))
    rooms = _rooms_from_spec(spec, uw, uh)

    poly = [[M,M],[plot_w-M,M],[plot_w-M,plot_h-M],[M,plot_h-M]]

    layout = Layout(plot_width=plot_w, plot_height=plot_h,
                    facing=facing, bhk_type=bhk_type, rooms=rooms)
    layout.__dict__['plot_shape']   = 'rect'
    layout.__dict__['plot_polygon'] = poly
    layout.__dict__['plot_zones']   = [
        {'x0': M, 'y0': M, 'x1': plot_w-M, 'y1': plot_h-M}]
    return layout


def _make_polygon(zones, pw, ph):
    return [[M,M],[pw-M,M],[pw-M,ph-M],[M,ph-M]]