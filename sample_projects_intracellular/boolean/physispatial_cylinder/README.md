# PhysiSpatial Cylinder sample project

Original Cilindro family, NOT Cilindro_simple.10752 CSV-initialized cells, two XY source columns and24 prescribed voxel indices. Original BioFVM OpenMP variants are compiled from historical_*.cpp in custom_modules; upstream BioFVM files remain unchanged.

## Standard PhysiBoSS workflow (from distribution root)

```bash
make physispatial-cylinder POPULATION=BM0
make -j2 ARCH=x86-64
mkdir output_0  # Must be NEW; otherwise choose a new save/folder in the XML.
./physispatial_cylinder config/PhysiCell_settings.xml
```

The last command executes the ORIGINAL long horizon, not a cheap test. Prefer the safe preparation/smoke commands in the root README. To change population, reload with POPULATION=BM1 or BM2 and rebuild. D/C changes in the active XML require no recompile. Do not simply change cell_type IDs: historical projects use ID0 for each selected BM population, and files named norm_0.cfg contain different population-specific values.

## Original defaults

- BM0: D=500, C=6e-07, drug activation=30000min, initial cells=10752, sphere radius=None, prescribed source voxels=24.
- BM1: D=500, C=2.5e-08, drug activation=30000min, initial cells=10752, sphere radius=None, prescribed source voxels=24.
- BM2: D=500, C=5e-08, drug activation=30000min, initial cells=10752, sphere radius=None, prescribed source voxels=24.

The portable default config/PhysiCell_settings.xml selects BM0. config/BM0..BM2/PhysiCell_settings.xml contain population-matched configurations; *.original.xml preserve original bytes and historical paths for provenance only. Resource paths are the only portable-XML adaptations. All BND/CFG/source/ECM/cell file contents are unchanged. profiles/BM*/main.cpp preserve each population's exact original main. Source TSV numbers are voxel indices, not physical coordinates.

D: microenvironment_setup/variable[@name='drug_A']/physical_parameter_set/diffusion_coefficient (micron²/min). C: user_parameters/drug_conc (original numerical units; unit labels are unresolved). Drug is initially inactive at sources; time_remove_o2 governs its original scheduled activation. Zero early drug field does not imply the concentration setting was ignored.

See root VALIDATION_REPORT.md for measured checks and remaining full-runtime limits. Do not infer long-time validation from a source-only probe.
