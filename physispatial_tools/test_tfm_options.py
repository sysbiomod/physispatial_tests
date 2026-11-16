"""Checks for the TFM options of run.py (--max-time, --drug-time, --initial-tissue, --cells-file). No simulation."""
import csv,json,tempfile
from pathlib import Path
import xml.etree.ElementTree as ET
from run import ROOT,prepare,sha,PRISM_TISSUES
PRISM=ROOT/'sample_projects_intracellular/boolean/physispatial_prism/config'
def rows(path):
    with open(path,newline='') as f:return [tuple(float(v) for v in r[:3])+(int(r[3]),) for r in csv.reader(f) if r]
def main():
    tests={}
    def check(name,result):assert result,name;tests[name]='PASS'
    # The 'original' tissue documented in run.py is exactly the shipped CSV.
    original=rows(PRISM/'BM0/cells_prisma.csv')
    lattice={(x,y,z,0) for x in range(-470,-109,20) for y in range(-70,71,20) for z in range(-70,71,20)}
    check('original_prism_tissue_is_19x8x8_lattice',len(original)==1216 and {tuple(int(v) for v in r) for r in original}==lattice)
    with tempfile.TemporaryDirectory(prefix='tfm_options_') as temp:
        # Defaults: same XML changes as the original run.py.
        run=prepare('prism','BM0',None,None,0,1,temp,'default',.02);m=json.loads((run/'run_manifest.json').read_text())
        check('defaults_keep_original_xml',not any(k.endswith(('time_remove_o2[0]','filename[0]')) for k in m['changed_XML_elements'])
              and m['drug_activation_time']==35000 and m['initial_tissue']=='original' and m['initial_cells']==1216)
        for preset,expected in [('half-length',1536),('half-volume',2400)]:
            run=prepare('prism','BM1',1000,1e-5,7,2,temp,'tfm_'+preset,None,20000,0,preset)
            m=json.loads((run/'run_manifest.json').read_text());tree=ET.parse(run/'config/run.xml')
            cells=rows(run/m['initial_cells_csv']);spec=PRISM_TISSUES[preset]
            check(preset+'_xml',float(tree.findtext('overall/max_time'))==20000 and float(tree.findtext('user_parameters/time_remove_o2'))==0
                  and tree.findtext('initial_conditions/cell_positions/filename')=='cells_prisma_'+preset+'.csv'
                  and tree.findtext('initial_conditions/cell_positions/folder').strip()=='./config/BM1')
            check(preset+'_cells',len(cells)==expected==m['initial_cells'] and max(c[0] for c in cells)==-10 and min(c[0] for c in cells)==-470
                  and max(c[1] for c in cells)==max(spec['yz']) and all(c[3]==0 for c in cells))
            check(preset+'_inputs_hashed',m['initial_cells_csv'] in m['input_sha256'] and m['drug_activation_time']==0 and m['max_time']==20000)
            check(preset+'_original_csv_untouched',sha(run/'config/BM1/cells_prisma.csv')==sha(PRISM/'BM1/cells_prisma.csv'))
        own=Path(temp)/'my cells.csv';own.write_text('-470,0,0,0\n-450,0,0,0\n')
        run=prepare('prism','BM2',None,None,None,1,temp,'own_cells',None,5000,1000,'original',own)
        m=json.loads((run/'run_manifest.json').read_text())
        check('cells_file_copied',m['initial_cells']==2 and m['initial_cells_csv'].endswith('custom_my_cells.csv') and m['initial_tissue']=='custom')
        bad=Path(temp)/'bad.csv';bad.write_text('x,y,z,type\n0,0,0,0\n');outside=Path(temp)/'outside.csv';outside.write_text('900,0,0,0\n')
        invalid=[dict(smoke_minutes=.02,max_time=100),dict(max_time=0),dict(drug_time=-1),dict(initial_tissue='full'),
                 dict(geometry='cylinder',initial_tissue='half-length'),dict(geometry='sphere',cells_file=own),
                 dict(initial_tissue='half-length',cells_file=own),dict(cells_file=bad),dict(cells_file=outside)]
        for i,kw in enumerate(invalid):
            geometry=kw.pop('geometry','prism')
            try:prepare(geometry,'BM0',None,None,None,1,temp,f'invalid_{i}',**kw)
            except ValueError:pass
            else:raise AssertionError(('accepted',kw))
            assert not (Path(temp)/f'invalid_{i}').exists(),('left a run folder behind',kw)
        check('invalid_tfm_options_rejected_before_creating_runs',True)
    print(json.dumps(tests,indent=2))
if __name__=='__main__':main()
