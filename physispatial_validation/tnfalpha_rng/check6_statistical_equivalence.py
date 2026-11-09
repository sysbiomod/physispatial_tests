"""Check 6: statistical equivalence between main (pre-fix) and the TNFalpha RNG
seeding fix. Runs N single-thread replicates per arm with distinct seeds, at a
shortened horizon (user-approved shortening of the spec's 1000/2000/3000 min
readouts), and compares total live cells, live cell_type==0 ("BM0") cells, and
the fraction of live cells with the Apoptosis node active, at each readout time,
via a two-sample Kolmogorov-Smirnov test.

Does not touch the shipped PhysiCell_settings.xml; uses scratch_run.py's XML
overrides on a per-run copy only.
"""
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import scipy.io as sio
from scipy.stats import ks_2samp

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from scratch_run import make_scratch_run  # noqa: E402

DEAD_ROW = 26
CELL_TYPE_ROW = 5


def run_one(executable, label, seed, max_time, interval, output_root, threads=1):
    name = f"{label}_seed{seed}"
    run = make_scratch_run("prism", "BM0", seed, threads, max_time, name, output_root,
                            concentration=1e-7, full_data_interval=interval, time_remove_o2=1.0)
    shutil.copy2(executable, run / "physispatial_prism")
    t0 = time.monotonic()
    with (run / "sim.log").open("w") as log:
        result = subprocess.run([str(run / "physispatial_prism"), "config/run.xml"],
                                 cwd=run, env=dict(os.environ, OMP_NUM_THREADS=str(threads)),
                                 stdout=log, stderr=subprocess.STDOUT)
    wall = time.monotonic() - t0
    return run, result.returncode, wall


def extract_readout(run, t):
    # full_data saves are numbered sequentially from t=0; with interval `dt`
    # the save at simulated time t is index round(t/dt).
    manifest = json.loads((run / "run_manifest.json").read_text())
    dt = manifest["full_data_interval"]
    idx = round(t / dt)
    mat_path = run / "output" / f"output{idx:08d}_cells.mat"
    csv_path = run / "output" / f"output{idx:08d}_boolean_intracellular.csv"
    if not mat_path.is_file():
        return None
    cells = sio.loadmat(mat_path)["cells"]
    ids = cells[0, :].astype(int)
    dead = cells[DEAD_ROW, :]
    cell_type = cells[CELL_TYPE_ROW, :]
    alive_mask = dead == 0
    total_live = int(alive_mask.sum())
    live_type0 = int(((cell_type == 0) & alive_mask).sum())

    apoptosis_ids = set()
    if csv_path.is_file():
        with csv_path.open() as f:
            next(f)  # header
            for line in f:
                cid_str, state = line.rstrip("\n").split(",", 1)
                nodes = state.split(" -- ")
                if "Apoptosis" in nodes:
                    apoptosis_ids.add(int(cid_str))
    alive_ids = set(ids[alive_mask].tolist())
    apoptosis_live = len(apoptosis_ids & alive_ids)
    apoptosis_fraction = apoptosis_live / total_live if total_live > 0 else float("nan")

    return dict(total_live=total_live, live_type0=live_type0,
                apoptosis_fraction=apoptosis_fraction, n_apoptosis_live=apoptosis_live)


def main():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--main-exe", required=True)
    p.add_argument("--fixed-exe", required=True)
    p.add_argument("--n-replicates", type=int, default=20)
    p.add_argument("--max-time", type=float, default=300.0)
    p.add_argument("--interval", type=float, default=50.0)
    p.add_argument("--readout-times", default="100,200,300")
    p.add_argument("--output-root", default=str(ROOT / "physispatial_validation/tnfalpha_rng/check6_runs"))
    p.add_argument("--jobs", type=int, default=6)
    p.add_argument("--main-seed-base", type=int, default=1000)
    p.add_argument("--fixed-seed-base", type=int, default=2000)
    a = p.parse_args()

    readout_times = [float(x) for x in a.readout_times.split(",")]
    tasks = []
    for i in range(a.n_replicates):
        tasks.append(("main", a.main_exe, a.main_seed_base + i))
    for i in range(a.n_replicates):
        tasks.append(("fixed", a.fixed_exe, a.fixed_seed_base + i))

    from concurrent.futures import ThreadPoolExecutor, as_completed
    results = {}
    wall_times = []

    def worker(label, exe, seed):
        run, rc, wall = run_one(exe, label, seed, a.max_time, a.interval, a.output_root)
        return label, seed, run, rc, wall

    with ThreadPoolExecutor(max_workers=a.jobs) as pool:
        futures = [pool.submit(worker, *t) for t in tasks]
        for fut in as_completed(futures):
            label, seed, run, rc, wall = fut.result()
            print(f"done: {label} seed={seed} rc={rc} wall={wall:.1f}s", flush=True)
            results.setdefault(label, []).append(dict(seed=seed, run=str(run), returncode=rc, wall_seconds=wall))
            wall_times.append(wall)

    summary = dict(readout_times=readout_times, n_replicates=a.n_replicates,
                    max_time=a.max_time, interval=a.interval, runs=results, readouts={})

    for t in readout_times:
        summary["readouts"][str(t)] = {}
        for label in ("main", "fixed"):
            values = {"total_live": [], "live_type0": [], "apoptosis_fraction": []}
            for r in results[label]:
                readout = extract_readout(Path(r["run"]), t)
                if readout is None:
                    continue
                values["total_live"].append(readout["total_live"])
                values["live_type0"].append(readout["live_type0"])
                values["apoptosis_fraction"].append(readout["apoptosis_fraction"])
            summary["readouts"][str(t)][label] = values

        ks = {}
        for metric in ("total_live", "live_type0", "apoptosis_fraction"):
            a_vals = summary["readouts"][str(t)]["main"][metric]
            b_vals = summary["readouts"][str(t)]["fixed"][metric]
            stat, pval = ks_2samp(a_vals, b_vals)
            ks[metric] = dict(
                main_mean=float(np.mean(a_vals)), main_std=float(np.std(a_vals, ddof=1)),
                fixed_mean=float(np.mean(b_vals)), fixed_std=float(np.std(b_vals, ddof=1)),
                ks_statistic=float(stat), ks_pvalue=float(pval), n_main=len(a_vals), n_fixed=len(b_vals))
        summary["readouts"][str(t)]["ks_tests"] = ks

    out_path = ROOT / "physispatial_validation/tnfalpha_rng/check6_results.json"
    out_path.write_text(json.dumps(summary, indent=2))
    print("wrote", out_path)
    print("wall time: min=%.1fs max=%.1fs mean=%.1fs" % (min(wall_times), max(wall_times), np.mean(wall_times)))


if __name__ == "__main__":
    main()
