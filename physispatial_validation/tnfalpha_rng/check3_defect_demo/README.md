# Check 3 evidence: defect demonstration on pre-fix `main`

Format of each `*.txt` file: `draw_index  uniform_value  omp_thread_num  cell_ID`,
the first 20 draws from BioFVM's `uniform_random()` at the TNFalpha decision
(`tnf_boolean_model_interface.cpp:164` on `main`), captured with a temporary,
uncommitted debug print (added only in a scratch git worktree on `main`, never
committed, discarded after this run).

Config: prism BM0, drug_conc=1e-7, time_remove_o2=1 min, max_time=60 min,
full saves every 20 min.

- `1thread_seed11.txt` vs `1thread_seed22.txt`: single-thread runs, different
  `random_seed` (11 vs 22) -> byte-identical draw sequences. Confirms the draw
  ignores `random_seed` entirely (ships with the default, unseeded
  `std::mt19937_64` construction).
- `4thread_seed33_run1.txt` vs `4thread_seed33_run2.txt`: two runs, same
  `random_seed` (33), 4 threads -> different draw sequences. Confirms the same
  seed does not reproduce the same run under threading. Note the duplicate
  values within a single run across different `omp_thread_num`/cell IDs (e.g.
  run1 draws 0-2: `0.571611` read by threads 0, 1 and 3 for different cells) --
  direct evidence of a data race on the shared, unsynchronized generator, not
  just a reproducibility gap.
