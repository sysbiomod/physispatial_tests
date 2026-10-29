"""Small interface tests; preparation only, zero sweep simulations."""
import json,subprocess,sys,tempfile
from pathlib import Path
from run import ROOT,prepare
def main():
    checks={}
    with tempfile.TemporaryDirectory(prefix='physispatial_sweep_test_') as temp:
        dest=Path(temp)/'grid';args=[sys.executable,'-B',str(ROOT/'physispatial_tools/sweep.py'),'prepare','--geometry','cylinder',
           '--diffusions','500','1000','--concentrations','1e-9','1e-7','--populations','BM0','BM2',
           '--seeds','11','12','--threads','1','--directory',str(dest)]
        result=subprocess.run(args,capture_output=True,text=True);assert result.returncode==0,result.stderr
        rows=json.loads((dest/'sweep.json').read_text());assert len(rows)==16
        assert len({r['path'] for r in rows})==16
        for row in rows:
            m=json.loads((dest/row['path']/'run_manifest.json').read_text())
            assert m['state']=='PREPARED' and m['diffusion']==row['D'] and m['concentration']==row['C'] and m['seed']==row['seed'] and m['population']==row['population']
            assert not any((dest/row['path']/'output').iterdir())
        checks['16_independent_config_directories_correct_D_C_population_seeds']='PASS'
        assert subprocess.run(args,capture_output=True).returncode!=0;checks['existing_sweep_not_overwritten']='PASS'
        for i,(d,c,seed) in enumerate([(0,1e-7,0),(float('nan'),1e-7,0),(500,-1,0),(500,1e-7,-1)]):
            try:prepare('prism','BM0',d,c,seed,1,temp,'invalid_'+str(i))
            except ValueError:pass
            else:raise AssertionError('Invalid input accepted')
        checks['invalid_parameters_rejected']='PASS'
        assert not (ROOT/'physispatial_tools/sweep.py').read_text().count('sbatch(')
        checks['preparation_does_not_submit_or_execute']='PASS'
    (ROOT/'physispatial_validation/sweep_checks.json').write_text(json.dumps(checks,indent=2));print(len(checks),'sweep checks PASS')
if __name__=='__main__':main()
