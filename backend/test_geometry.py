"""
╔══════════════════════════════════════════════════════════════════╗
║       IntelliPlan·3D — GEOMETRY MODULE TEST SUITE               ║
║       test_geometry.py                                           ║
║                                                                  ║
║  Run:  python test_geometry.py                                   ║
║  Run:  python test_geometry.py -v              (verbose)         ║
║  Run:  python test_geometry.py -t room layout  (single group)    ║
║                                                                  ║
║  Groups: room  layout  overlap  validation                       ║
╚══════════════════════════════════════════════════════════════════╝
"""

import sys, os, time, unittest, argparse, traceback, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── colour helpers ───────────────────────────────────────────────
C_RESET = "\033[0m"; C_GREEN = "\033[92m"; C_RED = "\033[91m"
C_YELLOW = "\033[93m"; C_CYAN = "\033[96m"; C_BOLD = "\033[1m"; C_DIM = "\033[2m"
ok   = lambda m: f"{C_GREEN}✓{C_RESET} {m}"
fail = lambda m: f"{C_RED}✗{C_RESET} {m}"
warn = lambda m: f"{C_YELLOW}⚠{C_RESET} {m}"

# ════════════════════════════════════════════════════════════════
#  TEST GROUP 1 — room.py
# ════════════════════════════════════════════════════════════════

class TestRoom(unittest.TestCase):
    """Tests for geometry/room.py"""

    def setUp(self):
        from geometry.room import Room
        self.Room = Room

    def _r(self, t="kitchen", x=5.0, y=5.0, w=10.0, h=12.0):
        return self.Room(type=t, x=x, y=y, width=w, height=h)

    # ── basic properties ─────────────────────────────────────────

    def test_label_known_type(self):
        """Known room type returns a non-empty human label"""
        r = self._r("master_bedroom")
        self.assertIsInstance(r.label, str)
        self.assertGreater(len(r.label), 0)
        self.assertNotEqual(r.label, "master_bedroom")

    def test_label_unknown_type(self):
        """Unknown room type falls back to a title-cased string"""
        r = self._r("mystery_room")
        self.assertIsInstance(r.label, str)
        self.assertGreater(len(r.label), 0)

    def test_area(self):
        """area == width × height"""
        r = self._r(w=8.5, h=10.0)
        self.assertAlmostEqual(r.area, 85.0, places=2)

    def test_right_edge(self):
        """right == x + width"""
        r = self._r(x=4.0, w=9.0)
        self.assertAlmostEqual(r.right, 13.0, places=4)

    def test_bottom_edge(self):
        """bottom == y + height"""
        r = self._r(y=3.0, h=11.0)
        self.assertAlmostEqual(r.bottom, 14.0, places=4)

    def test_center_x(self):
        """center_x == x + width/2"""
        r = self._r(x=4.0, w=10.0)
        self.assertAlmostEqual(r.center_x, 9.0, places=4)

    def test_center_y(self):
        """center_y == y + height/2"""
        r = self._r(y=6.0, h=12.0)
        self.assertAlmostEqual(r.center_y, 12.0, places=4)

    # ── aspect ratio ─────────────────────────────────────────────

    def test_aspect_ratio_square(self):
        """Square room has aspect ratio 1.0"""
        r = self._r(w=10.0, h=10.0)
        self.assertAlmostEqual(r.aspect_ratio, 1.0, places=4)

    def test_aspect_ratio_wider(self):
        """Wider room: w/h ≥ 1"""
        r = self._r(w=15.0, h=10.0)
        self.assertAlmostEqual(r.aspect_ratio, 1.5, places=4)

    def test_aspect_ratio_taller(self):
        """Taller room: aspect ratio still ≥ 1 (inverted)"""
        r = self._r(w=8.0, h=14.0)
        self.assertGreaterEqual(r.aspect_ratio, 1.0)
        self.assertAlmostEqual(r.aspect_ratio, 14.0/8.0, places=4)

    def test_aspect_ratio_zero_height_no_crash(self):
        """Zero height doesn't crash — returns a large sentinel"""
        r = self._r(w=10.0, h=0.0)
        ar = r.aspect_ratio
        self.assertIsInstance(ar, float)
        self.assertGreater(ar, 1.0)

    # ── overlap detection ────────────────────────────────────────

    def test_no_overlap_adjacent(self):
        """Side-by-side rooms do not overlap"""
        a = self._r(x=0,  w=10, h=10)
        b = self._r(x=10, w=10, h=10)
        self.assertFalse(a.overlaps(b))
        self.assertFalse(b.overlaps(a))

    def test_overlap_full(self):
        """Identical rooms overlap"""
        a = self._r(x=0, y=0, w=10, h=10)
        b = self._r(x=0, y=0, w=10, h=10)
        self.assertTrue(a.overlaps(b))

    def test_overlap_partial(self):
        """Partially overlapping rooms detected"""
        a = self._r(x=0, y=0, w=10, h=10)
        b = self._r(x=5, y=5, w=10, h=10)
        self.assertTrue(a.overlaps(b))
        self.assertTrue(b.overlaps(a))

    def test_no_overlap_tolerance(self):
        """Rooms sharing a wall within tolerance do not count as overlapping"""
        a = self._r(x=0,   y=0, w=10, h=10)
        b = self._r(x=9.95, y=0, w=10, h=10)  # share ~0.05 ft
        self.assertFalse(a.overlaps(b, tol=0.1))

    def test_overlap_symmetry(self):
        """a.overlaps(b) == b.overlaps(a)"""
        a = self._r(x=0, y=0, w=12, h=10)
        b = self._r(x=8, y=5, w=12, h=10)
        self.assertEqual(a.overlaps(b), b.overlaps(a))

    # ── to_dict ──────────────────────────────────────────────────

    def test_to_dict_keys(self):
        """to_dict returns all required frontend keys"""
        r = self._r()
        d = r.to_dict()
        for key in ("type","label","x","y","w","h","width","height","area"):
            self.assertIn(key, d, f"Missing key: {key}")

    def test_to_dict_values(self):
        """to_dict values match Room attributes"""
        r = self._r(t="bathroom", x=3.0, y=7.0, w=6.0, h=8.0)
        d = r.to_dict()
        self.assertEqual(d["type"],   "bathroom")
        self.assertAlmostEqual(d["x"], 3.0, places=2)
        self.assertAlmostEqual(d["width"], 6.0, places=2)
        self.assertAlmostEqual(d["area"],  48.0, places=2)

    def test_to_dict_w_h_compat(self):
        """to_dict includes both 'w'/'h' (legacy) and 'width'/'height'"""
        r = self._r(w=9.0, h=11.0)
        d = r.to_dict()
        self.assertAlmostEqual(d["w"], d["width"],  places=4)
        self.assertAlmostEqual(d["h"], d["height"], places=4)

    def test_repr_string(self):
        """__repr__ returns a meaningful string"""
        r = self._r()
        s = repr(r)
        self.assertIsInstance(s, str)
        self.assertIn("kitchen", s)


# ════════════════════════════════════════════════════════════════
#  TEST GROUP 2 — layout.py
# ════════════════════════════════════════════════════════════════

class TestLayout(unittest.TestCase):
    """Tests for geometry/layout.py"""

    def setUp(self):
        from geometry.room   import Room
        from geometry.layout import Layout
        self.Room   = Room
        self.Layout = Layout

    def _make_layout(self, rooms=None):
        if rooms is None:
            rooms = [
            self.Room("kitchen", x=5, y=5,  width=9,  height=10),
            self.Room("living",  x=0, y=15, width=20, height=15),
            ]
        return self.Layout(
            plot_width=40.0, plot_height=60.0,
            facing="East", bhk_type="2BHK",
            rooms=rooms,
        )

    # ── identity ─────────────────────────────────────────────────

    def test_layout_id_generated(self):
        """Each Layout gets a unique layout_id"""
        l1 = self._make_layout()
        l2 = self._make_layout()
        self.assertIsInstance(l1.layout_id, str)
        self.assertGreater(len(l1.layout_id), 0)
        self.assertNotEqual(l1.layout_id, l2.layout_id)

    def test_layout_id_prefix(self):
        """layout_id starts with 'layout-'"""
        l = self._make_layout()
        self.assertTrue(l.layout_id.startswith("layout-"))

    # ── derived properties ───────────────────────────────────────

    def test_usable_area(self):
        """usable_area = (width-2*MARGIN) × (height-2*MARGIN)"""
        from utils.constants import PLOT_MARGIN as M
        l = self._make_layout()
        expected = round((40 - 2*M) * (60 - 2*M), 2)
        self.assertAlmostEqual(l.usable_area, expected, places=2)

    def test_total_room_area(self):
        """total_room_area == sum of all room areas"""
        rooms = [
            self.Room("kitchen", x=0, y=0,  width=9,  height=10),
            self.Room("living",  x=0, y=10, width=15, height=12),
        ]
        l = self._make_layout(rooms)
        expected = round(9*10 + 15*12, 2)
        self.assertAlmostEqual(l.total_room_area, expected, places=2)

    def test_total_room_area_empty(self):
        """total_room_area == 0 for empty room list"""
        l = self._make_layout([])
        self.assertEqual(l.total_room_area, 0.0)

    # ── to_dict ──────────────────────────────────────────────────

    def test_to_dict_top_level_keys(self):
        """to_dict has all required top-level keys"""
        d = self._make_layout().to_dict()
        for key in ("layout_id","rooms","vastu_score","fitness",
                    "space_util","total_room_area","vastu_rules","plot"):
            self.assertIn(key, d, f"Missing key: {key}")

    def test_to_dict_plot_keys(self):
        """to_dict.plot has all required keys"""
        d = self._make_layout().to_dict()
        for key in ("width","height","facing","bhk_type","usable_area"):
            self.assertIn(key, d["plot"], f"Missing plot key: {key}")

    def test_to_dict_plot_values(self):
        """to_dict.plot values match constructor args"""
        l = self._make_layout()
        p = l.to_dict()["plot"]
        self.assertEqual(p["width"],    40.0)
        self.assertEqual(p["height"],   60.0)
        self.assertEqual(p["facing"],   "East")
        self.assertEqual(p["bhk_type"], "2BHK")

    def test_to_dict_rooms_list(self):
        """to_dict.rooms is a list of dicts with room keys"""
        d = self._make_layout().to_dict()
        self.assertIsInstance(d["rooms"], list)
        for r in d["rooms"]:
            for k in ("type","label","x","y","width","height","area"):
                self.assertIn(k, r)

    def test_to_dict_scores_rounded(self):
        """Scores are rounded floats, not raw numpy types"""
        l = self._make_layout()
        l.fitness     = 0.87654321
        l.vastu_score = 76.543
        l.space_util  = 72.111
        d = l.to_dict()
        self.assertIsInstance(d["fitness"],     float)
        self.assertIsInstance(d["vastu_score"], float)
        self.assertAlmostEqual(d["fitness"],     0.876543, places=5)
        self.assertAlmostEqual(d["vastu_score"], 76.54,    places=1)

    # ── clone ─────────────────────────────────────────────────────

    def test_clone_is_independent(self):
        """Cloning a layout produces an independent copy"""
        l  = self._make_layout()
        lc = l.clone()
        # Mutate clone's first room position
        lc.rooms[0].x = 99.0
        # Original should be unchanged
        self.assertNotEqual(l.rooms[0].x, 99.0)

    def test_clone_new_id(self):
        """Cloned layout gets its own new layout_id"""
        l  = self._make_layout()
        lc = l.clone()
        self.assertNotEqual(l.layout_id, lc.layout_id)

    def test_clone_same_room_count(self):
        """Clone has same number of rooms"""
        l  = self._make_layout()
        lc = l.clone()
        self.assertEqual(len(l.rooms), len(lc.rooms))


# ════════════════════════════════════════════════════════════════
#  TEST GROUP 3 — overlap.py
# ════════════════════════════════════════════════════════════════

class TestOverlap(unittest.TestCase):
    """Tests for geometry/overlap.py"""

    def setUp(self):
        from geometry.room import Room
        from geometry.overlap import (
            overlap_area, total_overlap_area,
            has_any_overlap, overlapping_pairs, overlap_penalty
        )
        self.Room              = Room
        self.overlap_area      = overlap_area
        self.total_overlap     = total_overlap_area
        self.has_overlap       = has_any_overlap
        self.pairs             = overlapping_pairs
        self.penalty           = overlap_penalty

    def _r(self, x, y, w, h, t="living"):
        return self.Room(type=t, x=x, y=y, width=w, height=h)

    # ── overlap_area ─────────────────────────────────────────────

    def test_no_overlap_area(self):
        """Non-overlapping rooms have overlap area 0"""
        a = self._r(0,  0, 10, 10)
        b = self._r(10, 0, 10, 10)
        self.assertEqual(self.overlap_area(a, b), 0.0)

    def test_full_overlap_area(self):
        """Identical rooms overlap by their full area"""
        a = self._r(0, 0, 10, 10)
        b = self._r(0, 0, 10, 10)
        self.assertAlmostEqual(self.overlap_area(a, b), 100.0, places=2)

    def test_partial_overlap_area(self):
        """Partial overlap returns correct area"""
        a = self._r(0, 0, 10, 10)
        b = self._r(5, 5, 10, 10)   # 5×5 overlap
        self.assertAlmostEqual(self.overlap_area(a, b), 25.0, places=2)

    def test_overlap_area_symmetry(self):
        """overlap_area(a, b) == overlap_area(b, a)"""
        a = self._r(0, 0, 12, 8)
        b = self._r(8, 4, 12, 8)
        self.assertAlmostEqual(self.overlap_area(a, b),
                               self.overlap_area(b, a), places=4)

    def test_overlap_area_non_negative(self):
        """overlap_area is always >= 0"""
        a = self._r(0,  0, 10, 10)
        b = self._r(20, 0, 10, 10)
        self.assertGreaterEqual(self.overlap_area(a, b), 0.0)

    # ── total_overlap_area ───────────────────────────────────────

    def test_total_overlap_no_rooms(self):
        """Empty list → 0 overlap"""
        self.assertEqual(self.total_overlap([]), 0.0)

    def test_total_overlap_one_room(self):
        """Single room → 0 overlap"""
        self.assertEqual(self.total_overlap([self._r(0, 0, 10, 10)]), 0.0)

    def test_total_overlap_non_overlapping(self):
        """Non-overlapping rooms → 0 total overlap"""
        rooms = [self._r(0, 0, 10, 10), self._r(11, 0, 10, 10), self._r(22, 0, 10, 10)]
        self.assertEqual(self.total_overlap(rooms), 0.0)

    def test_total_overlap_all_overlapping(self):
        """All rooms stacked at origin → large overlap"""
        rooms = [self._r(0, 0, 10, 10) for _ in range(4)]
        ov = self.total_overlap(rooms)
        self.assertGreater(ov, 0.0)

    # ── has_any_overlap ──────────────────────────────────────────

    def test_has_overlap_false(self):
        rooms = [self._r(0, 0, 10, 10), self._r(11, 0, 10, 10)]
        self.assertFalse(self.has_overlap(rooms))

    def test_has_overlap_true(self):
        rooms = [self._r(0, 0, 10, 10), self._r(5, 5, 10, 10)]
        self.assertTrue(self.has_overlap(rooms))

    def test_has_overlap_single_room(self):
        self.assertFalse(self.has_overlap([self._r(0, 0, 10, 10)]))

    # ── overlapping_pairs ────────────────────────────────────────

    def test_pairs_none(self):
        rooms = [self._r(0, 0, 10, 10), self._r(11, 0, 10, 10)]
        self.assertEqual(self.pairs(rooms), [])

    def test_pairs_one(self):
        rooms = [self._r(0, 0, 10, 10), self._r(5, 5, 10, 10), self._r(30, 0, 5, 5)]
        p = self.pairs(rooms)
        self.assertEqual(len(p), 1)
        self.assertIn((0, 1), p)

    def test_pairs_indices_valid(self):
        """All pair indices are valid room indices"""
        rooms = [self._r(i*3, 0, 5, 5) for i in range(4)]
        # Make rooms[0] and rooms[1] overlap
        rooms[1] = self._r(2, 0, 5, 5)
        p = self.pairs(rooms)
        for i, j in p:
            self.assertGreaterEqual(i, 0)
            self.assertLess(j, len(rooms))
            self.assertLess(i, j)

    # ── overlap_penalty ──────────────────────────────────────────

    def test_penalty_no_overlap(self):
        rooms = [self._r(0, 0, 10, 10), self._r(11, 0, 10, 10)]
        p = self.penalty(rooms, plot_area=40*60)
        self.assertEqual(p, 0.0)

    def test_penalty_range(self):
        """Penalty is always in [0, 1]"""
        rooms = [self._r(0, 0, 20, 20), self._r(5, 5, 20, 20)]
        p = self.penalty(rooms, plot_area=40*60)
        self.assertGreaterEqual(p, 0.0)
        self.assertLessEqual(p, 1.0)

    def test_penalty_increases_with_overlap(self):
        """More overlap → higher penalty"""
        rooms_small = [self._r(0, 0, 10, 10), self._r(8, 8, 10, 10)]  # small overlap
        rooms_large = [self._r(0, 0, 20, 20), self._r(0, 0, 20, 20)]  # full overlap
        p_small = self.penalty(rooms_small, 40*60)
        p_large = self.penalty(rooms_large, 40*60)
        self.assertGreater(p_large, p_small)


# ════════════════════════════════════════════════════════════════
#  TEST GROUP 4 — validation.py
# ════════════════════════════════════════════════════════════════

class TestValidation(unittest.TestCase):
    """Tests for geometry/validation.py"""

    def setUp(self):
        from geometry.room import Room
        from geometry.validation import (
            room_within_bounds, room_meets_min_size,
            layout_boundary_violations, layout_size_violations,
            space_utilisation, aspect_ratio_score, is_valid_layout,
        )
        self.Room       = Room
        self.within     = room_within_bounds
        self.min_size   = room_meets_min_size
        self.bviol      = layout_boundary_violations
        self.sviol      = layout_size_violations
        self.space_util = space_utilisation
        self.ar_score   = aspect_ratio_score
        self.is_valid   = is_valid_layout
        self.pw, self.ph = 40.0, 60.0

    def _r(self, t, x, y, w, h):
        return self.Room(type=t, x=x, y=y, width=w, height=h)

    # ── room_within_bounds ───────────────────────────────────────

    def test_within_bounds_pass(self):
        r = self._r("kitchen", x=5, y=5, w=9, h=10)
        self.assertTrue(self.within(r, self.pw, self.ph))

    def test_exceeds_right(self):
        r = self._r("kitchen", x=35, y=5, w=9, h=10)
        self.assertFalse(self.within(r, self.pw, self.ph))

    def test_exceeds_bottom(self):
        r = self._r("kitchen", x=5, y=55, w=9, h=10)
        self.assertFalse(self.within(r, self.pw, self.ph))

    def test_negative_x(self):
        r = self._r("kitchen", x=-1, y=5, w=9, h=10)
        self.assertFalse(self.within(r, self.pw, self.ph))

    def test_exactly_fits(self):
        """Room that exactly fills the plot is within bounds"""
        r = self._r("living", x=0, y=0, w=self.pw, h=self.ph)
        self.assertTrue(self.within(r, self.pw, self.ph))

    # ── room_meets_min_size ──────────────────────────────────────

    def test_min_size_pass(self):
        from utils.constants import ROOM_MIN_SIZES
        mw, mh = ROOM_MIN_SIZES["kitchen"]
        r = self._r("kitchen", 0, 0, mw, mh)
        self.assertTrue(self.min_size(r))

    def test_min_size_fail_width(self):
        from utils.constants import ROOM_MIN_SIZES
        mw, mh = ROOM_MIN_SIZES["kitchen"]
        r = self._r("kitchen", 0, 0, mw - 0.5, mh)
        self.assertFalse(self.min_size(r))

    def test_min_size_fail_height(self):
        from utils.constants import ROOM_MIN_SIZES
        mw, mh = ROOM_MIN_SIZES["living"]
        r = self._r("living", 0, 0, mw, mh - 1.0)
        self.assertFalse(self.min_size(r))

    def test_unknown_type_uses_default(self):
        """Unknown room type uses default minimum (3×3)"""
        r = self._r("mystery", 0, 0, 3.5, 3.5)
        self.assertTrue(self.min_size(r))
        r_small = self._r("mystery", 0, 0, 2.0, 2.0)
        self.assertFalse(self.min_size(r_small))

    # ── layout_boundary_violations ───────────────────────────────

    def test_no_violations(self):
        rooms = [
            self._r("kitchen",  5, 5,  9,  10),
            self._r("bathroom", 0, 40, 7,  8),
        ]
        self.assertEqual(self.bviol(rooms, self.pw, self.ph), [])

    def test_one_violation(self):
        rooms = [
            self._r("kitchen",  5,  5, 9, 10),
            self._r("bathroom", 38, 0, 7, 8),  # right edge at 45 > 40
        ]
        v = self.bviol(rooms, self.pw, self.ph)
        self.assertEqual(v, [1])

    def test_multiple_violations(self):
        rooms = [
            self._r("kitchen",  -1,  5,  9, 10),  # x < 0
            self._r("bathroom",  5, 58,  7,  8),  # bottom > 60
        ]
        v = self.bviol(rooms, self.pw, self.ph)
        self.assertEqual(len(v), 2)

    # ── layout_size_violations ───────────────────────────────────

    def test_size_no_violations(self):
        from utils.constants import ROOM_MIN_SIZES
        rooms = []
        for t in ("kitchen","bathroom","entrance"):
            mw, mh = ROOM_MIN_SIZES[t]
            rooms.append(self._r(t, 0, 0, mw, mh))
        self.assertEqual(self.sviol(rooms), [])

    def test_size_violation_detected(self):
        rooms = [self._r("kitchen", 0, 0, 3.0, 4.0)]  # below 7×8 minimum
        v = self.sviol(rooms)
        self.assertIn(0, v)

    # ── space_utilisation ────────────────────────────────────────

    def test_util_zero(self):
        self.assertEqual(self.space_util([], self.pw, self.ph), 0.0)

    def test_util_full(self):
        """Single room covering the full plot → utilisation = 1.0"""
        rooms = [self._r("living", 0, 0, self.pw, self.ph)]
        u = self.space_util(rooms, self.pw, self.ph)
        self.assertAlmostEqual(u, 1.0, places=4)

    def test_util_half(self):
        """Room covering half the plot → ~0.5"""
        rooms = [self._r("living", 0, 0, self.pw/2, self.ph)]
        u = self.space_util(rooms, self.pw, self.ph)
        self.assertAlmostEqual(u, 0.5, places=4)

    def test_util_range(self):
        """utilisation always in [0, 1]"""
        rooms = [self._r("living", 0, 0, 20, 30), self._r("kitchen", 20, 0, 20, 30)]
        u = self.space_util(rooms, self.pw, self.ph)
        self.assertGreaterEqual(u, 0.0)
        self.assertLessEqual(u, 1.0)

    # ── aspect_ratio_score ───────────────────────────────────────

    def test_ar_empty(self):
        self.assertEqual(self.ar_score([]), 0.0)

    def test_ar_perfect_squares(self):
        """Square rooms → score = 1.0"""
        rooms = [self._r("kitchen", 0, 0, 10, 10)]
        self.assertAlmostEqual(self.ar_score(rooms), 1.0, places=4)

    def test_ar_good_ratio(self):
        """2:1 ratio room → score = 1.0"""
        rooms = [self._r("living", 0, 0, 20, 10)]
        self.assertAlmostEqual(self.ar_score(rooms), 1.0, places=4)

    def test_ar_extreme_ratio_penalised(self):
        """Very elongated room → lower score"""
        good   = [self._r("balcony", 0, 0, 10, 10)]
        bad    = [self._r("balcony", 0, 0, 40, 2)]   # 20:1 ratio
        s_good = self.ar_score(good)
        s_bad  = self.ar_score(bad)
        self.assertGreater(s_good, s_bad)

    def test_ar_range(self):
        """aspect_ratio_score always in [0, 1]"""
        rooms = [self._r("living", 0, 0, 50, 2)]  # extreme
        s = self.ar_score(rooms)
        self.assertGreaterEqual(s, 0.0)
        self.assertLessEqual(s, 1.0)

    # ── is_valid_layout ──────────────────────────────────────────

    def test_is_valid_empty(self):
        ok, reason = self.is_valid([], self.pw, self.ph)
        self.assertFalse(ok)
        self.assertIsInstance(reason, str)

    def test_is_valid_good_layout(self):
        from utils.constants import ROOM_MIN_SIZES
        rooms = []
        for t, x, y in [("kitchen",5,5),("bathroom",20,5)]:
            mw, mh = ROOM_MIN_SIZES[t]
            rooms.append(self._r(t, x, y, mw, mh))
        ok_, reason = self.is_valid(rooms, self.pw, self.ph)
        self.assertTrue(ok_, f"Valid layout rejected: {reason}")

    def test_is_valid_out_of_bounds(self):
        rooms = [self._r("kitchen", 35, 5, 9, 10)]  # right edge = 44 > 40
        ok_, _ = self.is_valid(rooms, self.pw, self.ph)
        self.assertFalse(ok_)

    def test_is_valid_returns_reason_string(self):
        ok_, reason = self.is_valid([], self.pw, self.ph)
        self.assertIsInstance(reason, str)
        self.assertGreater(len(reason), 0)


# ════════════════════════════════════════════════════════════════
#  CUSTOM RUNNER
# ════════════════════════════════════════════════════════════════

class ColourResult(unittest.TestResult):
    def __init__(self, verbose=False):
        super().__init__(); self.verbose = verbose; self.passed = []; self._t0 = {}
    def startTest(self, test):
        super().startTest(test); self._t0[test] = time.perf_counter()
    def addSuccess(self, test):
        super().addSuccess(test)
        elapsed = (time.perf_counter() - self._t0[test]) * 1000
        self.passed.append((test, elapsed))
        if self.verbose:
            print(f"  {ok(f'{type(test).__name__}.{test._testMethodName}')}  {C_DIM}({elapsed:.1f}ms){C_RESET}")
    def addFailure(self, test, err):
        super().addFailure(test, err)
        elapsed = (time.perf_counter() - self._t0[test]) * 1000
        print(f"  {fail(f'{type(test).__name__}.{test._testMethodName}')}  {C_DIM}({elapsed:.1f}ms){C_RESET}")
        for line in traceback.format_exception(*err)[-3:]:
            print(f"    {C_RED}{line.rstrip()}{C_RESET}")
    def addError(self, test, err):
        super().addError(test, err)
        print(f"  {warn(f'ERROR: {type(test).__name__}.{test._testMethodName}')}")
        for line in traceback.format_exception(*err)[-3:]:
            print(f"    {C_YELLOW}{line.rstrip()}{C_RESET}")


def _bar(passed, total, width=20):
    if total == 0: return " " * width
    f = int(width * passed / total)
    col = C_GREEN if passed == total else C_RED
    return f"{col}{'█'*f}{'░'*(width-f)}{C_RESET}"


def run_tests(groups=None, verbose=False):
    ALL = {
        "room":       TestRoom,
        "layout":     TestLayout,
        "overlap":    TestOverlap,
        "validation": TestValidation,
    }
    selected = {k: v for k, v in ALL.items() if not groups or k in groups}
    if groups:
        unknown = set(groups) - set(ALL)
        if unknown:
            print(f"{C_RED}Unknown groups: {unknown}{C_RESET}"); sys.exit(1)

    print(f"\n{C_BOLD}{'═'*62}{C_RESET}")
    print(f"{C_BOLD}  IntelliPlan·3D  —  GEOMETRY MODULE TEST SUITE{C_RESET}")
    print(f"{C_BOLD}{'═'*62}{C_RESET}")
    print(f"  Groups: {C_CYAN}{', '.join(selected)}{C_RESET}\n")

    total_pass = total_fail = total_err = 0
    t_global = time.perf_counter()

    import logging; logging.disable(logging.CRITICAL)

    for name, cls in selected.items():
        suite  = unittest.TestLoader().loadTestsFromTestCase(cls)
        result = ColourResult(verbose=verbose)
        t0     = time.perf_counter()
        print(f"{C_BOLD}  [{name.upper()}]{C_RESET}  {C_DIM}{cls.__name__}{C_RESET}")
        suite.run(result)
        elapsed = (time.perf_counter() - t0) * 1000
        n_run   = result.testsRun
        n_fail  = len(result.failures)
        n_err   = len(result.errors)
        n_pass  = n_run - n_fail - n_err
        total_pass += n_pass; total_fail += n_fail; total_err += n_err
        status = f"{C_GREEN}PASS{C_RESET}" if n_fail+n_err == 0 else f"{C_RED}FAIL{C_RESET}"
        if not verbose:
            for test, err in result.failures + result.errors:
                print(f"  {fail(test._testMethodName)}")
                for line in traceback.format_exception(*err)[-2:]:
                    print(f"    {C_RED}{line.rstrip()}{C_RESET}")
        print(f"  {_bar(n_pass, n_run)}  {n_pass}/{n_run} passed  {C_DIM}({elapsed:.0f}ms){C_RESET}  {status}\n")

    logging.disable(logging.NOTSET)
    elapsed_total = (time.perf_counter() - t_global) * 1000
    total_run = total_pass + total_fail + total_err
    print(f"{C_BOLD}{'═'*62}{C_RESET}")
    if total_fail + total_err == 0:
        print(f"  {C_GREEN}{C_BOLD}ALL {total_run} TESTS PASSED ✓{C_RESET}  {C_DIM}({elapsed_total:.0f}ms){C_RESET}")
    else:
        print(f"  {C_RED}{C_BOLD}{total_fail+total_err} FAILED / {total_run} total{C_RESET}  {C_DIM}({elapsed_total:.0f}ms){C_RESET}")
    print(f"{C_BOLD}{'═'*62}{C_RESET}\n")
    return total_fail + total_err == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Geometry Module Test Suite")
    parser.add_argument("-t","--test", nargs="+",
                        choices=["room","layout","overlap","validation"],
                        help="Run specific group(s)", metavar="GROUP")
    parser.add_argument("-v","--verbose", action="store_true")
    args = parser.parse_args()
    success = run_tests(groups=args.test, verbose=args.verbose)
    sys.exit(0 if success else 1)
