"""
╔══════════════════════════════════════════════════════════════════╗
║       IntelliPlan·3D — VASTU ENGINE TEST SUITE                  ║
║       test_vastu_engine.py                                       ║
║                                                                  ║
║  Run:  python test_vastu_engine.py                               ║
║  Run:  python test_vastu_engine.py -v         (verbose)          ║
║  Run:  python test_vastu_engine.py -t zones   (single group)     ║
║                                                                  ║
║  Groups: zones  rules  score                                     ║
╚══════════════════════════════════════════════════════════════════╝
"""

import sys, os, time, unittest, argparse, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── colour helpers ───────────────────────────────────────────────
C_RESET = "\033[0m"; C_GREEN = "\033[92m"; C_RED = "\033[91m"
C_YELLOW = "\033[93m"; C_CYAN = "\033[96m"; C_BOLD = "\033[1m"; C_DIM = "\033[2m"
ok   = lambda m: f"{C_GREEN}✓{C_RESET} {m}"
fail = lambda m: f"{C_RED}✗{C_RESET} {m}"
warn = lambda m: f"{C_YELLOW}⚠{C_RESET} {m}"

# ════════════════════════════════════════════════════════════════
#  HELPERS
# ════════════════════════════════════════════════════════════════

def _room(t, x, y, w, h):
    from geometry.room import Room
    return Room(type=t, x=x, y=y, width=w, height=h)

def _plot(w=40.0, h=60.0):
    return w, h

# ════════════════════════════════════════════════════════════════
#  TEST GROUP 1 — direction_utils.py
# ════════════════════════════════════════════════════════════════

class TestDirectionUtils(unittest.TestCase):
    """Tests for vastu_engine/direction_utils.py — zone detection logic"""

    def setUp(self):
        from vastu_engine.direction_utils import (
            get_room_zone, is_in_zone, cardinal_to_description, _local_to_cardinal
        )
        self.get_room_zone       = get_room_zone
        self.is_in_zone          = is_in_zone
        self.cardinal_to_desc    = cardinal_to_description
        self._local_to_cardinal  = _local_to_cardinal
        self.pw, self.ph = 40.0, 60.0

    # ── zone grid coverage ───────────────────────────────────────

    def test_ne_corner_north_facing(self):
        """Top-right corner → NE for North-facing plot"""
        # top-right: x near plot_w, y near 0
        room = _room("pooja", x=self.pw*0.7, y=0, w=4, h=4)
        z = self.get_room_zone(room, self.pw, self.ph, "North")
        self.assertEqual(z, "NE", f"Expected NE, got {z}")

    def test_sw_corner_north_facing(self):
        """Bottom-left corner → SW for North-facing plot"""
        room = _room("store", x=0, y=self.ph*0.7, w=4, h=4)
        z = self.get_room_zone(room, self.pw, self.ph, "North")
        self.assertEqual(z, "SW", f"Expected SW, got {z}")

    def test_centre_zone(self):
        """Dead-centre room → C (Brahmasthana)"""
        cx = self.pw * 0.5 - 2
        cy = self.ph * 0.5 - 2
        room = _room("living", x=cx, y=cy, w=4, h=4)
        z = self.get_room_zone(room, self.pw, self.ph, "North")
        self.assertEqual(z, "C")

    def test_all_nine_zones_north_facing(self):
        """All 9 grid positions map to distinct zones for North-facing"""
        positions = {
            "NW": (0.05, 0.05), "N":  (0.5, 0.05), "NE": (0.85, 0.05),
            "W":  (0.05, 0.5),  "C":  (0.5, 0.5),  "E":  (0.85, 0.5),
            "SW": (0.05, 0.85), "S":  (0.5, 0.85),  "SE": (0.85, 0.85),
        }
        for expected_zone, (xf, yf) in positions.items():
            room = _room("living",
                         x=self.pw*xf - 1, y=self.ph*yf - 1,
                         w=2, h=2)
            got = self.get_room_zone(room, self.pw, self.ph, "North")
            self.assertEqual(got, expected_zone,
                             f"Position ({xf},{yf}) → expected {expected_zone}, got {got}")

    # ── facing rotation ──────────────────────────────────────────

    def test_facing_rotations_ne_corner(self):
        """
        A room in the top-right of the plot maps to different cardinal
        zones depending on facing direction.
        NE corner (local top-right) maps to:
          North → NE,  East → SE,  South → SW,  West → NW
        """
        room = _room("pooja", x=self.pw*0.7, y=0, w=4, h=4)
        expected = {"North": "NE", "East": "SE", "South": "SW", "West": "NW"}
        for facing, exp_zone in expected.items():
            got = self.get_room_zone(room, self.pw, self.ph, facing)
            self.assertEqual(got, exp_zone,
                             f"Facing={facing}: expected {exp_zone}, got {got}")

    def test_all_four_facings_return_valid_zone(self):
        """get_room_zone always returns a valid 9-zone string"""
        valid = {"N","NE","E","SE","S","SW","W","NW","C"}
        room = _room("kitchen", x=10, y=5, w=8, h=10)
        for facing in ("North","East","South","West"):
            z = self.get_room_zone(room, self.pw, self.ph, facing)
            self.assertIn(z, valid, f"Facing={facing} returned invalid zone '{z}'")

    # ── is_in_zone ───────────────────────────────────────────────

    def test_is_in_zone_true(self):
        """is_in_zone returns True when zone matches"""
        room = _room("kitchen", x=self.pw*0.7, y=self.ph*0.7, w=4, h=4)
        result = self.is_in_zone(room, self.pw, self.ph, "North", ("SE", "S"))
        self.assertTrue(result)

    def test_is_in_zone_false(self):
        """is_in_zone returns False when zone doesn't match"""
        room = _room("kitchen", x=0, y=0, w=4, h=4)
        result = self.is_in_zone(room, self.pw, self.ph, "North", ("SE",))
        self.assertFalse(result)

    # ── cardinal_to_description ──────────────────────────────────

    def test_cardinal_descriptions_not_empty(self):
        """cardinal_to_description returns a non-empty string for all zones"""
        for zone in ("N","NE","E","SE","S","SW","W","NW","C"):
            desc = self.cardinal_to_desc(zone)
            self.assertIsInstance(desc, str)
            self.assertGreater(len(desc), 0, f"Empty description for zone '{zone}'")

    def test_unknown_zone_returns_string(self):
        """cardinal_to_description handles unknown zone gracefully"""
        desc = self.cardinal_to_desc("XY")
        self.assertIsInstance(desc, str)


# ════════════════════════════════════════════════════════════════
#  TEST GROUP 2 — vastu_rules.py
# ════════════════════════════════════════════════════════════════

class TestVastuRules(unittest.TestCase):
    """Tests for vastu_engine/vastu_rules.py — all 16 individual rules"""

    def setUp(self):
        from vastu_engine import vastu_rules as vr
        self.vr = vr
        self.pw, self.ph, self.facing = 40.0, 60.0, "North"

    def _call(self, fn, rooms):
        return fn(rooms, self.pw, self.ph, self.facing)

    def _assert_result_schema(self, result):
        """Every rule result must have these keys with correct types."""
        for key in ("key","label","status","weight","earned","description"):
            self.assertIn(key, result, f"Rule result missing key '{key}'")
        self.assertIn(result["status"],
                      {"compliant","partial","violation","missing"})
        self.assertGreaterEqual(result["weight"], 0)
        self.assertGreaterEqual(result["earned"], 0)
        self.assertLessEqual(result["earned"], result["weight"] + 0.01,
                             "earned > weight")

    # ── schema tests (all rules must return valid structure) ─────

    def test_all_rules_schema_no_rooms(self):
        """All rules return valid schema even with empty room list"""
        for rule_fn in self.vr.ALL_RULES:
            result = self._call(rule_fn, [])
            self._assert_result_schema(result)

    def test_all_rules_schema_full_2bhk(self):
        """All rules return valid schema with a complete 2BHK layout"""
        pw, ph = 40.0, 60.0
        rooms = [
            _room("entrance",       x=14, y=0,  w=9,  h=4),
            _room("living",         x=0,  y=4,  w=22, h=18),
            _room("kitchen",        x=22, y=4,  w=18, h=16), # SE
            _room("dining",         x=22, y=20, w=18, h=8),
            _room("master_bedroom", x=0,  y=22, w=22, h=18), # SW
            _room("bedroom",        x=22, y=28, w=18, h=18),
            _room("bathroom",       x=0,  y=40, w=12, h=8),
            _room("toilet",         x=12, y=40, w=10, h=8),
            _room("balcony",        x=22, y=46, w=18, h=6),
            _room("pooja",          x=0,  y=48, w=8,  h=8),  # SW (not ideal)
            _room("store",          x=8,  y=48, w=14, h=8),
        ]
        for rule_fn in self.vr.ALL_RULES:
            result = self._call(rule_fn, rooms)
            self._assert_result_schema(result)

    # ── individual rule logic ────────────────────────────────────

    def test_kitchen_se_compliant(self):
        """Kitchen in SE zone → compliant"""
        # For North-facing: SE is bottom-right (x>2/3, y>2/3)
        room = _room("kitchen", x=28, y=42, w=10, h=12)
        r = self._call(self.vr.rule_kitchen, [room])
        self.assertEqual(r["status"], "compliant", f"SE kitchen not compliant: {r}")
        self.assertEqual(r["earned"], r["weight"])

    def test_kitchen_missing(self):
        """No kitchen rooms → missing status"""
        r = self._call(self.vr.rule_kitchen, [])
        self.assertEqual(r["status"], "missing")
        self.assertEqual(r["earned"], 0)

    def test_kitchen_wrong_zone_violation(self):
        """Kitchen in SW zone → violation"""
        room = _room("kitchen", x=0, y=42, w=10, h=12)
        r = self._call(self.vr.rule_kitchen, [room])
        self.assertIn(r["status"], ("violation", "partial"),
                      "SW kitchen should be violation or partial")

    def test_master_bedroom_sw_compliant(self):
        """Master bedroom in SW zone → compliant"""
        room = _room("master_bedroom", x=0, y=42, w=14, h=14)
        r = self._call(self.vr.rule_master_bedroom, [room])
        self.assertEqual(r["status"], "compliant")
        self.assertEqual(r["earned"], r["weight"])

    def test_master_bedroom_missing(self):
        """No master bedroom → missing"""
        r = self._call(self.vr.rule_master_bedroom, [])
        self.assertEqual(r["status"], "missing")

    def test_pooja_ne_compliant(self):
        """Pooja in NE zone → compliant"""
        # NE for North-facing: top-right (x>2/3, y<1/3)
        room = _room("pooja", x=28, y=0, w=8, h=8)
        r = self._call(self.vr.rule_pooja_room, [room])
        self.assertEqual(r["status"], "compliant",
                         f"NE pooja should be compliant: {r}")

    def test_pooja_sw_violation(self):
        """Pooja in SW zone → violation"""
        room = _room("pooja", x=0, y=42, w=6, h=6)
        r = self._call(self.vr.rule_pooja_room, [room])
        self.assertEqual(r["status"], "violation")
        self.assertEqual(r["earned"], 0)

    def test_living_north_compliant(self):
        """Living room in North zone → compliant"""
        room = _room("living", x=8, y=0, w=22, h=14)
        r = self._call(self.vr.rule_living_room, [room])
        self.assertEqual(r["status"], "compliant")

    def test_bathroom_nw_compliant(self):
        """Bathroom in NW zone → compliant"""
        # NW for North-facing: top-left (x<1/3, y<1/3)
        room = _room("bathroom", x=0, y=0, w=7, h=8)
        r = self._call(self.vr.rule_bathroom, [room])
        self.assertEqual(r["status"], "compliant")

    def test_bathroom_multiple_mixed(self):
        """Mixed bathrooms (some correct, some not) → partial"""
        good = _room("bathroom", x=0,  y=0,  w=6, h=7)   # NW
        bad  = _room("toilet",   x=0,  y=42, w=6, h=6)   # SW
        r = self._call(self.vr.rule_bathroom, [good, bad])
        self.assertIn(r["status"], ("partial", "violation"))

    def test_entrance_north_compliant(self):
        """Entrance on North side → compliant"""
        room = _room("entrance", x=14, y=0, w=9, h=4)
        r = self._call(self.vr.rule_entrance, [room])
        self.assertEqual(r["status"], "compliant")

    def test_balcony_east_compliant(self):
        """Balcony on East side → compliant"""
        # East for North-facing: right side (x>2/3)
        room = _room("balcony", x=28, y=22, w=12, h=6)
        r = self._call(self.vr.rule_balcony, [room])
        self.assertEqual(r["status"], "compliant")

    def test_ne_corner_clear_compliant(self):
        """No heavy rooms in NE → compliant"""
        light_rooms = [
            _room("pooja",   x=28, y=0, w=8, h=8),
            _room("balcony", x=22, y=0, w=6, h=5),
        ]
        r = self._call(self.vr.rule_staircase_zone, light_rooms)
        self.assertEqual(r["status"], "compliant")

    def test_ne_corner_heavy_violation(self):
        """Kitchen in NE corner → violation for NE-clear rule"""
        bad_room = _room("kitchen", x=28, y=0, w=10, h=12)
        r = self._call(self.vr.rule_staircase_zone, [bad_room])
        self.assertEqual(r["status"], "violation")

    def test_centre_open_compliant(self):
        """No rooms in centre → centre-open compliant"""
        peripheral = [
            _room("living", x=0,  y=0,  w=12, h=18),
            _room("kitchen",x=28, y=42, w=10, h=12),
        ]
        r = self._call(self.vr.rule_centre_open, peripheral)
        self.assertEqual(r["status"], "compliant")

    def test_water_not_sw_compliant(self):
        """Bathrooms not in SW → water-source rule compliant"""
        rooms = [_room("bathroom", x=0, y=0, w=6, h=7)]  # NW
        r = self._call(self.vr.rule_water_source, rooms)
        self.assertEqual(r["status"], "compliant")

    def test_water_in_sw_violation(self):
        """Bathroom in SW → water-source rule violation"""
        rooms = [_room("bathroom", x=0, y=42, w=6, h=7)]  # SW
        r = self._call(self.vr.rule_water_source, rooms)
        self.assertEqual(r["status"], "violation")

    # ── ALL_RULES list ───────────────────────────────────────────

    def test_all_rules_count(self):
        """ALL_RULES contains exactly 15 rules"""
        self.assertEqual(len(self.vr.ALL_RULES), 15,
                         f"Expected 15 rules, got {len(self.vr.ALL_RULES)}")

    def test_all_rules_are_callable(self):
        """Every item in ALL_RULES is callable"""
        for fn in self.vr.ALL_RULES:
            self.assertTrue(callable(fn), f"{fn} is not callable")

    def test_all_rules_unique_keys(self):
        """Every rule returns a unique 'key' field"""
        rooms = [_room("kitchen", x=28, y=42, w=10, h=12)]
        keys = [self._call(fn, rooms)["key"] for fn in self.vr.ALL_RULES]
        self.assertEqual(len(keys), len(set(keys)),
                         f"Duplicate rule keys found: {keys}")


# ════════════════════════════════════════════════════════════════
#  TEST GROUP 3 — vastu_score.py
# ════════════════════════════════════════════════════════════════

class TestVastuScore(unittest.TestCase):
    """Tests for vastu_engine/vastu_score.py — aggregate scoring"""

    def setUp(self):
        from vastu_engine.vastu_score import compute_vastu_score
        self.compute = compute_vastu_score
        self.pw, self.ph = 40.0, 60.0

    # ── score range ──────────────────────────────────────────────

    def test_score_range_zero_rooms(self):
        """Empty room list returns score in [0, 100]"""
        score, rules = self.compute([], self.pw, self.ph, "North")
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score,   100.0)

    def test_score_range_full_layout(self):
        """Full layout score always in [0, 100]"""
        rooms = [
            _room("entrance",       x=14, y=0,  w=9,  h=4),
            _room("living",         x=0,  y=4,  w=22, h=18),
            _room("kitchen",        x=28, y=42, w=10, h=12),
            _room("master_bedroom", x=0,  y=42, w=16, h=14),
            _room("pooja",          x=28, y=0,  w=8,  h=8),
            _room("bathroom",       x=0,  y=0,  w=7,  h=8),
        ]
        for facing in ("North","East","South","West"):
            score, _ = self.compute(rooms, self.pw, self.ph, facing)
            self.assertGreaterEqual(score, 0.0,   f"{facing}: score < 0")
            self.assertLessEqual(score,   100.0,  f"{facing}: score > 100")

    # ── ideal layout scores higher ───────────────────────────────

    def test_vastu_compliant_layout_scores_higher(self):
        """
        A layout with rooms in Vastu-correct zones should score higher
        than one with all rooms in wrong zones.
        """
        # Correct: kitchen=SE, pooja=NE, master_bed=SW, bathroom=NW
        good = [
            _room("kitchen",        x=28, y=42, w=10, h=12),  # SE
            _room("pooja",          x=28, y=0,  w=8,  h=8),   # NE
            _room("master_bedroom", x=0,  y=42, w=14, h=14),  # SW
            _room("bathroom",       x=0,  y=0,  w=7,  h=8),   # NW
            _room("living",         x=8,  y=0,  w=18, h=14),  # N
            _room("entrance",       x=14, y=0,  w=9,  h=4),   # N
        ]
        # Wrong: everything in obviously wrong zones
        bad = [
            _room("kitchen",        x=0,  y=0,  w=10, h=12),  # NW
            _room("pooja",          x=0,  y=42, w=8,  h=8),   # SW
            _room("master_bedroom", x=28, y=0,  w=14, h=14),  # NE
            _room("bathroom",       x=28, y=42, w=7,  h=8),   # SE
            _room("living",         x=0,  y=42, w=18, h=14),  # SW
            _room("entrance",       x=0,  y=42, w=9,  h=4),   # SW
        ]
        good_score, _ = self.compute(good, self.pw, self.ph, "North")
        bad_score,  _ = self.compute(bad,  self.pw, self.ph, "North")
        self.assertGreater(good_score, bad_score,
                           f"Good layout ({good_score:.1f}) not > bad ({bad_score:.1f})")

    # ── rules returned ───────────────────────────────────────────

    def test_returns_rule_list(self):
        """compute_vastu_score returns a list of rule dicts"""
        _, rules = self.compute([], self.pw, self.ph, "North")
        self.assertIsInstance(rules, list)
        self.assertGreater(len(rules), 0)

    def test_rules_have_required_keys(self):
        """Every returned rule has all required frontend keys"""
        _, rules = self.compute([], self.pw, self.ph, "East")
        required = {"label","status","weight","earned","description"}
        for rule in rules:
            missing = required - set(rule.keys())
            self.assertFalse(missing, f"Rule missing keys: {missing}")

    def test_earned_never_exceeds_weight(self):
        """earned ≤ weight for every rule in every facing direction"""
        rooms = [_room("kitchen", x=28, y=42, w=10, h=12)]
        for facing in ("North","East","South","West"):
            _, rules = self.compute(rooms, self.pw, self.ph, facing)
            for r in rules:
                self.assertLessEqual(
                    r["earned"], r["weight"] + 0.01,
                    f"Rule '{r['label']}' earned={r['earned']} > weight={r['weight']}"
                )

    def test_score_formula_consistency(self):
        """Score equals (sum of earned / sum of weight) * 100"""
        rooms = [
            _room("kitchen",  x=28, y=42, w=10, h=12),
            _room("pooja",    x=28, y=0,  w=8,  h=8),
            _room("bathroom", x=0,  y=0,  w=7,  h=8),
        ]
        score, rules = self.compute(rooms, self.pw, self.ph, "North")
        total_w = sum(r["weight"] for r in rules)
        total_e = sum(r["earned"] for r in rules)
        expected = round((total_e / total_w) * 100, 2) if total_w > 0 else 0.0
        self.assertAlmostEqual(score, expected, places=1,
                               msg=f"Score formula mismatch: {score} vs {expected}")

    def test_all_four_facings_produce_different_scores(self):
        """Rotating the facing changes the Vastu score (rooms stay the same)"""
        rooms = [
            _room("kitchen",        x=28, y=42, w=10, h=12),
            _room("pooja",          x=28, y=0,  w=8,  h=8),
            _room("master_bedroom", x=0,  y=42, w=14, h=14),
        ]
        scores = {
            f: self.compute(rooms, self.pw, self.ph, f)[0]
            for f in ("North","East","South","West")
        }
        # At least two facings should produce different scores
        unique_scores = set(scores.values())
        self.assertGreater(len(unique_scores), 1,
                           f"All facings gave identical scores: {scores}")


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
        "zones": TestDirectionUtils,
        "rules": TestVastuRules,
        "score": TestVastuScore,
    }
    selected = {k: v for k, v in ALL.items() if not groups or k in groups}
    if groups:
        unknown = set(groups) - set(ALL)
        if unknown:
            print(f"{C_RED}Unknown groups: {unknown}{C_RESET}"); sys.exit(1)

    print(f"\n{C_BOLD}{'═'*62}{C_RESET}")
    print(f"{C_BOLD}  IntelliPlan·3D  —  VASTU ENGINE TEST SUITE{C_RESET}")
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
    parser = argparse.ArgumentParser(description="Vastu Engine Test Suite")
    parser.add_argument("-t","--test", nargs="+", choices=["zones","rules","score"],
                        help="Run specific group(s)", metavar="GROUP")
    parser.add_argument("-v","--verbose", action="store_true")
    args = parser.parse_args()
    success = run_tests(groups=args.test, verbose=args.verbose)
    sys.exit(0 if success else 1)
