"""Check 4: reproducibility of the TNFalpha RNG seeding fix.

Runs prism BM0 (drug_conc=1e-7, time_remove_o2=1 min, max_time=60 min, full
saves every 20 min) for: 1 thread x2 same seed, 4 threads x2 same seed, and
1 thread with a different seed; compares outputs with compare_runs.py and
writes check4_*.json. Uses the executable built from the current working tree
(physispatial_tools/run.py's build cache). Scratch outputs go to check4_runs/
(gitignored); remove that directory before re-running.
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from compare_runs import compare_runs  # noqa: E402
from scratch_run import make_scratch_run, run_mod  # noqa: E402

OUT = HERE / "check4_runs"
SPECS = {
    "1t_s42_a": (42, 1), "1t_s42_b": (42, 1),
    "4t_s42_a": (42, 4), "4t_s42_b": (42, 4),
    "1t_s99": (99, 1),
}


def go(item):
    name, (seed, threads) = item
    run = make_scratch_run("prism", "BM0", seed, threads, 60.0, name, str(OUT),
                            full_data_interval=20.0, time_remove_o2=1.0)
    run_mod.execute(run, jobs=2)
    return name, run


def main():
    run_mod.build("prism", "BM0", 2)  # build once, before parallel execute()
    with ThreadPoolExecutor(max_workers=5) as pool:
        runs = dict(pool.map(go, SPECS.items()))
    pairs = {
        "check4_1thread_sameseed.json": ("1t_s42_a", "1t_s42_b"),
        "check4_4thread_sameseed.json": ("4t_s42_a", "4t_s42_b"),
        "check4_1thread_diffseed.json": ("1t_s42_a", "1t_s99"),
    }
    for fname, (a, b) in pairs.items():
        result = compare_runs(runs[a], runs[b])
        (HERE / fname).write_text(json.dumps(result, indent=2))
        print(f"{fname}: {result['n_identical']}/{result['n_compared']} identical")


if __name__ == "__main__":
    main()
