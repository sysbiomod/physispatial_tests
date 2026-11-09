# TNFalpha RNG seeding validation (branch fix/tnfalpha-rng-seeding)

Results and interpretation: `VALIDATION_REPORT.md` addendum at the repo root.
Run everything from the repo root. Scratch outputs (`runs/`, `check4_runs/`,
`check6_runs/`) are gitignored; delete them before re-running.

| Check | Command |
|---|---|
| 3 (defect on `main`) | Evidence in `check3_defect_demo/` (captured with a temporary, uncommitted debug print in a scratch worktree of `main`; see its README). |
| 4 (reproducibility) | `python3 -B physispatial_validation/tnfalpha_rng/check4_reproducibility.py` (~3 min) |
| 5 (draw is thread-count independent) | Needs a temporary debug print logging `(cell_ID, time, draw)`; method and result in the VALIDATION_REPORT addendum. |
| 6 (statistical equivalence) | `python3 -B physispatial_validation/tnfalpha_rng/check6_statistical_equivalence.py --main-exe <main build> --fixed-exe <fixed build> --n-replicates 20 --max-time 300 --interval 50 --readout-times 100,200,300` (~50 min on 6 cores). Build `main`'s executable from a worktree: `git worktree add <dir> main`, then `make physispatial-prism POPULATION=BM0 && make -j2 ARCH=x86-64` there. |

Helpers: `scratch_run.py` (short-horizon scratch config on top of
`physispatial_tools/run.py`; never edits the shipped XML), `compare_runs.py`
(bitwise comparator, excludes only wall-clock metadata and the uninitialized
`total_attack_time` MAT row).
