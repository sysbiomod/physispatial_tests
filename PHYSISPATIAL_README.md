# PhysiBoSS + PhysiSpatial geometry unit tests

A **complete PhysiBoSS distribution**, based on official tag **v2.2.3**, commit **514efcfce9d099f800e1d6cef1aa59a6f45b27c5** (PhysiCell1.14.0), with three integrated sample projects recovered from the original PhysiSpatial/Ramachandran experiments on MN5. Nothing is automatically published to GitHub.

PhysiSpatial combines extracellular transport, spatial cellular mechanics and stochastic Boolean intracellular models. Prism, Cylinder and Sphere are controlled original geometric experiments; they are not interchangeable analytic transport boundaries or a new implementation of the model. See [the upstream release](https://github.com/PhysiBoSS/PhysiBoSS/releases/tag/v2.2.3), [original upstream README](physispatial_provenance/upstream/README.md), [provenance report](CODE_PROVENANCE.md) and [validation report](VALIDATION_REPORT.md).

## Measured validation status

All three projects compile;17 interface +4 sweep checks and18 source-function probes pass. Full Prism smoke completes and matches the previous scaffold except one known uninitialized field. Full cellular Cylinder/Sphere runtime remains pending adequate-memory compute resources; source probes are not full trajectories. See VALIDATION_REPORT.md.

## Layout

```text
core/ BioFVM/ modules/ addons/           original PhysiBoSS framework, unchanged
sample_projects/                       all original sample projects retained
sample_projects_intracellular/boolean/
    physispatial_prism/
    physispatial_cylinder/
    physispatial_sphere/
        main.cpp  Makefile  custom_modules/  config/  profiles/  README.md
physispatial_tools/                    parameter preparation, sweeps, tests, SLURM
physispatial_provenance/                original hashes, defaults, patches, licenses
physispatial_validation/                actual measured build/probe/smoke evidence
```

There is no independent root src/, models/ or geometries/ architecture. The bundled original MaBoSS2.5.6 source builds offline. No precompiled historical executable is required. New tests retain original physics and Boolean contents; minor resource-path relocation and Makefile plumbing are fully documented. The historical Cylinder/Sphere BioFVM OpenMP source variants and quiet CSV-loader implementation are flat custom_modules/historical_*.cpp sources, compiled only by these new projects. **Upstream core/modules/BioFVM files are never overwritten.**

## Requirements

Linux x86-64, C++11/OpenMP GCC/G++, GNU Make, flex, bison and Python3.9+ (stdlib). Python NumPy/SciPy are optional for runtime MAT validation, not required for simulations. No automatic downloads, software installations, GPU, GREASY or MPI. Other upstream optional ODE/FBA examples retain their normal upstream dependencies; only dependencies needed by the three Boolean tests are bundled here. Source/build paths must not contain whitespace or shell metacharacters because original C++ contains unquoted shell-copy calls.

## Load and compile a sample

From this distribution root:

```bash
make physispatial-prism
make -j2 ARCH=x86-64

make physispatial-cylinder POPULATION=BM1
make -j2 ARCH=x86-64

make physispatial-sphere POPULATION=BM2
make -j2 ARCH=x86-64
```

The first build compiles bundled MaBoSS(MAXNODES256). ARCH=x86-64 creates a portable CPU binary; default native is upstream's normal tuning. To select another compiler, use PHYSICELL_CPP or make CC=g++. Loading archives the previous main.cpp/Makefile/config/custom_modules and objects under ignored physispatial_work/backups instead of overwriting them irrecoverably. No simulation outputs are removed. Do not switch the active root project while manually compiling/running another one there.

Standard upstream `make reset` returns to sample_projects/Makefile-default, which keeps the three added targets. Original targets/recipes are not rewritten. After loading an unrelated original sample, first `make reset` before selecting a PhysiSpatial project (normal upstream workflow). Existing sample source files are unchanged. The new utility lives outside upstream scripts/, which historical reset recipes can remove. Standard upstream clean/reset targets can delete active working files as documented upstream; our loader makes recoverable backups.

## Original configurations and populations

Default is the recovered **D500/BM0 source profile**, with original D/C values retained, not a fabricated common concentration. config/BM0..BM2 contain portable population-matched XMLs and byte-identical original inputs. Numeric cell type0 and filenames norm_0 occur in all three selected BM profiles; their CFG contents differ. Use POPULATION selection, not filename or ID renaming. Prism has a population-dependent main variant, so population changes require reloading/recompiling; D/C changes do not. The45 original geometry/population/D directories are catalogued as provenance, but this distribution integrates the nine D500 source profiles. It does not silently swap in D-specific output-timing variants when D changes or claim every historical binary is recovered.

## Change D and C without recompilation

Edit config/PhysiCell_settings.xml:

```xml
<!-- drug_A / physical_parameter_set -->
<diffusion_coefficient units="micron^2/min">500</diffusion_coefficient>
<!-- user_parameters -->
<drug_conc type="double" units="">1e-7</drug_conc>
```

D is loaded by the original BioFVM XML setup. C is read by the original custom.cpp for the internal source Dirichlet vector; it is not a homogeneous initial drug field. The original model has inconsistent/empty concentration units (drug_A dimensionless, some pharmacology labels mM), so no concentration-unit conversion is invented. No D/C C++ hardcode needs to be parameterized: both already come from XML. Other hardcoded transport constants, source reader quirks, apoptosis, mappings and initial distributions remain untouched.

Original drug activation is35000min for Prism and30000min for Cylinder/Sphere (time_remove_o2 parameter). Early smoke tests legitimately show no activated drug field. Do not shorten this schedule or shrink the tissue to claim original full-runtime validation.

## Safe isolated run interface

Prepare only (never launches a simulation):

```bash
python3 -B physispatial_tools/run.py --geometry cylinder --population BM1   --diffusion 500 --concentration 1e-7 --seed 42 --threads 8 --prepare-only
```

Omit --prepare-only to build/cache the selected original project and run it at its ORIGINAL long horizon. Each invocation has a new directory in physispatial_runs/ with config/run.xml, original inputs, run_manifest.json, simulation.log and output/. An existing --name is refused; started/nonempty runs cannot be silently rerun. The build cache is locked for array tasks; simulations run from their own independent working directories.

Small simulated-time smoke, still with the **full original tissue**:

```bash
python3 -B physispatial_tools/run.py --geometry prism --population BM0   --diffusion 500 --concentration 1e-7 --seed 0 --threads 1   --smoke-minutes 0.02 --timeout 90
```

WARNING: short simulated time does not make initialization cheap. Cylinder/Sphere can need considerably more memory than a small desktop. --memory-gb is an optional process address-space cap, not a biological change. Runtime success requires a valid final.xml at the requested time, not just exit code0 (the original main can catch exceptions). Production resource requirements are not established by the short smoke.

## D/C parameter sweeps

Prepare a complete explicit grid, with configured seeds:

```bash
python3 -B physispatial_tools/sweep.py prepare --geometry prism   --diffusions 500 1000 1250 --concentrations 1e-9 1e-8 1e-7   --populations BM0 BM2 --seeds 10 11 12 --threads 8   --directory physispatial_runs/prism_grid
```

This prepares54 isolated configurations and sweep.json; it does NOT execute or submit. Seeds are explicit; repeated seeds do not become independent biological replicates. Radius/source layout/BCs stay population-profile-specific. Execute just one prepared row:

```bash
python3 -B physispatial_tools/sweep.py run   --directory physispatial_runs/prism_grid --index 0
```

The same executable is reused across D/C combinations of a fixed geometry/population/source profile. No recompile per D/C. Initial directories, XML/hash allowlists and input hashes prevent accidental output collisions or unnoticed biological changes.

## Optional MN5 CPU SLURM

Copy/extract the complete distribution into your own project area. Load a site-provided GCC/make/flex/bison/Python environment. Use your CURRENT authorized CPU account and partition; no account is hardcoded and GPU allocations are unnecessary:

```bash
export MN5_ACCOUNT=YOUR_ACCOUNT
export MN5_CPU_PARTITION=YOUR_AUTHORIZED_CPU_PARTITION
sbatch --account="$MN5_ACCOUNT" --partition="$MN5_CPU_PARTITION"   --array=0-53%2 physispatial_tools/slurm_array.sbatch physispatial_runs/prism_grid
```

Submit from the root (or set PHYSISPATIAL_ROOT). Template8CPUs/32GiB/2h are editable resource caps, not measured production guarantees. Prepare threads to match --cpus-per-task. No job is submitted/monitored automatically. If runtime tests remain resource-limited, their status is explicitly reported, not inferred from compilation.

## Validate and find results

```bash
python3 -B physispatial_tools/validate_integration.py
```

Outputs follow original XML save intervals: initial/final and indexed XML/MAT, SVGs and Boolean CSV where emitted. full_cell MAT contains original positions/volume/phenotype; profile identity must be taken from the manifest, not cell_type0. Original Ramachandran penetration metrics are not recalculated here. Read VALIDATION_REPORT.md for what actually completed versus probes/full runtime pending, CODE_PROVENANCE.md for exact hashes and unrecoverable historical commits, and THIRD_PARTY_NOTICES.md before public release. Biological-model/input redistribution rights need author confirmation; no blanket new license is imposed on recovered models.
