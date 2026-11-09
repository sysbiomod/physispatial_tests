"""Compare two scratch-run output directories for bitwise reproducibility
(TNFalpha RNG seeding fix, checks 4 and 5).

Compares initial/final .xml, .mat, .csv and .txt output files, excluding only
the documented deprecated uninitialized total_attack_time row (MAT row index
22, per final.xml's <labels> legend), matching the existing migration check's
convention (see physispatial_validation/migration_state_comparison.json).
"""
import re
import sys
from pathlib import Path

import numpy as np
import scipy.io as sio

TOTAL_ATTACK_TIME_ROW = 22


RUNTIME_PATTERNS = [
    re.compile(rb"<current_runtime units=\"sec\">[^<]*</current_runtime>"),
    re.compile(rb"\d+ days, \d+ hours, \d+ minutes, and [\d.]+ seconds"),
    re.compile(rb"<created>[^<]*</created>"),
    re.compile(rb"<last_modified>[^<]*</last_modified>"),
]


def strip_wall_clock_metadata(raw_bytes):
    # current_runtime (XML) and the elapsed-wall-clock annotation (SVG) record
    # how long the run took on this machine, not simulation state; they are
    # expected to differ between separately-timed runs even when every
    # simulated quantity is bitwise identical.
    for pattern in RUNTIME_PATTERNS:
        raw_bytes = pattern.sub(b"<excluded: wall-clock runtime>", raw_bytes)
    return raw_bytes


def compare_mat(path_a, path_b):
    a = sio.loadmat(path_a)["cells"]
    b = sio.loadmat(path_b)["cells"]
    if a.shape != b.shape:
        return False, f"shape mismatch {a.shape} vs {b.shape}", None
    a_cmp = np.delete(a, TOTAL_ATTACK_TIME_ROW, axis=0)
    b_cmp = np.delete(b, TOTAL_ATTACK_TIME_ROW, axis=0)
    if np.array_equal(a_cmp, b_cmp):
        return True, "bitwise identical (excl. total_attack_time)", 0.0
    diff = np.max(np.abs(a_cmp - b_cmp))
    return False, "differs", float(diff)


def compare_bytes(path_a, path_b):
    a = path_a.read_bytes()
    b = path_b.read_bytes()
    if path_a.suffix in (".xml", ".svg"):
        a, b = strip_wall_clock_metadata(a), strip_wall_clock_metadata(b)
    return a == b, ("identical (excl. wall-clock runtime)" if a == b else "differs"), None


def find_comparable_files(run_dir):
    out = run_dir / "output"
    files = []
    for p in sorted(out.glob("*")):
        if p.suffix in (".xml", ".mat", ".csv", ".txt") or p.name == "final.svg" or p.name == "initial.svg":
            files.append(p.relative_to(out))
    return files


def compare_runs(run_a, run_b):
    run_a, run_b = Path(run_a), Path(run_b)
    files_a = find_comparable_files(run_a)
    files_b = find_comparable_files(run_b)
    common = sorted(set(files_a) & set(files_b))
    results = []
    for rel in common:
        pa, pb = run_a / "output" / rel, run_b / "output" / rel
        if rel.suffix == ".mat" and rel.name.endswith("_cells.mat"):
            ok, msg, maxdiff = compare_mat(pa, pb)
        else:
            ok, msg, maxdiff = compare_bytes(pa, pb)
        results.append(dict(file=str(rel), identical=ok, note=msg, max_abs_diff=maxdiff))
    return dict(run_a=str(run_a), run_b=str(run_b), n_compared=len(results),
                n_identical=sum(r["identical"] for r in results), files=results)


def main():
    import json
    result = compare_runs(sys.argv[1], sys.argv[2])
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["n_identical"] == result["n_compared"] else 1)


if __name__ == "__main__":
    main()
