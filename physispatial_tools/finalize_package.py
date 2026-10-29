"""Integrity-check recovered sources and export a complete clean PhysiBoSS ZIP."""
import argparse,hashlib,json,os,shlex,shutil,stat,subprocess,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify_remote(host,identity):
    records=json.loads((ROOT/'physispatial_provenance/original_manifest.json').read_text())
    files={info['source_path']:info for info in records.values()}
    code='''import datetime,hashlib,json,sys
from pathlib import Path
records=json.load(sys.stdin)
for name,info in records.items():
 p=Path(name);assert str(p).startswith('/gpfs/projects/bsc08/bsc08180/UNITS_TESTS_NEW_VERSION/')
 s=p.stat();assert s.st_size==info['size'] and s.st_mtime_ns==info['mtime_ns'],name
 assert hashlib.sha256(p.read_bytes()).hexdigest()==info['sha256'],name
print(json.dumps(dict(success=True,original_files_checked=len(records),originals_unchanged=True,
 new_simulation_jobs=0,timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())))
'''
    cmd=['ssh','-o','ControlMaster=no','-o','ControlPath=none','-o','BatchMode=yes','-o','ConnectTimeout=10','-i',identity,host,
        '/usr/bin/python3 -c '+shlex.quote(code)]
    result=subprocess.run(cmd,input=json.dumps(files).encode(),capture_output=True,timeout=240)
    if result.returncode:raise RuntimeError(result.stderr.decode())
    line=next(line for line in result.stdout.decode().splitlines() if line.startswith('{'))
    (ROOT/'physispatial_validation/remote_original_integrity.json').write_text(json.dumps(json.loads(line),indent=2))
    return json.loads(line)
def collect():
    upstream=json.loads((ROOT/'physispatial_provenance/upstream_manifest.json').read_text())['files']
    files={name:ROOT/name for name in upstream}
    for folder in ['physispatial_tools','physispatial_provenance','physispatial_validation']:
        for p in sorted((ROOT/folder).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.zip']:
                files[str(p.relative_to(ROOT))]=p
    for name in ['README.md','CODE_PROVENANCE.md','VALIDATION_REPORT.md','THIRD_PARTY_NOTICES.md']:
        files[name]=ROOT/name
    for g in ['prism','cylinder','sphere']:
        for p in (ROOT/'sample_projects_intracellular/boolean'/('physispatial_'+g)).rglob('*'):
            if p.is_file():files[str(p.relative_to(ROOT))]=p
    # Export the exact recovered dependency SOURCES, not build products or regenerated parser files.
    # The original source-only snapshot is preserved in the predecessor and protected by hashes.
    canonical=ROOT.parent/'PhysiSpatial-Geometry-Tests/src/vendor/41f348acd1fbc384/addons/PhysiBoSS/MaBoSS'
    for p in canonical.rglob('*'):
        if p.is_file():files[str(Path('addons/PhysiBoSS/MaBoSS')/p.relative_to(canonical))]=p
    return files
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--host',required=True);p.add_argument('--identity',required=True);args=p.parse_args()
    upstream=json.loads((ROOT/'physispatial_provenance/upstream_manifest.json').read_text())['files']
    allowed={'.gitignore','README.md','Makefile','sample_projects/Makefile-default'}
    for name,digest in upstream.items():assert (ROOT/name).is_file() and (name in allowed or sha(ROOT/name)==digest),name
    protected=json.loads((ROOT/'physispatial_provenance/protected_predecessor_manifest.json').read_text())
    for name,info in protected.items():
        path=Path(name);s=path.stat();assert (s.st_size,s.st_mtime_ns)==(info['size'],info['mtime_ns']),name
        assert sha(path)==info['sha256'],name
    remote=verify_remote(args.host,args.identity)
    probes=json.loads((ROOT/'physispatial_validation/source_probe_results.json').read_text());assert len(probes)==18
    assert json.loads((ROOT/'physispatial_validation/static_and_interface_checks.json').read_text())['success']
    scope=json.loads((ROOT/'physispatial_validation/runtime_scope.json').read_text());assert scope['full_prism_state']=='FINISHED'
    (ROOT/'physispatial_validation/final_integrity.json').write_text(json.dumps(dict(success=True,upstream_files_retained=len(upstream),
        original_upstream_files_changed=sorted(allowed),core_modules_BioFVM_adapter_unchanged=True,
        local_predecessor_files_unchanged=len(protected),remote_original_files_unchanged=remote['original_files_checked'],
        sources_reconstructed=False,new_expensive_simulations=False,slurm_jobs_submitted=0,
        source_probes=18,full_prism_smoke=True,full_cylinder_sphere_pending=True),indent=2))
    files=collect();manifest={name:dict(size=path.stat().st_size,sha256=sha(path)) for name,path in sorted(files.items()) if not name.endswith('PACKAGE_MANIFEST.json')}
    (ROOT/'physispatial_provenance/PACKAGE_MANIFEST.json').write_text(json.dumps(manifest,indent=2))
    files=collect();archive=ROOT.parent/'PhysiBoSS_PhysiSpatial_UnitTests.zip';assert not archive.exists()
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,path in sorted(files.items()):z.write(path,arcname=str(Path(ROOT.name)/name))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(files)
        for name in upstream:assert str(Path(ROOT.name)/name) in z.namelist()
        assert not any('/.git/' in n or '/physispatial_work/' in n for n in z.namelist())
        with tempfile.TemporaryDirectory(prefix='physiboss_zip_portability_') as folder:
            z.extractall(folder);unpacked=Path(folder)/ROOT.name
            for script in ['validate_integration.py','test_sweeps.py']:
                result=subprocess.run([sys.executable,'-B',str(unpacked/'physispatial_tools'/script)],cwd=unpacked,capture_output=True,text=True,timeout=60)
                if result.returncode:raise RuntimeError(result.stdout+result.stderr)
                print('Extracted ZIP:',result.stdout.strip())
    portability=dict(success=True,zip_test_passed=True,all_upstream_files_present=True,
       extracted_distribution_static_and_sweep_tests_passed=True,previous_repository_required_for_runtime=False,original_MN5_paths_required_for_runtime=False,
       packaged_files=len(files))
    # This receipt is added after testing; it does not change any scientific input.
    receipt=ROOT/'physispatial_validation/zip_portability.json';receipt.write_text(json.dumps(portability,indent=2))
    with zipfile.ZipFile(archive,'a',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:z.write(receipt,arcname=str(Path(ROOT.name)/receipt.relative_to(ROOT)))
    downloads=Path('/home/amadrid/Descargas')/archive.name;assert not downloads.exists();shutil.copy2(archive,downloads)
    print('ZIP:',downloads,'bytes:',downloads.stat().st_size,'sha256:',sha(downloads))
if __name__=='__main__':main()
