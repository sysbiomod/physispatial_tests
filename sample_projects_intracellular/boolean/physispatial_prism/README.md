# PhysiSpatial Prism sample project

Planar wall geometry, original cells_prisma.csv and ECM TSV. The original source reader skips the first line although the source TSV has no header, leaving99 distinct prescribed voxels. This historical quirk is unchanged. BM0 main.cpp differs from BM1/BM2: population selection loads the correct original main, not just an XML.

## Standard PhysiBoSS workflow (from distribution root)

```bash
make physispatial-prism POPULATION=BM0
make -j2 ARCH=x86-64
mkdir output_0  # Must be NEW; otherwise choose a new save/folder in the XML.
./physispatial_prism config/PhysiCell_settings.xml
```

The last command executes the ORIGINAL long horizon, not a cheap test. Prefer the safe preparation/smoke commands in the root README. To change population, reload with POPULATION=BM1 or BM2 and rebuild. D/C changes in the active XML require no recompile. Do not simply change cell_type IDs: historical projects use ID0 for each selected BM population, and files named norm_0.cfg contain different population-specific values.

## Original defaults

- BM0: D=500, C=1e-09, drug activation=35000min, initial cells=1216, sphere radius=None, prescribed source voxels=99.
- BM1: D=500, C=1e-09, drug activation=35000min, initial cells=1216, sphere radius=None, prescribed source voxels=99.
- BM2: D=500, C=1e-09, drug activation=35000min, initial cells=1216, sphere radius=None, prescribed source voxels=99.

The portable default config/PhysiCell_settings.xml selects BM0. config/BM0..BM2/PhysiCell_settings.xml contain population-matched configurations; *.original.xml preserve original bytes and historical paths for provenance only. Resource paths are the only portable-XML adaptations. All BND/CFG/source/ECM/cell file contents are unchanged. profiles/BM*/main.cpp preserve each population's exact original main. Source TSV numbers are voxel indices, not physical coordinates.

D: microenvironment_setup/variable[@name='drug_A']/physical_parameter_set/diffusion_coefficient (micron²/min). C: user_parameters/drug_conc (original numerical units; unit labels are unresolved). Drug is initially inactive at sources; time_remove_o2 governs its original scheduled activation. Zero early drug field does not imply the concentration setting was ignored.

See root VALIDATION_REPORT.md for measured checks and remaining full-runtime limits. Do not infer long-time validation from a source-only probe.
