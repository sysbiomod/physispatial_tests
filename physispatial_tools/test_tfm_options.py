"""Checks for the TFM options of run.py (--max-time, --drug-time, --initial-tissue, --fill-fraction,
--source-footprint, --cells-file). No simulation."""
import csv,json,tempfile
from pathlib import Path
import xml.etree.ElementTree as ET
from run import ROOT,prepare,sha,effective_sources
PRISM=ROOT/'sample_projects_intracellular/boolean/physispatial_prism/config'
def rows(path):
    with open(path,newline='') as f:return [tuple(float(v) for v in r[:3])+(int(r[3]),) for r in csv.reader(f) if r]
def ecm_voxels():
    lines=(PRISM/'BM0/ecm_prisma.tsv').read_text().split('\n')[1:]
    return {tuple(int(v) for v in l.split('\t')[:3]) for l in lines if l.strip()}
def voxel(x,y,z):return (round((x+590)/20),round((y+170)/20),round((z+170)/20))
def main():
    tests={}
    def check(name,result):assert result,name;tests[name]='PASS'
    # Geometry facts the presets rely on, read from the shipped inputs.
    original=rows(PRISM/'BM0/cells_prisma.csv')
    lattice={(x,y,z,0) for x in range(-470,-109,20) for y in range(-70,71,20) for z in range(-70,71,20)}
    check('original_prism_tissue_is_19x8x8_lattice',len(original)==1216 and {tuple(int(v) for v in r) for r in original}==lattice)
    ecm=ecm_voxels();src=[tuple(int(v) for v in l.split('\t')) for l in (PRISM/'BM0/prisma_wall_drug_2.tsv').read_text().split('\n') if l.strip()]
    check('ecm_tube_walls_at_j_k_4_and_15_cap_at_i_4',all((4,j,k) in ecm for j in range(4,16) for k in range(4,16))
          and all((i,4,8) in ecm and (i,15,8) in ecm and (i,8,4) in ecm and (i,8,15) in ecm for i in range(5,55)))
    check('original_sources_offset_j_k_4_13_and_99_used',{s[1] for s in src}==set(range(4,14)) and effective_sources(PRISM/'BM0/prisma_wall_drug_2.tsv')==99)
    with tempfile.TemporaryDirectory(prefix='tfm_options_') as temp:
        # Defaults: same XML changes as the original run.py.
        run=prepare('prism','BM0',None,None,0,1,temp,'default',.02);m=json.loads((run/'run_manifest.json').read_text())
        check('defaults_keep_original_xml',not any(k.endswith(('time_remove_o2[0]','filename[0]','blood_source_file[0]')) for k in m['changed_XML_elements'])
              and m['drug_activation_time']==35000 and m['initial_tissue']=='original' and m['initial_cells']==1216 and m['source_voxels']==99)
        # Full-section tissue, 75 % by default, plus the aligned source plate.
        run=prepare('prism','BM1',1000,1e-5,7,2,temp,'tfm_full',None,20000,0,'full-section',None,None,'tube')
        m=json.loads((run/'run_manifest.json').read_text());tree=ET.parse(run/'config/run.xml');cells=rows(run/m['initial_cells_csv'])
        check('full_section_xml',float(tree.findtext('overall/max_time'))==20000 and float(tree.findtext('user_parameters/time_remove_o2'))==0
              and tree.findtext('initial_conditions/cell_positions/filename')=='cells_prisma_full-section_0.75.csv'
              and tree.findtext('user_parameters/blood_source_file')=='./config/BM1/prisma_wall_drug_tube.tsv')
        check('full_section_75_percent_cells',len(cells)==3800==m['initial_cells'] and m['fill_fraction']==0.75
              and min(c[0] for c in cells)==-490 and max(c[0] for c in cells)==250
              and {c[1] for c in cells}=={c[2] for c in cells}==set(range(-70,111,20)) and all(c[3]==0 for c in cells))
        check('cells_inside_tube_not_on_ecm',not any(voxel(*c[:3]) in ecm for c in cells))
        tube=(run/'config/BM1/prisma_wall_drug_tube.tsv').read_text()
        used=[tuple(int(v) for v in l.split('\t')) for l in tube.split('\n')[1:]]
        section={voxel(0,c[1],c[2])[1:] for c in cells}
        check('tube_sources_match_cell_section',tube.startswith('x\ty\tz\n') and not tube.endswith('\n') and len(used)==len(set(used))==100
              and {u[0] for u in used}=={55} and {u[1:] for u in used}==section and m['source_voxels']==100 and m['source_footprint']=='tube')
        check('originals_untouched',sha(run/'config/BM1/cells_prisma.csv')==sha(PRISM/'BM1/cells_prisma.csv')
              and sha(run/'config/BM1/prisma_wall_drug_2.tsv')==sha(PRISM/'BM1/prisma_wall_drug_2.tsv'))
        check('generated_inputs_hashed',{m['initial_cells_csv'],'./config/BM1/prisma_wall_drug_tube.tsv'}<=set(m['input_sha256']))
        run=prepare('prism','BM0',None,None,None,1,temp,'half',None,1000,0,'full-section',None,0.5)
        m=json.loads((run/'run_manifest.json').read_text())
        check('fill_fraction_0.5_is_25_slices_front_x_minus_10',m['initial_cells']==2500 and m['source_footprint']=='original')
        own=Path(temp)/'my cells.csv';own.write_text('-470,0,0,0\n-450,0,0,0\n')
        run=prepare('prism','BM2',None,None,None,1,temp,'own_cells',None,5000,1000,'original',own)
        m=json.loads((run/'run_manifest.json').read_text())
        check('cells_file_copied',m['initial_cells']==2 and m['initial_cells_csv'].endswith('custom_my_cells.csv') and m['initial_tissue']=='custom')
        bad=Path(temp)/'bad.csv';bad.write_text('x,y,z,type\n0,0,0,0\n');outside=Path(temp)/'outside.csv';outside.write_text('900,0,0,0\n')
        invalid=[dict(smoke_minutes=.02,max_time=100),dict(max_time=0),dict(drug_time=-1),dict(initial_tissue='half-volume'),
                 dict(geometry='cylinder',initial_tissue='full-section'),dict(geometry='sphere',cells_file=own),
                 dict(initial_tissue='full-section',cells_file=own),dict(cells_file=bad),dict(cells_file=outside),
                 dict(fill_fraction=0.5),dict(initial_tissue='full-section',fill_fraction=0),dict(initial_tissue='full-section',fill_fraction=1.2),
                 dict(initial_tissue='full-section',fill_fraction=0.001),dict(geometry='cylinder',source_footprint='tube'),dict(source_footprint='shifted')]
        for i,kw in enumerate(invalid):
            geometry=kw.pop('geometry','prism')
            try:prepare(geometry,'BM0',None,None,None,1,temp,f'invalid_{i}',**kw)
            except ValueError:pass
            else:raise AssertionError(('accepted',kw))
            assert not (Path(temp)/f'invalid_{i}').exists(),('left a run folder behind',kw)
        check('invalid_tfm_options_rejected_before_creating_runs',True)
    print(json.dumps(tests,indent=2))
if __name__=='__main__':main()
