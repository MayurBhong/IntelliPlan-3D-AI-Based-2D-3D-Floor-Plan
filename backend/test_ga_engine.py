"""
╔══════════════════════════════════════════════════════════════════╗
║          IntelliPlan·3D — GA ENGINE TEST SUITE                  ║
║          test_ga_engine.py                                       ║
║                                                                  ║
║  Run:  python3 test_ga_engine.py                                 ║
║  Run:  python3 test_ga_engine.py -v          (verbose)           ║
║  Run:  python3 test_ga_engine.py -t fitness  (single group)      ║
╚══════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import time
import math
import unittest
import argparse
import traceback
from io import StringIO
from typing import List

# ── path setup ──────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── colour helpers (no dependencies) ────────────────────────────
C_RESET  = "\033[0m"
C_GREEN  = "\033[92m"
C_RED    = "\033[91m"
C_YELLOW = "\033[93m"
C_CYAN   = "\033[96m"
C_BOLD   = "\033[1m"
C_DIM    = "\033[2m"

def ok(msg):   return f"{C_GREEN}✓{C_RESET} {msg}"
def fail(msg): return f"{C_RED}✗{C_RESET} {msg}"
def info(msg): return f"{C_CYAN}•{C_RESET} {msg}"
def warn(msg): return f"{C_YELLOW}⚠{C_RESET} {msg}"
def bold(msg): return f"{C_BOLD}{msg}{C_RESET}"

# ════════════════════════════════════════════════════════════════
#  TEST GROUP 1 — chromosome.py
# ════════════════════════════════════════════════════════════════

class TestChromosome(unittest.TestCase):
    """Tests for ga_engine/chromosome.py — encode, decode, random_chromosome"""

    def setUp(self):
        import numpy as np
        from geometry.room import Room
        from ga_engine.chromosome import (
            encode, decode, chromosome_length, random_chromosome, GENES_PER_ROOM
        )
        self.np  = np
        self.Room = Room
        self.encode             = encode
        self.decode             = decode
        self.chromosome_length  = chromosome_length
        self.random_chromosome  = random_chromosome
        self.GENES_PER_ROOM     = GENES_PER_ROOM
        self.rng = np.random.default_rng(42)

        self.plot_w, self.plot_h = 40.0, 60.0
        self.rooms = [
            Room("kitchen",        x=5.0,  y=5.0,  width=9.0,  height=10.0),  # min 7×8
            Room("living",         x=15.0, y=5.0,  width=15.0, height=12.0),  # min 10×12
            Room("master_bedroom", x=5.0,  y=18.0, width=12.0, height=12.0),  # min 10×12
            Room("bathroom",       x=18.0, y=18.0, width=6.0,  height=7.0),   # min 5×6
        ]
        self.types = [r.type for r in self.rooms]

    # ── encoding tests ───────────────────────────────────────────

    def test_chromosome_length(self):
        """chromosome_length(n) == n * 4"""
        for n in [1, 4, 8, 11, 14]:
            self.assertEqual(self.chromosome_length(n), n * self.GENES_PER_ROOM)

    def test_encode_shape(self):
        """encode() returns flat array of correct length"""
        chrom = self.encode(self.rooms, self.plot_w, self.plot_h)
        self.assertEqual(len(chrom), len(self.rooms) * self.GENES_PER_ROOM)

    def test_encode_range(self):
        """All encoded genes are in [0, 1]"""
        chrom = self.encode(self.rooms, self.plot_w, self.plot_h)
        self.assertTrue(self.np.all(chrom >= 0.0), "gene below 0")
        self.assertTrue(self.np.all(chrom <= 1.0), "gene above 1")

    def test_encode_dtype(self):
        """encode() returns float32"""
        chrom = self.encode(self.rooms, self.plot_w, self.plot_h)
        self.assertEqual(chrom.dtype, self.np.float32)

    # ── decoding tests ───────────────────────────────────────────

    def test_decode_count(self):
        """decode() returns correct number of rooms"""
        chrom = self.encode(self.rooms, self.plot_w, self.plot_h)
        out   = self.decode(chrom, self.types, self.plot_w, self.plot_h)
        self.assertEqual(len(out), len(self.rooms))

    def test_decode_types(self):
        """decode() preserves room types in order"""
        chrom = self.encode(self.rooms, self.plot_w, self.plot_h)
        out   = self.decode(chrom, self.types, self.plot_w, self.plot_h)
        for original, decoded in zip(self.rooms, out):
            self.assertEqual(original.type, decoded.type)

    def test_encode_decode_roundtrip(self):
        """encode→decode preserves x, y, width, height within 0.1 ft tolerance"""
        chrom = self.encode(self.rooms, self.plot_w, self.plot_h)
        out   = self.decode(chrom, self.types, self.plot_w, self.plot_h)
        for orig, dec in zip(self.rooms, out):
            self.assertAlmostEqual(orig.x,      dec.x,      delta=0.1, msg=f"{orig.type} x")
            self.assertAlmostEqual(orig.y,      dec.y,      delta=0.1, msg=f"{orig.type} y")
            self.assertAlmostEqual(orig.width,  dec.width,  delta=0.1, msg=f"{orig.type} w")
            self.assertAlmostEqual(orig.height, dec.height, delta=0.1, msg=f"{orig.type} h")

    def test_decode_bounds(self):
        """decode() rooms never exceed plot boundaries"""
        chrom = self.encode(self.rooms, self.plot_w, self.plot_h)
        for room in self.decode(chrom, self.types, self.plot_w, self.plot_h):
            self.assertGreaterEqual(room.x, 0.0,            f"{room.type} x < 0")
            self.assertGreaterEqual(room.y, 0.0,            f"{room.type} y < 0")
            self.assertLessEqual(room.right,  self.plot_w,  f"{room.type} right > plot_w")
            self.assertLessEqual(room.bottom, self.plot_h,  f"{room.type} bottom > plot_h")

    def test_decode_minimum_sizes(self):
        """decode() enforces minimum room sizes"""
        from utils.constants import ROOM_MIN_SIZES
        # Create chromosome with near-zero sizes
        import numpy as np
        zero_chrom = np.zeros(self.chromosome_length(len(self.types)), dtype=np.float32)
        out = self.decode(zero_chrom, self.types, self.plot_w, self.plot_h)
        for room in out:
            min_w, min_h = ROOM_MIN_SIZES.get(room.type, (3.0, 3.0))
            self.assertGreaterEqual(room.width,  min_w, f"{room.type} width below minimum")
            self.assertGreaterEqual(room.height, min_h, f"{room.type} height below minimum")

    # ── random chromosome tests ──────────────────────────────────

    def test_random_chromosome_shape(self):
        """random_chromosome() returns correct length"""
        chrom = self.random_chromosome(self.types, self.plot_w, self.plot_h, self.rng)
        self.assertEqual(len(chrom), self.chromosome_length(len(self.types)))

    def test_random_chromosome_range(self):
        """random_chromosome() genes all in [0, 1]"""
        chrom = self.random_chromosome(self.types, self.plot_w, self.plot_h, self.rng)
        self.assertTrue(self.np.all(chrom >= 0.0))
        self.assertTrue(self.np.all(chrom <= 1.0))

    def test_random_chromosomes_differ(self):
        """Different seeds produce different chromosomes"""
        rng1 = self.np.random.default_rng(1)
        rng2 = self.np.random.default_rng(2)
        c1 = self.random_chromosome(self.types, self.plot_w, self.plot_h, rng1)
        c2 = self.random_chromosome(self.types, self.plot_w, self.plot_h, rng2)
        self.assertFalse(self.np.array_equal(c1, c2))


# ════════════════════════════════════════════════════════════════
#  TEST GROUP 2 — population.py
# ════════════════════════════════════════════════════════════════

class TestPopulation(unittest.TestCase):
    """Tests for ga_engine/population.py"""

    def setUp(self):
        import numpy as np
        from ga_engine.population import initialise_population, population_diversity
        from ga_engine.chromosome import chromosome_length
        self.np               = np
        self.init_pop         = initialise_population
        self.diversity        = population_diversity
        self.chrom_len        = chromosome_length
        self.types = ["entrance","living","kitchen","master_bedroom",
                      "bedroom","bathroom","balcony","pooja","store"]
        self.pw, self.ph = 40.0, 60.0

    def test_population_shape(self):
        """Population has correct (pop_size, chrom_len) shape"""
        pop = self.init_pop(50, self.types, self.pw, self.ph, seed=0)
        self.assertEqual(pop.shape, (50, self.chrom_len(len(self.types))))

    def test_population_range(self):
        """All gene values are in [0, 1]"""
        pop = self.init_pop(30, self.types, self.pw, self.ph, seed=1)
        self.assertTrue(self.np.all(pop >= 0.0))
        self.assertTrue(self.np.all(pop <= 1.0))

    def test_population_dtype(self):
        """Population array is float32"""
        pop = self.init_pop(20, self.types, self.pw, self.ph, seed=2)
        self.assertEqual(pop.dtype, self.np.float32)

    def test_population_diversity_positive(self):
        """A freshly initialised population has non-zero diversity"""
        pop = self.init_pop(30, self.types, self.pw, self.ph, seed=3)
        div = self.diversity(pop)
        self.assertGreater(div, 0.0, "population diversity is zero — all chromosomes identical")

    def test_population_different_seeds(self):
        """Different seeds produce different populations"""
        p1 = self.init_pop(20, self.types, self.pw, self.ph, seed=10)
        p2 = self.init_pop(20, self.types, self.pw, self.ph, seed=99)
        self.assertFalse(self.np.array_equal(p1, p2))

    def test_single_member_diversity(self):
        """Diversity of a single-chromosome population is 0"""
        pop = self.init_pop(1, self.types, self.pw, self.ph, seed=0)
        div = self.diversity(pop)
        self.assertEqual(div, 0.0)

    def test_various_bhk_sizes(self):
        """Population initialisation works for all BHK sizes"""
        from utils.constants import BHK_ROOM_COMPOSITIONS
        for bhk, types in BHK_ROOM_COMPOSITIONS.items():
            pop = self.init_pop(10, types, 40.0, 60.0, seed=0)
            self.assertEqual(pop.shape[0], 10,  f"{bhk}: wrong pop size")
            self.assertEqual(pop.shape[1], self.chrom_len(len(types)),
                             f"{bhk}: wrong chrom length")


# ════════════════════════════════════════════════════════════════
#  TEST GROUP 3 — fitness.py
# ════════════════════════════════════════════════════════════════

class TestFitness(unittest.TestCase):
    """Tests for ga_engine/fitness.py — evaluate_fitness, evaluate_population"""

    def setUp(self):
        import numpy as np
        from geometry.room import Room
        from ga_engine.fitness import evaluate_fitness, evaluate_population
        from ga_engine.population import initialise_population
        from ga_engine.chromosome import decode
        self.np                 = np
        self.Room               = Room
        self.evaluate_fitness   = evaluate_fitness
        self.evaluate_population= evaluate_population
        self.init_pop           = initialise_population
        self.decode             = decode
        self.pw, self.ph = 40.0, 60.0
        self.facing      = "East"
        self.types = ["entrance","living","dining","kitchen",
                      "master_bedroom","bedroom","bathroom",
                      "toilet","balcony","pooja","store"]

    def _make_rooms(self):
        """Decode a single chromosome into rooms"""
        from ga_engine.chromosome import random_chromosome
        rng   = self.np.random.default_rng(42)
        chrom = random_chromosome(self.types, self.pw, self.ph, rng)
        return self.decode(chrom, self.types, self.pw, self.ph)

    # ── single evaluation ────────────────────────────────────────

    def test_fitness_return_types(self):
        """evaluate_fitness returns (float, float, float, list)"""
        rooms = self._make_rooms()
        fit, vastu, util, rules = self.evaluate_fitness(rooms, self.pw, self.ph, self.facing)
        self.assertIsInstance(fit,   float)
        self.assertIsInstance(vastu, float)
        self.assertIsInstance(util,  float)
        self.assertIsInstance(rules, list)

    def test_fitness_ranges(self):
        """Fitness, vastu, util all in valid ranges"""
        rooms = self._make_rooms()
        fit, vastu, util, rules = self.evaluate_fitness(rooms, self.pw, self.ph, self.facing)
        self.assertGreaterEqual(fit,   0.0);  self.assertLessEqual(fit,   1.0)
        self.assertGreaterEqual(vastu, 0.0);  self.assertLessEqual(vastu, 100.0)
        self.assertGreaterEqual(util,  0.0);  self.assertLessEqual(util,  100.0)

    def test_vastu_rules_count(self):
        """At least 8 Vastu rules returned"""
        rooms = self._make_rooms()
        _, _, _, rules = self.evaluate_fitness(rooms, self.pw, self.ph, self.facing)
        self.assertGreaterEqual(len(rules), 8)

    def test_vastu_rule_schema(self):
        """Each Vastu rule has required keys"""
        rooms = self._make_rooms()
        _, _, _, rules = self.evaluate_fitness(rooms, self.pw, self.ph, self.facing)
        required = {"label", "status", "weight", "earned", "description"}
        for rule in rules:
            missing = required - set(rule.keys())
            self.assertFalse(missing, f"Rule missing keys: {missing}")

    def test_vastu_rule_status_values(self):
        """Rule status values are one of the valid set"""
        rooms = self._make_rooms()
        _, _, _, rules = self.evaluate_fitness(rooms, self.pw, self.ph, self.facing)
        valid = {"compliant", "partial", "violation", "missing"}
        for rule in rules:
            self.assertIn(rule["status"], valid,
                          f"Invalid status '{rule['status']}' for rule '{rule['label']}'")

    def test_vastu_earned_le_weight(self):
        """Earned score never exceeds weight for any rule"""
        rooms = self._make_rooms()
        _, _, _, rules = self.evaluate_fitness(rooms, self.pw, self.ph, self.facing)
        for rule in rules:
            self.assertLessEqual(rule["earned"], rule["weight"] + 0.01,
                                 f"Rule '{rule['label']}' earned > weight")

    def test_overlapping_rooms_penalty(self):
        """Heavily overlapping rooms score lower than non-overlapping"""
        # Non-overlapping layout
        good_rooms = [
            self.Room("kitchen",  x=0,  y=0,  width=10, height=10),
            self.Room("living",   x=10, y=0,  width=20, height=15),
            self.Room("bathroom", x=0,  y=10, width=8,  height=8),
        ]
        # Fully overlapping layout (all rooms at origin)
        bad_rooms = [
            self.Room("kitchen",  x=0, y=0, width=10, height=10),
            self.Room("living",   x=1, y=1, width=10, height=10),
            self.Room("bathroom", x=2, y=2, width=8,  height=8),
        ]
        good_fit, _, _, _ = self.evaluate_fitness(good_rooms, self.pw, self.ph, self.facing)
        bad_fit,  _, _, _ = self.evaluate_fitness(bad_rooms,  self.pw, self.ph, self.facing)
        self.assertGreater(good_fit, bad_fit,
                           "Non-overlapping layout should score higher than overlapping")

    def test_all_facing_directions(self):
        """evaluate_fitness works for all 4 facing directions"""
        rooms = self._make_rooms()
        for facing in ("North", "East", "South", "West"):
            fit, vastu, util, rules = self.evaluate_fitness(rooms, self.pw, self.ph, facing)
            self.assertGreaterEqual(fit, 0.0, f"{facing}: fitness < 0")
            self.assertLessEqual(fit,   1.0, f"{facing}: fitness > 1")

    # ── population evaluation ────────────────────────────────────

    def test_population_fitness_shape(self):
        """evaluate_population returns 1-D array of length pop_size"""
        pop  = self.init_pop(20, self.types, self.pw, self.ph, seed=0)
        fits = self.evaluate_population(pop, self.types, self.pw, self.ph, self.facing)
        self.assertEqual(fits.shape, (20,))

    def test_population_fitness_range(self):
        """All population fitness values in [0, 1]"""
        pop  = self.init_pop(20, self.types, self.pw, self.ph, seed=5)
        fits = self.evaluate_population(pop, self.types, self.pw, self.ph, self.facing)
        self.assertTrue(self.np.all(fits >= 0.0))
        self.assertTrue(self.np.all(fits <= 1.0))

    def test_population_fitness_variance(self):
        """Fitness scores should not all be identical (variance > 0)"""
        pop  = self.init_pop(30, self.types, self.pw, self.ph, seed=7)
        fits = self.evaluate_population(pop, self.types, self.pw, self.ph, self.facing)
        self.assertGreater(float(self.np.std(fits)), 0.0,
                           "All chromosomes have identical fitness — no learning signal")


# ════════════════════════════════════════════════════════════════
#  TEST GROUP 4 — selection.py
# ════════════════════════════════════════════════════════════════

class TestSelection(unittest.TestCase):
    """Tests for ga_engine/selection.py"""

    def setUp(self):
        import numpy as np
        from ga_engine.population import initialise_population
        from ga_engine.fitness import evaluate_population
        from ga_engine.selection import (
            tournament_select, elitism_indices, rank_population, select_parents
        )
        self.np               = np
        self.tournament_select= tournament_select
        self.elitism_indices  = elitism_indices
        self.rank_population  = rank_population
        self.select_parents   = select_parents

        types = ["entrance","living","kitchen","master_bedroom",
                 "bedroom","bathroom","balcony","pooja","store"]
        pop   = initialise_population(30, types, 40.0, 60.0, seed=11)
        fits  = evaluate_population(pop, types, 40.0, 60.0, "East")
        self.pop   = pop
        self.fits  = fits
        self.chrom_len = pop.shape[1]
        self.rng   = np.random.default_rng(77)

    def test_tournament_select_shape(self):
        """Selected chromosome has correct length"""
        sel = self.tournament_select(self.pop, self.fits, self.rng)
        self.assertEqual(sel.shape, (self.chrom_len,))

    def test_tournament_select_from_population(self):
        """Selected chromosome is one of the population members"""
        for _ in range(10):
            sel = self.tournament_select(self.pop, self.fits, self.rng)
            match = any(self.np.array_equal(sel, self.pop[i])
                        for i in range(len(self.pop)))
            self.assertTrue(match, "Selected chromosome not found in population")

    def test_tournament_selection_bias(self):
        """Tournament selection tends to pick higher-fitness individuals"""
        wins = {i: 0 for i in range(len(self.pop))}
        for _ in range(200):
            sel = self.tournament_select(self.pop, self.fits, self.rng)
            for i, chrom in enumerate(self.pop):
                if self.np.array_equal(sel, chrom):
                    wins[i] += 1
                    break
        # Top 5 by fitness should collectively win > 30% of selections
        top5 = self.np.argsort(self.fits)[::-1][:5]
        top5_wins = sum(wins[i] for i in top5)
        self.assertGreater(top5_wins / 200, 0.30,
                           f"Top 5 won only {top5_wins}/200 — selection not fitness-biased")

    def test_elitism_count(self):
        """elitism_indices returns exactly the requested count"""
        for k in [1, 2, 3, 5]:
            idx = self.elitism_indices(self.fits, k)
            self.assertEqual(len(idx), k)

    def test_elitism_sorted(self):
        """Elites are sorted best → worst"""
        idx = self.elitism_indices(self.fits, 5)
        for i in range(len(idx) - 1):
            self.assertGreaterEqual(self.fits[idx[i]], self.fits[idx[i+1]])

    def test_rank_population_order(self):
        """rank_population returns descending fitness order"""
        rp, rf = self.rank_population(self.pop, self.fits)
        for i in range(len(rf) - 1):
            self.assertGreaterEqual(rf[i], rf[i+1])

    def test_rank_population_preserves_values(self):
        """rank_population doesn't change fitness values, only order"""
        _, rf = self.rank_population(self.pop, self.fits)
        self.assertAlmostEqual(float(self.np.sum(rf)), float(self.np.sum(self.fits)), places=4)

    def test_select_parents_returns_two(self):
        """select_parents returns exactly two chromosomes"""
        p1, p2 = self.select_parents(self.pop, self.fits, self.rng)
        self.assertEqual(p1.shape, (self.chrom_len,))
        self.assertEqual(p2.shape, (self.chrom_len,))


# ════════════════════════════════════════════════════════════════
#  TEST GROUP 5 — operators.py
# ════════════════════════════════════════════════════════════════

class TestOperators(unittest.TestCase):
    """Tests for ga_engine/operators.py — crossover & mutation"""

    def setUp(self):
        import numpy as np
        from ga_engine.population import initialise_population
        from ga_engine.selection import rank_population
        from ga_engine.fitness import evaluate_population
        from ga_engine.operators import (
            crossover, mutate,
            uniform_crossover, single_point_crossover, arithmetic_crossover,
            gaussian_mutation, room_shift_mutation, room_resize_mutation, room_swap_mutation,
        )
        self.np                   = np
        self.crossover            = crossover
        self.mutate               = mutate
        self.uniform_crossover    = uniform_crossover
        self.sp_crossover         = single_point_crossover
        self.arith_crossover      = arithmetic_crossover
        self.gaussian_mutation    = gaussian_mutation
        self.shift_mutation       = room_shift_mutation
        self.resize_mutation      = room_resize_mutation
        self.swap_mutation        = room_swap_mutation

        types = ["entrance","living","dining","kitchen","master_bedroom",
                 "bedroom","bathroom","toilet","balcony","pooja","store"]
        pop   = initialise_population(20, types, 40.0, 60.0, seed=33)
        fits  = evaluate_population(pop, types, 40.0, 60.0, "North")
        rp, _ = rank_population(pop, fits)
        self.p1  = rp[0].copy()
        self.p2  = rp[1].copy()
        self.rng = np.random.default_rng(123)
        self.chrom_len = len(self.p1)

    # ── crossover tests ──────────────────────────────────────────

    def _test_crossover_fn(self, fn, name):
        for _ in range(10):
            c1, c2 = fn(self.p1, self.p2, self.rng, crossover_rate=1.0)
            self.assertEqual(c1.shape, (self.chrom_len,), f"{name} c1 shape wrong")
            self.assertEqual(c2.shape, (self.chrom_len,), f"{name} c2 shape wrong")
            self.assertTrue(self.np.all(c1 >= 0) and self.np.all(c1 <= 1),
                            f"{name} c1 out of [0,1]")
            self.assertTrue(self.np.all(c2 >= 0) and self.np.all(c2 <= 1),
                            f"{name} c2 out of [0,1]")

    def test_uniform_crossover_shape_range(self):
        self._test_crossover_fn(self.uniform_crossover, "uniform_crossover")

    def test_single_point_crossover_shape_range(self):
        self._test_crossover_fn(self.sp_crossover, "single_point_crossover")

    def test_arithmetic_crossover_shape_range(self):
        self._test_crossover_fn(self.arith_crossover, "arithmetic_crossover")

    def test_crossover_produces_different_child(self):
        """crossover() child is different from parent (guaranteed by module)"""
        for _ in range(20):
            c1, c2 = self.crossover(self.p1, self.p2, self.rng)
            self.assertFalse(self.np.array_equal(c1, self.p1),
                             "c1 identical to p1 — diversity guarantee failed")

    def test_crossover_rate_zero_returns_copies(self):
        """crossover_rate=0 should return copies of parents"""
        c1, c2 = self.uniform_crossover(self.p1, self.p2, self.rng, crossover_rate=0.0)
        self.assertTrue(self.np.array_equal(c1, self.p1), "rate=0 should return p1 copy")
        self.assertTrue(self.np.array_equal(c2, self.p2), "rate=0 should return p2 copy")

    # ── mutation tests ───────────────────────────────────────────

    def _test_mutation_fn(self, fn, name, rate=1.0):
        c = self.p1.copy()
        for _ in range(10):
            m = fn(c, self.rng, mutation_rate=rate)
            self.assertEqual(m.shape, c.shape, f"{name} shape wrong")
            self.assertTrue(self.np.all(m >= 0) and self.np.all(m <= 1),
                            f"{name} out of [0,1]")

    def test_gaussian_mutation_shape_range(self):
        self._test_mutation_fn(self.gaussian_mutation, "gaussian_mutation")

    def test_shift_mutation_shape_range(self):
        self._test_mutation_fn(self.shift_mutation, "room_shift_mutation")

    def test_resize_mutation_shape_range(self):
        self._test_mutation_fn(self.resize_mutation, "room_resize_mutation")

    def test_swap_mutation_shape_range(self):
        self._test_mutation_fn(self.swap_mutation, "room_swap_mutation")

    def test_mutation_rate_zero_no_change(self):
        """mutation_rate=0 should return an unchanged chromosome"""
        c = self.p1.copy()
        m = self.gaussian_mutation(c, self.rng, mutation_rate=0.0)
        self.assertTrue(self.np.array_equal(c, m), "rate=0 mutation changed chromosome")

    def test_mutate_composite(self):
        """mutate() composite operator stays in [0,1]"""
        for _ in range(20):
            m = self.mutate(self.p1, self.rng, mutation_rate=0.5)
            self.assertEqual(m.shape, self.p1.shape)
            self.assertTrue(self.np.all(m >= 0) and self.np.all(m <= 1))

    def test_mutation_changes_chromosome(self):
        """High mutation rate should change at least one gene"""
        changed = False
        for _ in range(30):
            m = self.gaussian_mutation(self.p1, self.rng, mutation_rate=1.0, sigma=0.1)
            if not self.np.array_equal(self.p1, m):
                changed = True
                break
        self.assertTrue(changed, "Gaussian mutation at rate=1.0 never changed any gene")


# ════════════════════════════════════════════════════════════════
#  TEST GROUP 6 — ga_runner.py
# ════════════════════════════════════════════════════════════════

class TestGARunner(unittest.TestCase):
    """End-to-end tests for ga_engine/ga_runner.py — run_ga()"""

    def setUp(self):
        from ga_engine.ga_runner import run_ga
        self.run_ga = run_ga

    def _run(self, **kwargs):
        defaults = dict(
            plot_w=40.0, plot_h=60.0, bhk_type="2BHK",
            facing="East", pop_size=20, max_generations=10,
            top_n=3, seed=0,
        )
        defaults.update(kwargs)
        return self.run_ga(**defaults)

    # ── return value structure ───────────────────────────────────

    def test_returns_list(self):
        layouts = self._run()
        self.assertIsInstance(layouts, list)

    def test_returns_correct_count(self):
        layouts = self._run(top_n=3)
        self.assertLessEqual(len(layouts), 3)
        self.assertGreaterEqual(len(layouts), 1)

    def test_layout_attributes(self):
        """Each returned Layout has all required attributes"""
        for layout in self._run(top_n=2):
            self.assertIsInstance(layout.fitness,     float)
            self.assertIsInstance(layout.vastu_score, float)
            self.assertIsInstance(layout.space_util,  float)
            self.assertIsInstance(layout.rooms,       list)
            self.assertIsInstance(layout.vastu_rules, list)
            self.assertIsInstance(layout.layout_id,   str)

    def test_layout_score_ranges(self):
        """Layout scores are in valid ranges"""
        for lay in self._run(top_n=2):
            self.assertGreaterEqual(lay.fitness,     0.0)
            self.assertLessEqual(lay.fitness,        1.0)
            self.assertGreaterEqual(lay.vastu_score, 0.0)
            self.assertLessEqual(lay.vastu_score,   100.0)
            self.assertGreaterEqual(lay.space_util,  0.0)
            self.assertLessEqual(lay.space_util,    100.0)

    def test_rooms_not_empty(self):
        """Each layout has at least one room"""
        for lay in self._run(top_n=2):
            self.assertGreater(len(lay.rooms), 0)

    def test_sorted_descending_fitness(self):
        """Returned layouts are sorted best → worst"""
        layouts = self._run(top_n=3)
        for i in range(len(layouts) - 1):
            self.assertGreaterEqual(layouts[i].fitness, layouts[i+1].fitness,
                                    "Layouts not sorted descending by fitness")

    def test_to_dict_schema(self):
        """Layout.to_dict() matches the exact frontend JSON schema"""
        d = self._run(top_n=1)[0].to_dict()
        # Top-level keys
        for key in ("layout_id","rooms","vastu_score","fitness","space_util",
                    "total_room_area","vastu_rules","plot"):
            self.assertIn(key, d, f"to_dict missing key: {key}")
        # Room keys
        for r in d["rooms"]:
            for k in ("type","label","x","y","w","h","width","height","area"):
                self.assertIn(k, r, f"room dict missing key: {k}")
        # Plot keys
        for k in ("width","height","facing","bhk_type","usable_area"):
            self.assertIn(k, d["plot"], f"plot dict missing key: {k}")
        # Vastu rule keys
        for v in d["vastu_rules"]:
            for k in ("label","status","weight","earned","description"):
                self.assertIn(k, v, f"vastu_rule missing key: {k}")

    def test_reproducibility(self):
        """Same seed produces identical fitness and room count"""
        l1 = self._run(seed=42)
        l2 = self._run(seed=42)
        # layout_id is a random UUID generated after GA, so it differs each run;
        # reproducibility is validated by identical fitness and vastu scores
        self.assertAlmostEqual(l1[0].fitness,     l2[0].fitness,     places=5,
                               msg="fitness not reproducible with same seed")
        self.assertAlmostEqual(l1[0].vastu_score, l2[0].vastu_score, places=2,
                               msg="vastu_score not reproducible with same seed")
        self.assertEqual(len(l1[0].rooms), len(l2[0].rooms),
                         msg="room count not reproducible with same seed")

    def test_all_bhk_types(self):
        """run_ga works for 1BHK, 2BHK, 3BHK, 4BHK"""
        for bhk in ("1BHK", "2BHK", "3BHK", "4BHK"):
            layouts = self._run(bhk_type=bhk, top_n=1)
            self.assertGreater(len(layouts), 0, f"{bhk} returned no layouts")
            self.assertGreater(len(layouts[0].rooms), 0, f"{bhk} layout has no rooms")

    def test_all_facing_directions(self):
        """run_ga works for all 4 facing directions"""
        for facing in ("North", "East", "South", "West"):
            layouts = self._run(facing=facing, top_n=1)
            self.assertGreater(len(layouts), 0, f"{facing}: no layouts returned")
            self.assertEqual(layouts[0].facing, facing)

    def test_improvement_over_generations(self):
        """More generations produces better or equal fitness"""
        short  = self._run(max_generations=5,  pop_size=30, top_n=1, seed=7)[0].fitness
        longer = self._run(max_generations=30, pop_size=30, top_n=1, seed=7)[0].fitness
        self.assertGreaterEqual(longer, short - 0.02,
                                f"More generations degraded fitness: {short:.4f} → {longer:.4f}")

    def test_custom_plot_sizes(self):
        """Works with non-standard plot dimensions"""
        for pw, ph in [(20.0, 40.0), (30.0, 30.0), (60.0, 80.0), (50.0, 50.0)]:
            layouts = self._run(plot_w=pw, plot_h=ph, top_n=1)
            self.assertGreater(len(layouts), 0, f"{pw}×{ph}: no layouts returned")
            lay = layouts[0]
            self.assertEqual(lay.plot_width,  pw)
            self.assertEqual(lay.plot_height, ph)
            # All rooms within plot
            for r in lay.rooms:
                self.assertLessEqual(r.right,  pw + 0.01, f"Room exceeds plot width")
                self.assertLessEqual(r.bottom, ph + 0.01, f"Room exceeds plot height")

    def test_performance_benchmark(self):
        """Full GA (pop=60, gen=50) completes in reasonable time"""
        t0 = time.perf_counter()
        self.run_ga(40.0, 60.0, "2BHK", "East",
                    pop_size=60, max_generations=50, top_n=3, seed=1)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 60.0,
                        f"GA took {elapsed:.1f}s — exceeds 60s limit")
        print(f"\n    ⏱  Full GA (pop=60, gen=50): {elapsed*1000:.0f}ms")


# ════════════════════════════════════════════════════════════════
#  CUSTOM TEST RUNNER  (no pytest needed)
# ════════════════════════════════════════════════════════════════

class ColourResult(unittest.TestResult):
    """Pretty-printing test result collector."""

    def __init__(self, verbose=False):
        super().__init__()
        self.verbose    = verbose
        self.passed     = []
        self.group_times = {}
        self._t0        = {}

    def startTest(self, test):
        super().startTest(test)
        self._t0[test] = time.perf_counter()

    def addSuccess(self, test):
        super().addSuccess(test)
        elapsed = (time.perf_counter() - self._t0[test]) * 1000
        self.passed.append((test, elapsed))
        if self.verbose:
            name = f"{type(test).__name__}.{test._testMethodName}"
            print(f"  {ok(name)}  {C_DIM}({elapsed:.1f}ms){C_RESET}")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        elapsed = (time.perf_counter() - self._t0[test]) * 1000
        name = f"{type(test).__name__}.{test._testMethodName}"
        print(f"  {fail(name)}  {C_DIM}({elapsed:.1f}ms){C_RESET}")
        # Print compact traceback
        tb = traceback.format_exception(*err)
        for line in tb[-3:]:
            print(f"    {C_RED}{line.rstrip()}{C_RESET}")

    def addError(self, test, err):
        super().addError(test, err)
        elapsed = (time.perf_counter() - self._t0[test]) * 1000
        name = f"{type(test).__name__}.{test._testMethodName}"
        print(f"  {warn(f'ERROR: {name}')}  {C_DIM}({elapsed:.1f}ms){C_RESET}")
        tb = traceback.format_exception(*err)
        for line in tb[-3:]:
            print(f"    {C_YELLOW}{line.rstrip()}{C_RESET}")


def run_tests(groups=None, verbose=False):
    """Run all test groups (or a filtered subset) and print a summary."""

    ALL_GROUPS = {
        "chromosome": TestChromosome,
        "population": TestPopulation,
        "fitness":    TestFitness,
        "selection":  TestSelection,
        "operators":  TestOperators,
        "runner":     TestGARunner,
    }

    if groups:
        unknown = set(groups) - set(ALL_GROUPS)
        if unknown:
            print(f"{C_RED}Unknown test groups: {unknown}{C_RESET}")
            print(f"Available: {sorted(ALL_GROUPS)}")
            sys.exit(1)
        selected = {k: v for k, v in ALL_GROUPS.items() if k in groups}
    else:
        selected = ALL_GROUPS

    # ── Header ───────────────────────────────────────────────────
    print()
    print(f"{C_BOLD}{'═'*62}{C_RESET}")
    print(f"{C_BOLD}  IntelliPlan·3D  —  GA ENGINE TEST SUITE{C_RESET}")
    print(f"{C_BOLD}{'═'*62}{C_RESET}")
    print(f"  Running {len(selected)} group(s): "
          f"{C_CYAN}{', '.join(selected)}{C_RESET}")
    print()

    total_passed = total_failed = total_errors = 0
    t_global = time.perf_counter()

    for group_name, test_class in selected.items():
        suite  = unittest.TestLoader().loadTestsFromTestCase(test_class)
        result = ColourResult(verbose=verbose)
        t0     = time.perf_counter()

        print(f"{C_BOLD}  [{group_name.upper()}]{C_RESET}  "
              f"{C_DIM}{test_class.__name__}{C_RESET}")

        # Suppress logger noise during tests
        import logging
        logging.disable(logging.CRITICAL)
        suite.run(result)
        logging.disable(logging.NOTSET)

        elapsed = (time.perf_counter() - t0) * 1000
        n_run    = result.testsRun
        n_fail   = len(result.failures)
        n_err    = len(result.errors)
        n_pass   = n_run - n_fail - n_err

        total_passed += n_pass
        total_failed += n_fail
        total_errors += n_err

        status = (
            f"{C_GREEN}PASS{C_RESET}" if (n_fail + n_err == 0)
            else f"{C_RED}FAIL{C_RESET}"
        )

        if not verbose:
            # Summary line per group
            bar = _progress_bar(n_pass, n_run)
            print(f"  {bar}  {n_pass}/{n_run} passed  "
                  f"{C_DIM}({elapsed:.0f}ms){C_RESET}  {status}")
            # Show failures even in non-verbose
            for test, err in result.failures + result.errors:
                name = test._testMethodName
                tb   = traceback.format_exception(*err)
                print(f"  {fail(name)}")
                for line in tb[-2:]:
                    print(f"    {C_RED}{line.rstrip()}{C_RESET}")
        else:
            print(f"  {'─'*50}  {n_pass}/{n_run} passed  "
                  f"{C_DIM}({elapsed:.0f}ms){C_RESET}  {status}")
        print()

    # ── Summary ──────────────────────────────────────────────────
    elapsed_total = (time.perf_counter() - t_global) * 1000
    total_run = total_passed + total_failed + total_errors

    print(f"{C_BOLD}{'═'*62}{C_RESET}")
    if total_failed + total_errors == 0:
        print(f"  {C_GREEN}{C_BOLD}ALL {total_run} TESTS PASSED ✓{C_RESET}  "
              f"{C_DIM}({elapsed_total:.0f}ms total){C_RESET}")
    else:
        print(f"  {C_RED}{C_BOLD}{total_failed + total_errors} FAILED / "
              f"{total_run} total{C_RESET}  "
              f"{C_DIM}({elapsed_total:.0f}ms total){C_RESET}")
    print(f"{C_BOLD}{'═'*62}{C_RESET}")
    print()

    return total_failed + total_errors == 0


def _progress_bar(passed, total, width=20):
    if total == 0:
        return " " * width
    filled = int(width * passed / total)
    bar = "█" * filled + "░" * (width - filled)
    color = C_GREEN if passed == total else C_RED
    return f"{color}{bar}{C_RESET}"


# ── CLI entry point ──────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="IntelliPlan·3D GA Engine Test Suite"
    )
    parser.add_argument(
        "-t", "--test", nargs="+",
        choices=["chromosome","population","fitness","selection","operators","runner"],
        help="Run only specific test group(s)",
        metavar="GROUP",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="Print each test case individually",
    )
    args = parser.parse_args()

    success = run_tests(groups=args.test, verbose=args.verbose)
    sys.exit(0 if success else 1)
