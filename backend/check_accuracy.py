"""
╔══════════════════════════════════════════════════════════════════╗
║      IntelliPlan·3D — FULL BACKEND ACCURACY CHECK               ║
║                                                                  ║
║  Runs ALL test suites + model quality evaluation together.       ║
║                                                                  ║
║  Usage:                                                          ║
║    python check_accuracy.py             # full check             ║
║    python check_accuracy.py --quick     # quick check (faster)   ║
║    python check_accuracy.py --verbose   # show every test case   ║
╚══════════════════════════════════════════════════════════════════╝
"""

import sys, os, time, argparse, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logging.disable(logging.CRITICAL)   # silence GA logs during tests

import numpy as np

# ── Colours ─────────────────────────────────────────────────────
B  = "\033[1m";   X  = "\033[0m"
G  = "\033[92m";  R  = "\033[91m"
Y  = "\033[93m";  C  = "\033[96m"
D  = "\033[2m"

def _bar(passed, total, width=20):
    if total == 0: return " " * width
    f   = int(width * passed / total)
    col = G if passed == total else (Y if passed >= total * 0.8 else R)
    return f"{col}{'█'*f}{'░'*(width-f)}{X}"

def _score_bar(val, lo=0, hi=100, width=20):
    f   = int(max(0, min(1, (val-lo)/(hi-lo) if hi>lo else 1)) * width)
    col = G if val >= hi*0.80 else (Y if val >= hi*0.55 else R)
    return f"{col}{'█'*f}{'░'*(width-f)}{X}"


# ════════════════════════════════════════════════════════════════
#  SECTION 1 — Unit Tests  (test_*.py)
# ════════════════════════════════════════════════════════════════

def run_unit_tests(verbose: bool) -> dict:
    """Run all 3 test suites and return combined results."""

    import importlib.util

    suites = [
        ("GA Engine",      "test_ga_engine.py"),
        ("Vastu Engine",   "test_vastu_engine.py"),
        ("Geometry",       "test_geometry.py"),
    ]

    results = {}
    for suite_name, fname in suites:
        spec   = importlib.util.spec_from_file_location("_suite", fname)
        mod    = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        t0     = time.perf_counter()
        passed = mod.run_tests(groups=None, verbose=verbose)
        elapsed = (time.perf_counter() - t0) * 1000
        results[suite_name] = {"passed": passed, "elapsed_ms": elapsed}

    return results


# ════════════════════════════════════════════════════════════════
#  SECTION 2 — Module Accuracy  (per module)
# ════════════════════════════════════════════════════════════════

def check_module_accuracy() -> dict:
    """
    Test each backend module directly and return accuracy metrics.
    Returns pass/fail + accuracy % for each module.
    """
    from ga_engine.layout_generator import generate_layout
    from ga_engine.ga_runner        import run_ga
    from vastu_engine.vastu_score   import compute_vastu_score
    from geometry.overlap           import total_overlap_area
    from geometry.validation        import space_utilisation, room_meets_min_size
    from utils.helpers              import parse_plot_size, validate_bhk, validate_facing
    from services.layout_service    import LayoutService

    results = {}

    # ── 1. layout_generator — zero overlap guarantee ─────────────
    print(f"  {D}Checking layout_generator (200 layouts)...{X}")
    total = 0; passed = 0
    for seed in range(50):
        for bhk in ("1BHK","2BHK","3BHK","4BHK"):
            lay = generate_layout(50., 80., bhk, "North",
                                  rng=np.random.default_rng(seed))
            ov  = total_overlap_area(lay.rooms)
            oob = sum(1 for r in lay.rooms
                      if r.x<-0.01 or r.y<-0.01
                      or r.right>50.01 or r.bottom>80.01)
            total += 1
            if ov < 0.01 and oob == 0:
                passed += 1
    results["Layout Generator"] = {
        "label":    "Zero overlap & in-bounds",
        "accuracy": passed / total * 100,
        "passed":   passed,
        "total":    total,
    }

    # ── 2. vastu_engine — score correctness ──────────────────────
    print(f"  {D}Checking vastu_engine (all 4 facings, ideal layouts)...{X}")
    from geometry.room import Room
    def _room(t,x,y,w,h): return Room(type=t,x=x,y=y,width=w,height=h)

    tests = [
        # (rooms, facing, expected_min_score)
        ([_room("kitchen",28,42,10,12), _room("pooja",28,0,8,8),
          _room("master_bedroom",0,42,14,14), _room("living",8,0,18,14),
          _room("bathroom",0,0,7,8), _room("entrance",14,0,9,4)],
         "North", 50),
        ([_room("kitchen",0,42,10,12), _room("pooja",0,0,8,8),
          _room("master_bedroom",28,42,14,14), _room("living",0,0,18,14),
          _room("bathroom",28,0,7,8)],
         "North", 0),   # wrong zones → low score
    ]
    total=0; passed=0
    for rooms, facing, min_score in tests:
        score, _ = compute_vastu_score(rooms, 40., 60., facing)
        total += 1
        if (min_score > 0 and score >= min_score) or \
           (min_score == 0 and score < 50):
            passed += 1
    # Test all 4 facings don't crash
    for facing in ("North","East","South","West"):
        for bhk in ("1BHK","2BHK","3BHK","4BHK"):
            lay = generate_layout(40.,60.,bhk,facing,rng=np.random.default_rng(0))
            score,rules = compute_vastu_score(lay.rooms,40.,60.,facing)
            total += 1
            if 0 <= score <= 100 and len(rules) > 0:
                passed += 1
    results["Vastu Engine"] = {
        "label":    "Score range + rule correctness",
        "accuracy": passed / total * 100,
        "passed":   passed,
        "total":    total,
    }

    # ── 3. fitness function — output validity ─────────────────────
    print(f"  {D}Checking fitness function (80 layouts)...{X}")
    from ga_engine.fitness import evaluate_fitness
    total=0; passed=0
    for seed in range(20):
        for bhk in ("1BHK","2BHK","3BHK","4BHK"):
            lay = generate_layout(40.,60.,bhk,"East",rng=np.random.default_rng(seed))
            fit,vastu,util,rules = evaluate_fitness(lay.rooms,40.,60.,"East")
            total += 1
            if (0 <= fit <= 1 and 0 <= vastu <= 100
                    and 0 <= util <= 100 and len(rules) > 0):
                passed += 1
    results["Fitness Function"] = {
        "label":    "Output in valid range + has rules",
        "accuracy": passed / total * 100,
        "passed":   passed,
        "total":    total,
    }

    # ── 4. helpers — input validation ────────────────────────────
    print(f"  {D}Checking input validation (helpers)...{X}")
    total=0; passed=0
    good = [("40x60",(40.,60.)), ("30x45",(30.,45.)), ("100x80",(100.,80.))]
    bad  = ["bad","40","x60","-1x60","0x0",""]
    for s,(ew,eh) in good:
        total+=1
        try:
            w,h = parse_plot_size(s)
            if abs(w-ew)<0.01 and abs(h-eh)<0.01: passed+=1
        except: pass
    for s in bad:
        total+=1
        try: parse_plot_size(s)
        except ValueError: passed+=1

    for v in ("2BHK","1bhk","3BHK","4BHK"):
        total+=1
        try:
            r=validate_bhk(v)
            if r in ("1BHK","2BHK","3BHK","4BHK"): passed+=1
        except: pass
    for bad_bhk in ("5BHK","0BHK","studio"):
        total+=1
        try: validate_bhk(bad_bhk)
        except ValueError: passed+=1

    for v in ("North","east","SOUTH","West"):
        total+=1
        try:
            r=validate_facing(v)
            if r in ("North","East","South","West"): passed+=1
        except: pass
    results["Input Validation"] = {
        "label":    "Correct parsing + error handling",
        "accuracy": passed / total * 100,
        "passed":   passed,
        "total":    total,
    }

    # ── 5. room min-size compliance ───────────────────────────────
    print(f"  {D}Checking room min-size compliance (160 layouts)...{X}")
    total=0; passed=0
    for seed in range(20):
        for bhk in ("1BHK","2BHK","3BHK","4BHK"):
            for pw,ph in [(40,60),(50,80)]:
                lay = generate_layout(float(pw),float(ph),bhk,"North",
                                      rng=np.random.default_rng(seed))
                for r in lay.rooms:
                    total += 1
                    if room_meets_min_size(r):
                        passed += 1
    results["Min-Size Compliance"] = {
        "label":    "Every room ≥ minimum dimensions",
        "accuracy": passed / total * 100,
        "passed":   passed,
        "total":    total,
    }

    # ── 6. API service layer ──────────────────────────────────────
    print(f"  {D}Checking API service layer (all BHK × facing)...{X}")
    svc = LayoutService()
    total=0; passed=0
    for bhk in ("1BHK","2BHK","3BHK","4BHK"):
        for facing in ("North","East","South","West"):
            total += 1
            r = svc.generate("40x60",bhk,facing,pop_size=10,max_generations=5,top_n=1)
            if r.success and r.count >= 1:
                d = r.to_dict()
                if all(k in d for k in ("success","count","layouts","elapsed_ms")):
                    if all(k in d["layouts"][0]
                           for k in ("layout_id","rooms","vastu_score","plot")):
                        passed += 1
    # Test bad inputs return errors cleanly
    for bad in [("bad","2BHK","East"),("40x60","5BHK","East"),("40x60","2BHK","Up")]:
        total += 1
        r = svc.generate(*bad)
        if not r.success and r.error: passed += 1

    results["API Service Layer"] = {
        "label":    "Generate + validate JSON schema",
        "accuracy": passed / total * 100,
        "passed":   passed,
        "total":    total,
    }

    return results


# ════════════════════════════════════════════════════════════════
#  SECTION 3 — GA Model Quality
# ════════════════════════════════════════════════════════════════

def check_ga_quality(quick: bool) -> dict:
    """Run GA on real plot configurations and measure output quality."""
    from ga_engine.ga_runner import run_ga
    from geometry.overlap    import total_overlap_area
    from geometry.validation import space_utilisation

    combos = (
        [(40,60,"2BHK","North"), (50,80,"3BHK","East"), (30,45,"1BHK","South")]
        if quick else
        [(40,60,"1BHK","North"),(40,60,"2BHK","North"),(40,60,"3BHK","East"),
         (50,80,"2BHK","East"),(50,80,"3BHK","North"),(30,45,"1BHK","South"),
         (60,60,"4BHK","West"),(40,80,"2BHK","South")]
    )
    pop = 30 if quick else 50
    gen = 20 if quick else 35

    print(f"  {D}Running GA quality check ({len(combos)} configurations)...{X}")

    vastu_scores=[]; fitness_scores=[]; util_scores=[]
    overlap_list=[]; n_total=0; n_zero_ov=0

    for pw,ph,bhk,facing in combos:
        layouts = run_ga(float(pw),float(ph),bhk,facing,
                         pop_size=pop,max_generations=gen,top_n=3,seed=1)
        for lay in layouts:
            n_total += 1
            ov = total_overlap_area(lay.rooms)
            overlap_list.append(ov)
            vastu_scores.append(lay.vastu_score)
            fitness_scores.append(lay.fitness)
            util_scores.append(lay.space_util)
            if ov < 0.01:
                n_zero_ov += 1

    return {
        "avg_vastu":      float(np.mean(vastu_scores)),
        "avg_fitness":    float(np.mean(fitness_scores)),
        "avg_util":       float(np.mean(util_scores)),
        "zero_ov_pct":    n_zero_ov / n_total * 100,
        "n_layouts":      n_total,
        "n_zero_overlap": n_zero_ov,
    }


# ════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════

def main(quick: bool, verbose: bool):
    t_global = time.perf_counter()

    print(f"\n{B}{'═'*64}{X}")
    print(f"{B}  IntelliPlan·3D — FULL BACKEND ACCURACY CHECK{X}")
    print(f"{B}{'═'*64}{X}")
    print(f"  Mode: {'QUICK' if quick else 'FULL'}\n")

    total_score = 0.0

    # ════════════════════════════════════════════════════════════
    #  SECTION 1 — Unit Tests
    # ════════════════════════════════════════════════════════════
    print(f"\n{B}  ┌─────────────────────────────────────────────┐{X}")
    print(f"{B}  │  SECTION 1 — Unit Tests (181 total)          │{X}")
    print(f"{B}  └─────────────────────────────────────────────┘{X}\n")

    unit_results = run_unit_tests(verbose)

    unit_pass = sum(1 for r in unit_results.values() if r["passed"])
    unit_total = len(unit_results)

    # The run_tests() functions print their own output — just show summary
    print(f"\n  Unit test suites: {unit_pass}/{unit_total} passed")
    for name, r in unit_results.items():
        status = f"{G}✓ PASS{X}" if r["passed"] else f"{R}✗ FAIL{X}"
        print(f"  {_bar(1 if r['passed'] else 0, 1)}  {name:20s}  {status}  "
              f"{D}({r['elapsed_ms']:.0f}ms){X}")

    unit_score = unit_pass / unit_total * 100
    total_score += unit_score * 0.30   # 30% weight

    # ════════════════════════════════════════════════════════════
    #  SECTION 2 — Module Accuracy
    # ════════════════════════════════════════════════════════════
    print(f"\n{B}  ┌─────────────────────────────────────────────┐{X}")
    print(f"{B}  │  SECTION 2 — Module Accuracy                 │{X}")
    print(f"{B}  └─────────────────────────────────────────────┘{X}\n")

    mod_results = check_module_accuracy()

    print(f"\n  {'Module':25s}  {'Accuracy Bar':22s}  {'Score':>7}  {'Tests':>10}")
    print(f"  {'─'*25}  {'─'*22}  {'─'*7}  {'─'*10}")

    mod_avg = 0.0
    for name, r in mod_results.items():
        col = G if r["accuracy"]>=90 else (Y if r["accuracy"]>=70 else R)
        print(f"  {name:25s}  {_score_bar(r['accuracy'],50,100)}  "
              f"  {col}{r['accuracy']:5.1f}%{X}  "
              f"{D}{r['passed']}/{r['total']}{X}")
        mod_avg += r["accuracy"]
    mod_avg /= len(mod_results)

    total_score += mod_avg * 0.40   # 40% weight

    # ════════════════════════════════════════════════════════════
    #  SECTION 3 — GA Model Quality
    # ════════════════════════════════════════════════════════════
    print(f"\n{B}  ┌─────────────────────────────────────────────┐{X}")
    print(f"{B}  │  SECTION 3 — GA Model Quality                │{X}")
    print(f"{B}  └─────────────────────────────────────────────┘{X}\n")

    qa = check_ga_quality(quick)

    metrics = [
        ("Vastu Compliance",   qa["avg_vastu"],          0,  100, "%",  60),
        ("Fitness Score",      qa["avg_fitness"]*100,    50, 100, "",   80),
        ("Space Utilisation",  qa["avg_util"],           55,  90, "%",  68),
        ("Zero Overlap Rate",  qa["zero_ov_pct"],        80, 100, "%", 100),
    ]

    print(f"\n  {'Metric':24s}  {'Quality Bar':22s}  {'Value':>8}  {'Target':>7}")
    print(f"  {'─'*24}  {'─'*22}  {'─'*8}  {'─'*7}")

    qa_score = 0.0
    weights  = [0.35, 0.25, 0.15, 0.25]
    for (name, val, lo, hi, unit, target), w in zip(metrics, weights):
        display = val/100 if unit=="" else val
        col = G if val>=target else (Y if val>=target*0.75 else R)
        print(f"  {name:24s}  {_score_bar(val,lo,hi)}  "
              f"  {col}{display:6.1f}{unit}{X}  "
              f"{D}≥{target/100 if unit=='' else target}{unit}{X}")
        qa_score += min(val/target, 1.0) * w * 100

    print(f"\n  {D}Evaluated on {qa['n_layouts']} layouts "
          f"({qa['n_zero_overlap']}/{qa['n_layouts']} zero-overlap){X}")

    total_score += qa_score * 0.30   # 30% weight

    # ════════════════════════════════════════════════════════════
    #  FINAL REPORT
    # ════════════════════════════════════════════════════════════
    elapsed = time.perf_counter() - t_global
    grade = ("A+" if total_score>=92 else "A" if total_score>=85
             else "B+" if total_score>=78 else "B" if total_score>=70
             else "C" if total_score>=60 else "D")
    grade_col = G if total_score>=78 else (Y if total_score>=60 else R)

    print(f"\n{B}{'═'*64}{X}")
    print(f"{B}  FINAL ACCURACY REPORT{X}")
    print(f"{'─'*64}")

    comp = [
        ("Unit Tests (181 tests)", unit_score,  30),
        ("Module Accuracy",        mod_avg,     40),
        ("GA Model Quality",       qa_score,    30),
    ]
    for name, score, weight in comp:
        col = G if score>=80 else (Y if score>=60 else R)
        print(f"  {name:30s}  {_score_bar(score,0,100,16)}  "
              f"{col}{score:5.1f}%{X}  {D}(weight {weight}%){X}")

    print(f"{'─'*64}")
    print(f"  {B}Overall Accuracy:  {grade_col}{total_score:.1f}%  "
          f"[ Grade: {grade} ]{X}")
    print(f"  {D}Total time: {elapsed:.1f}s{X}")
    print(f"{B}{'═'*64}{X}\n")

    return total_score >= 60


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="IntelliPlan·3D — Full Backend Accuracy Check"
    )
    parser.add_argument("--quick",   action="store_true",
                        help="Quick check (fewer GA runs)")
    parser.add_argument("--verbose", action="store_true",
                        help="Show every individual test case")
    args = parser.parse_args()

    ok = main(quick=args.quick, verbose=args.verbose)
    sys.exit(0 if ok else 1)