"""Bounded integration tests. Full Prism smoke; source-only diagnostics for all geometries."""
import json,os,shutil,subprocess,time
from pathlib import Path
from run import ROOT,build,prepare,execute,sha
def main():
    validation=ROOT/'physispatial_validation';work=ROOT/'physispatial_work/validation'
    if work.exists():
        assert len(json.loads((validation/'source_probe_results.json').read_text()))==18
        assert len(json.loads((validation/'build_results.json').read_text()))==3
        return complete(work/'full_prism_smoke',validation)
    work.mkdir(parents=True,exist_ok=False)
    builds=[];probes=[]
    for geometry in ['prism','cylinder','sphere']:
        started=time.monotonic();executable=build(geometry,'BM0',2)
        builds.append(dict(geometry=geometry,population='BM0',success=True,wall_seconds=time.monotonic()-started,
            executable_sha256=sha(executable),binary=str(executable.relative_to(ROOT))))
        # Build and execute a distinct validation driver using the ORIGINAL compiled objects.
        objects=subprocess.check_output(['make','--no-print-directory','-s','--eval=physispatial-objects: ; @echo $(ALL_OBJECTS)','physispatial-objects'],cwd=ROOT,text=True).strip().split()
        probe=work/('source_probe_'+geometry)
        command=['g++','-O3','-std=c++11','-fopenmp','-DADDON_PHYSIBOSS','-DMAXNODES=256','-I.',
             '-Iaddons/PhysiBoSS/MaBoSS/engine/include']
        if geometry=='sphere':command+=['-DPHYSISPATIAL_SPHERE']
        command+=objects+['physispatial_tools/source_probe.cpp','-Laddons/PhysiBoSS/MaBoSS/engine/lib','-lMaBoSS_256n-static','-ldl','-o',str(probe)]
        with (validation/('build_probe_'+geometry+'.log')).open('x') as log:subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        defaults=json.loads((ROOT/'physispatial_provenance/integrated_profiles.json').read_text())
        for pop in ['BM0','BM1','BM2']:
            for label,d,c in [('original',None,None),('changed',1250,2e-7)]:
                run=prepare(geometry,pop,d,c,42,1,work,f'probe_{geometry}_{pop}_{label}',.02)
                started=time.monotonic()
                with (run/'probe.log').open('x') as log:
                    result=subprocess.run([str(probe),'config/run.xml','probe.json'],cwd=run,stdout=log,stderr=subprocess.STDOUT,timeout=60)
                if result.returncode!=0:raise RuntimeError('Source probe failed: '+str(run))
                row=json.loads((run/'probe.json').read_text());expected=defaults[geometry+'/'+pop]
                assert row['D']==(1250 if label=='changed' else expected['default_D'])
                assert row['C']==(2e-7 if label=='changed' else expected['default_C'])
                assert row['unique_prescribed_source_voxels']==dict(prism=99,cylinder=24,sphere=98)[geometry]
                assert row['source_concentration_max_error']==0 and row['drug_active_sources_before']==0
                row.update(geometry=geometry,population=pop,test=label,wall_seconds=time.monotonic()-started,
                    source_probe_sha256=sha(probe),original_model_inputs_parsed=True)
                probes.append(row)
                shutil.copy2(run/'probe.log',validation/(run.name+'.log'))
        (validation/'build_results.json').write_text(json.dumps(builds,indent=2))
        (validation/'source_probe_results.json').write_text(json.dumps(probes,indent=2))
        print('Built and source-tested',geometry,flush=True)
    # Only the inexpensive original Prism tissue is fully initialized here.
    smoke=prepare('prism','BM0',500,1e-7,0,1,work,'full_prism_smoke',.02)
    try:execute(smoke,2,90,memory_gb=3.5)
    except RuntimeError:pass # A failure is evidence, never converted to a passing run.
    complete(smoke,validation)
def complete(smoke,validation):
    m=json.loads((smoke/'run_manifest.json').read_text())
    sample=validation/'prism_smoke';sample.mkdir(exist_ok=True)
    for name in ['run_manifest.json','simulation.log']:shutil.copy2(smoke/name,sample/name)
    if m['state']=='FINISHED':
        import numpy as np
        from scipy.io import loadmat
        import xml.etree.ElementTree as ET
        checks=[]
        for stem in ['initial','final']:
            xml=smoke/'output'/(stem+'.xml');mat=smoke/'output'/(stem+'_cells.mat')
            tree=ET.parse(xml);labels={e.text:int(e.get('index')) for e in tree.findall('.//simplified_data/labels/label')}
            data=loadmat(mat)['cells'];pos=labels['position']
            # Initialization count is fixed; the original model may divide even in a short smoke.
            assert (data.shape[1]==1216 if stem=='initial' else data.shape[1]>0) and np.isfinite(data[pos:pos+3]).all()
            checks.append(dict(snapshot=stem,n_cells=data.shape[1],time_min=float(tree.findtext('.//current_time')),position_finite=True,
               cell_ids_unique=len(np.unique(data[labels['ID']]))==data.shape[1]))
            # Small complete snapshot bundles: include every filename referenced by XML.
            for f in (smoke/'output').glob(stem+'*'):
                if f.is_file():shutil.copy2(f,sample/f.name)
        (validation/'full_prism_smoke_checks.json').write_text(json.dumps(checks,indent=2))
    report=dict(full_prism_state=m['state'],full_prism_wall_seconds=m.get('wall_seconds'),
       full_cylinder_state='PENDING_RESOURCE_ADEQUATE_NODE',full_sphere_state='PENDING_RESOURCE_ADEQUATE_NODE',
       reason='Full-size legacy network-per-cell initialization is not safely affordable on this desktop; previous4GiB Cylinder failure is documented. No tissue or mesh was shrunk.',
       probes_are_not_production_trajectories=True,new_slurm_jobs=0,production_sweeps_run=0)
    (validation/'runtime_scope.json').write_text(json.dumps(report,indent=2));print(report)
if __name__=='__main__':main()
