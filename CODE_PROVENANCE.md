# Code provenance and architectural changes

## Complete upstream base

Official PhysiBoSS v2.2.3, Git commit **514efcfce9d099f800e1d6cef1aa59a6f45b27c5**, cloned from https://github.com/PhysiBoSS/PhysiBoSS . This release uses PhysiCell1.14.0. Do not substitute the later master snapshot that also says PhysiBoSS2.2.3 but uses PhysiCell1.14.2. All748 tracked upstream files and existing sample projects are retained. upstream_manifest.json records every original byte hash. The upstream README and default Makefiles are preserved under physispatial_provenance/upstream/.

This commit identifies the **official distribution base**, NOT an asserted original historical manuscript executable. Original MN5 project copies contain no recoverable Git HEAD/build manifest. Source hashes identify the scientific snapshots; binary-to-paper identity remains unproven.

## Original scientific code and populations

Scientific main.cpp, custom_modules, XML, BND/CFG and geometry inputs come from the already recovered/verified MN5 UNITS_TESTS_NEW_VERSION/Prisma, Cilindro and Esfera families. Cilindro_simple is not substituted. Reuse location before integration: PhysiSpatial-Geometry-Tests, without modifying it. recovery_catalog.json and original_manifest.json preserve all45 geometry×population×D source/config catalog entries. The integrated defaults are nine D500 projects (3geometries×3populations). Different D-specific historical main save conditions are catalogued, not silently selected by a requested diffusion value.

integrated_profiles.json maps each portable config/model/main to the original MN5 source path and SHA256. *.original.xml preserve original bytes. Portable XMLs alter resource paths only, keeping all numerical defaults/BC flags, schedules, pharmacology and model mappings unchanged. Concentration defaults differ by geometry/population. All three Boolean definitions per profile are retained, including the historical norm_0 filename conventions; no Boolean network/CFG content is edited. New default config/PhysiCell_settings.xml is the original BM0 profile with portable paths.

## No overwritten internal framework components

core/, modules/, BioFVM/ and addons/PhysiBoSS/src match the official commit byte-for-byte. Archived Prism framework matches upstream BioFVM. Cylinder/Sphere retain historical OpenMP changes in BioFVM_microenvironment.cpp and BioFVM_solvers.cpp. A historical PhysiCell_geometry.cpp suppresses per-cell CSV print logging. These exact C++ files are compiled as flat **custom_modules/historical_*.cpp** in the affected new projects, with include directories pointing to unchanged upstream headers. framework_differences.json and per-file patches describe every difference. No hybrid or newly invented diffusion implementation was created.

## Make integration and dependency

Root Makefile and sample_projects/Makefile-default append a single include for physispatial_tools/projects.mk; their original target recipes remain verbatim. Each new project uses its original recovered geometry Makefile, with only program name, historical-source compile paths, offline bundled-MaBoSS static-library dependency, added target include and reset→clean dependency adapted. The latter prevents stale historical BioFVM objects leaking into a subsequently loaded standard sample. original_makefiles/ preserves the baseline geometry Makefiles; makefile_diffs/ records integration patches. Normal project copying/loading is performed by select_project.py for main.cpp, Makefile, custom_modules/ and config/, plus population-specific original main selection. Previous active files are archived, not destroyed by the loader.

Original MaBoSS2.5.6 source/headers/LICENSE are bundled from the recovered source snapshot. The three project Makefiles build it offline at MAXNODES256. Prebuilt MaBoSS libraries/objects from MN5 were not substituted. Git ignore exceptions ensure this bundled dependency SOURCE is not accidentally omitted from a future fork, while generated binaries/objects/caches remain ignored.

## New glue, not new physics

physispatial_tools provides conventional project selection, isolated XML parameterization, collision-safe run/sweep handling, locked build cache, optional CPU SLURM template and validation. source_probe.cpp is an explicitly separate test driver that invokes original setup/activation/generator functions; it is not a production model or a substitute full cellular trajectory. No production treatment schedule is accelerated. Tests do not shrink the mesh, source set or initial tissue. Integration/recovery/report/packaging helpers are maintenance utilities; recipients need only project make targets, run.py/sweep.py and validators, not the previous scaffold or original absolute MN5 paths.

No manuscript analysis, penetration reference, existing simulation, previous ZIP or previous repository was altered. No automatic GitHub publication, software installation, production sweep or SLURM job was performed.

## TNFalpha RNG seeding fix (branch fix/tnfalpha-rng-seeding)

The TNFalpha activation draw in `anti_node_mapping_function()` used BioFVM's `uniform_random()` — a single, never-seeded, unsynchronized global generator — so it ignored `random_seed` and was not thread-safe. Fixed with a stateless, seeded, thread-count-independent hash-based draw; see the README's "Random seeds" section for the full explanation and `physispatial_validation/tnfalpha_rng/` for the verification numbers. No physical, Boolean or numerical parameter changed; no `.bnd`/`.cfg`/`.csv`/`.tsv`/`PhysiCell_settings.original.xml` file was touched; no `tnf_seed` entry was added to any shipped XML (it is read with `parameters.ints.find_index("tnf_seed")` and derives from `random_seed` when absent, so the shipped XML files and their hashes are unchanged). The fix is byte-identical across the three projects (verified by diff) in `custom_modules/tnf_boolean_model_interface.cpp`/`.h`; `custom_modules/custom.cpp` carries the same added seeding block, interleaved with each project's otherwise-unrelated, pre-existing content.

| File | old SHA256 | new SHA256 |
|---|---|---|
| `sample_projects_intracellular/boolean/physispatial_prism/custom_modules/tnf_boolean_model_interface.cpp` | `28694a2aa6e6e7e1e9c099de6b37ae790c874ab4bff28b4e23550d809449b26a` | `fba5501770b1e3b62ce3401844cef898de42fecc3abd4a9fb344205abaf3f7aa` |
| `sample_projects_intracellular/boolean/physispatial_prism/custom_modules/tnf_boolean_model_interface.h` | `9fab8f8081f732abe639fac94b5eb7448713537e7d11c28432d8362b681b6ca2` | `4eb60ab03b45ff5117ddd29e72272fdb7a6ca75e25963b5dc0a9bea35a64fec4` |
| `sample_projects_intracellular/boolean/physispatial_prism/custom_modules/custom.cpp` | `57d30c9375d7b2b598f2402265d52dcae49a07042b06b77101f25cfe3bc8f5d0` | `deda394e145261097d9670e2a90fd0378b34a959c923bb2c9ea6d7c2a21c05fd` |
| `sample_projects_intracellular/boolean/physispatial_cylinder/custom_modules/tnf_boolean_model_interface.cpp` | `28694a2aa6e6e7e1e9c099de6b37ae790c874ab4bff28b4e23550d809449b26a` | `fba5501770b1e3b62ce3401844cef898de42fecc3abd4a9fb344205abaf3f7aa` |
| `sample_projects_intracellular/boolean/physispatial_cylinder/custom_modules/tnf_boolean_model_interface.h` | `9fab8f8081f732abe639fac94b5eb7448713537e7d11c28432d8362b681b6ca2` | `4eb60ab03b45ff5117ddd29e72272fdb7a6ca75e25963b5dc0a9bea35a64fec4` |
| `sample_projects_intracellular/boolean/physispatial_cylinder/custom_modules/custom.cpp` | `57d30c9375d7b2b598f2402265d52dcae49a07042b06b77101f25cfe3bc8f5d0` | `deda394e145261097d9670e2a90fd0378b34a959c923bb2c9ea6d7c2a21c05fd` |
| `sample_projects_intracellular/boolean/physispatial_sphere/custom_modules/tnf_boolean_model_interface.cpp` | `28694a2aa6e6e7e1e9c099de6b37ae790c874ab4bff28b4e23550d809449b26a` | `fba5501770b1e3b62ce3401844cef898de42fecc3abd4a9fb344205abaf3f7aa` |
| `sample_projects_intracellular/boolean/physispatial_sphere/custom_modules/tnf_boolean_model_interface.h` | `9fab8f8081f732abe639fac94b5eb7448713537e7d11c28432d8362b681b6ca2` | `4eb60ab03b45ff5117ddd29e72272fdb7a6ca75e25963b5dc0a9bea35a64fec4` |
| `sample_projects_intracellular/boolean/physispatial_sphere/custom_modules/custom.cpp` | `d79ffa98c99a631419524fb886d2b51327b784959fd2a4b46157ce970e869fe9` | `a3c68b6748d0952d87ecdc9de4b94a37bef772aa962dfad2bb3f2a02e6bf5bb0` |
| `PHYSISPATIAL_README.md` | `35c85f9e486d81a4053869cdac89005c6ca04425677d84f75f3825602e767427` | `fcc521ee942a6a665ecd882b6ef1ccba72601fde03cd77ba2a7016d6d974cca9` |

`core/`, `modules/`, `BioFVM/` and `addons/` are untouched by this branch; no entry in `upstream_manifest.json` changes. No `config/**/PhysiCell_settings.xml`, `.original.xml`, `.bnd`, `.cfg`, `.csv` or `.tsv` file changes; `integrated_profiles.json` and `original_static_profiles.json` entries are unaffected.

Separately and outside this fix's scope: this working tree's line endings differ from the committed history (CRLF in the working tree vs. LF in `HEAD` and in the hashes recorded above and elsewhere in this document, across nearly the entire repository, pre-dating this branch). The nine files touched above were normalized to LF before editing, specifically so this branch's diff stays minimal and these hashes are meaningful; no other file's line endings were changed by this branch.
