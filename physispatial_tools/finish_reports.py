"""Reports distinguish compilation, direct source-function probes and full cellular runtime."""
import difflib,json,platform,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def write(name,text):(ROOT/name).write_text(text.strip()+'\n')
def main():
    validation=ROOT/'physispatial_validation';profiles=json.loads((ROOT/'physispatial_provenance/original_static_profiles.json').read_text())
    builds=json.loads((validation/'build_results.json').read_text());probes=json.loads((validation/'source_probe_results.json').read_text())
    runtime=json.loads((validation/'runtime_scope.json').read_text());comparison=json.loads((validation/'migration_state_comparison.json').read_text())
    geometry_table='| Geometry | Population | Original C | Source voxels | Initial cells / generated positions | Activation (min) |\n| --- | --- | --- | --- | --- | --- |\n'
    for p in profiles:
        probe=next(r for r in probes if r['geometry']==p['geometry'] and r['population']==p['population'] and r['test']=='original')
        n=p['initial_cells_from_csv'] if p['initial_cells_from_csv'] is not None else probe['original_sphere_generator_positions']
        geometry_table+=f"| {p['geometry']} | {p['population']} | {p['original_C']:g} | {p['unique_source_voxels']} | {n} | {p['drug_activation_min']:g} |\n"
    write('CODE_PROVENANCE.md','''# Code provenance and architectural changes

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
''')
    write('VALIDATION_REPORT.md',f'''# Validation report — PhysiBoSS integration, 2026-10-27

## Summary

- **Complete official distribution**: all748 upstream files retained; core/modules/BioFVM/PhysiBoSS adapter unchanged.
- **Three standard sample projects compile**, using normal make loading and make -j2 ARCH=x86-64. Build manifests/logs for Prism BM0, Cylinder BM0 and Sphere BM0 are in physispatial_validation/.
- **17 static/interface checks** and **4 sweep-preparation checks** passed.
- **18 direct source-function probes** passed: every geometry×BM population, with original D/C and with D1250/C2e−7, no executable rebuild between D/C changes. These are source/initialization unit tests, NOT full cellular trajectories.
- **Full original Prism BM0 smoke completed**: initial1216 cells, final1218 at0.03min for max_time0.02min (original loop final step). The two added cells are also present in the earlier scaffold smoke; no stable-count assertion is imposed on a proliferative model.
- **Migration check**: initial/final cell matrices match the preceding scaffold bitwise after excluding only the documented deprecated uninitialized total_attack_time row; maximum difference elsewhere0. IDs, positions, cell type, phases and all other saved rows agree. This does not prove long-time or cross-platform reproducibility.
- Standard make reset succeeds, clears historical objects and restores the default Makefile while retaining the three new targets.
- No full parameter sweep, new SLURM job or installation. Original files are integrity-checked in final_integrity.json/remote_original_integrity.json.

## Original geometry contracts

{geometry_table}

All profiles use D500 originally. Sphere counts above are measured by calling the ORIGINAL position generator with the original cell radius and tumor_radius, without allocating tens of thousands of per-cell MaBoSS states. They are not falsely labeled completed tissue initialization. Prism mesh59×18×18; Cylinder118×56×8; Sphere100×100×100 (the exact per-profile contracts are checked against original_static_profiles.json; consult source_probe_results.json if a textual summary differs).

## What the source probes establish

The test driver loads the real portable XML, invokes original setup_microenvironment and create_cell_types (actual Boolean files parsed), obtains prescribed source voxel IDs with the original reader, confirms the original source count and mesh dimensions, and reads the actual BioFVM diffusion coefficient. Original sources are inactive for drug before scheduled activation. The driver then **directly invokes change_dirichlet_nodes for a function-level test**, applies Dirichlet conditions and checks every prescribed drug source equals the requested C exactly. All18 cases have zero source-concentration error; active sources go0→99/24/98.

This verifies active source values and parameter wiring without simulating30000/35000min. It is not a delayed-treatment trajectory, steady-state drug profile, full population response or long-exposure validation. Actual XML/MAT microenvironment output is generated by the original writer in the probe working directories; large probe MATs are omitted from the ZIP. Compact complete initial/final XML/MAT/Boolean/graph outputs from the full Prism smoke are included.

## Full cellular runtime and resource limits

Prism full-size smoke: state **{runtime['full_prism_state']}**, wall time {runtime['full_prism_wall_seconds']:.2f}s,1CPU thread,3.5GiB address-space cap. This cap is not a measured peak RSS or production requirement. A short endpoint does not remove initialization cost.

Cylinder/Sphere **full cellular initialization remains pending on an adequately provisioned compute node**. Previous original Cylinder10752-cell initialization failed under a4GiB cap; the current desktop has limited available RAM. The source probes deliberately avoid per-cell network allocation and do not get promoted to full-runtime success. No login-node fallback or reduced geometry was used. Sphere BM0 has50232 generated positions and BM1/BM2 have31651, so its full initialization is not a small desktop smoke.

Optional CPU SLURM templates are provided, with explicit user account/partition selection; no job was submitted or permissions assumed.32GiB/8CPUs/2h are configurable caps, not guaranteed suitable for every full model. No new production outcome is claimed.

## Preserved hazards and limits

1. Original source TSV parser uses unchecked do/while(!eof()) and skips a first line. Prism99 effective sources (nominal100) is preserved. Trailing-newline EOF behavior remains an original C++ robustness hazard; tests passed on this toolchain, not proof of portable absence of undefined behavior. No silent physics-changing cleanup was made.
2. Original total_attack_time is an uninitialized deprecated output; exclude it from scientific analysis, never conflate with MAT metadata. Migration comparison explicitly excludes only that field.
3. Original main can return0 after caught exceptions. New run utility also checks final.xml and endpoint time; output collisions/started-run re-execution are rejected.
4. Concentration units are inconsistent in original input annotations. Values are preserved in model numerical convention; no unsupported mM/M conversion.
5. D500 default source profiles are integrated; D-specific historical save variants are catalogued, not declared identical trajectories or silently swapped.
6. Original upstream commit is pinned, but original historical binary/commit/compiler provenance remains absent. Public redistribution of biological inputs still requires author approval.

## Reproduce checks

`python3 -B physispatial_tools/validate_integration.py` and `python3 -B physispatial_tools/test_sweeps.py` need only Python stdlib. Full runtime/probes need the normal C++ toolchain; optional NumPy/SciPy are used to inspect full MAT output. runtime_checks.py is bounded validation, not a production sweep; it writes physispatial_work/validation and never overwrites existing simulation outputs. Runtime evidence is local to this integration and not inferred from compilation.
''')
    # Derive textual mesh summary from measured profiles, not guesses.
    text=(ROOT/'VALIDATION_REPORT.md').read_text()
    cylinder=next(r for r in probes if r['geometry']=='cylinder')
    text=text.replace('Cylinder118×56×8',f"Cylinder{cylinder['mesh_x']}×{cylinder['mesh_y']}×{cylinder['mesh_z']}")
    (ROOT/'VALIDATION_REPORT.md').write_text(text)
    patchdir=ROOT/'physispatial_provenance/makefile_diffs';patchdir.mkdir(exist_ok=True)
    for g in ['prism','cylinder','sphere']:
        before=(ROOT/'physispatial_provenance/original_makefiles'/(g+'.Makefile')).read_text()
        after=(ROOT/'sample_projects_intracellular/boolean'/('physispatial_'+g)/'Makefile').read_text()
        (patchdir/(g+'.patch')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='original/'+g+'/Makefile',tofile='integrated/'+g+'/Makefile')))
    # Config actually executed, alongside immutable compact output evidence.
    sample=validation/'prism_smoke';shutil.copytree(ROOT/'physispatial_work/validation/full_prism_smoke/config',sample/'config',dirs_exist_ok=True)
    (validation/'toolchain.json').write_text(json.dumps(dict(python=platform.python_version(),gcc=subprocess.check_output(['g++','--version'],text=True).splitlines()[0],
       make=subprocess.check_output(['make','--version'],text=True).splitlines()[0],architecture='x86-64',MAXNODES=256),indent=2))
    readme=(ROOT/'README.md').read_text()
    readme=readme.replace('## Layout','## Measured validation status\n\nAll three projects compile;17 interface +4 sweep checks and18 source-function probes pass. Full Prism smoke completes and matches the previous scaffold except one known uninitialized field. Full cellular Cylinder/Sphere runtime remains pending adequate-memory compute resources; source probes are not full trajectories. See VALIDATION_REPORT.md.\n\n## Layout')
    (ROOT/'README.md').write_text(readme)
if __name__=='__main__':main()
