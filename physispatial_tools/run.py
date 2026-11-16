"""Prepare isolated runs or execute them; never silently overwrite outputs.

TFM options (branch tfm_rafa): --max-time (any horizon), --drug-time (minute at which
the drug sources switch on, XML user_parameters/time_remove_o2), --initial-tissue and
--fill-fraction (prism: full cross-section block from the end cap), --source-footprint
(prism: source plate aligned with the tube interior) and --cells-file (own x,y,z,type CSV).
Without these options the behaviour is identical to the original run.py."""
import argparse,csv,datetime,fcntl,hashlib,json,math,os,re,shutil,subprocess,sys,time
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
GEOMETRIES=['prism','cylinder','sphere'];POPULATIONS=['BM0','BM1','BM2']
# Prism geometry (20 micron voxels; centres at -590+20i in x and -170+20j in y,z).
# ECM tube: end cap at x=-510, walls at y,z=-90 and y,z=130, open end at x=500.
# Interior lattice: x -490..490 (50 slices), y,z -70..110 (10x10), i.e. voxels i 5..54, j,k 5..14.
# Original inputs: cells x -470..-110, y,z -70..70 (19x8x8=1216); source plate i=55 (x=510),
# j,k 4..13 (y,z -90..90), shifted 20 micron down from the tube interior. Its reader skips the
# first line (no header in the TSV), so 99 of the 100 listed voxels are used.
PRISM_INTERIOR=dict(x=range(-490,491,20),yz=range(-70,111,20));PRISM_SOURCE_X=510
INITIAL_TISSUES=['original','full-section']
CELLS_FROM_CSV=['prism','cylinder'] # the sphere generates its positions from tumor_radius
SOURCE_FOOTPRINTS=['original','tube']
def prism_tissue_rows(fill_fraction):
    """Full 10x10 cross-section block starting at the end cap (x=-490), filling the nearest
    whole number of slices to fill_fraction of the 50-slice interior (0.75 -> 38 slices, front x=250)."""
    n=math.floor(fill_fraction*len(PRISM_INTERIOR['x'])+0.5)
    if n<1:raise ValueError('fill_fraction too small: no complete slice of cells')
    yz=PRISM_INTERIOR['yz'];return [(x,y,z,0) for x in PRISM_INTERIOR['x'][:n] for y in yz for z in yz]
def prism_tube_sources(domain,dx=20):
    """Voxel indices of a source plate at x=510 covering exactly the tube interior (y,z -70..110)."""
    index=lambda v,lo:int(round((v-lo)/dx-0.5))
    return [(index(PRISM_SOURCE_X,domain[0]),index(y,domain[2]),index(z,domain[4])) for y in PRISM_INTERIOR['yz'] for z in PRISM_INTERIOR['yz']]
def effective_sources(path):
    """Distinct voxels the original C++ reader actually uses: it always skips the first line."""
    lines=[l for l in Path(path).read_text().split('\n')[1:] if l.strip()]
    return len({tuple(int(float(v)) for v in l.split('\t')[:3]) for l in lines})
def read_cells_csv(path,domain):
    """Validate an x,y,z,type CSV (no header, as the original PhysiCell loader expects)."""
    rows=[]
    with open(path,newline='') as f:
        for i,row in enumerate(csv.reader(f),1):
            if not row or not ''.join(row).strip():continue
            if len(row)<4:raise ValueError(f'{path}: line {i} needs x,y,z,type')
            try:x,y,z=(float(v) for v in row[:3]);t=int(row[3])
            except ValueError:raise ValueError(f'{path}: line {i} is not numeric x,y,z,integer type (no header allowed)')
            if not all(math.isfinite(v) for v in (x,y,z)) or t<0:raise ValueError(f'{path}: line {i} has invalid values')
            for v,lo,hi,axis in zip((x,y,z),domain[0::2],domain[1::2],'xyz'):
                if not lo<=v<=hi:raise ValueError(f'{path}: line {i}, {axis}={v} outside the domain [{lo},{hi}]')
            rows.append((x,y,z,t))
    if not rows:raise ValueError(f'{path}: no cells')
    return rows
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def xml_values(tree):
    out={}
    def visit(e,key):
        out[key]=dict(text=(e.text or '').strip(),attributes=e.attrib);counter={}
        for c in e:
            n=counter.get(c.tag,0);counter[c.tag]=n+1;visit(c,key+'/'+c.tag+f'[{n}]')
    visit(tree.getroot(),tree.getroot().tag);return out
def required_inputs(tree):
    root=tree.getroot();names=[e.text.strip() for e in root.findall('.//bnd_filename')+root.findall('.//cfg_filename')]
    for key in ['blood_source_file','ecm_density_file']:
        value=root.findtext('user_parameters/'+key)
        if value:names.append(value.strip())
    for key in ['initial_conditions/cell_positions','cell_rules']:
        node=root.find(key)
        if node is not None and node.get('enabled','false').lower()=='true':names.append(str(Path(node.findtext('folder'))/node.findtext('filename')))
    return sorted(set(names))
def prepare(geometry,population,diffusion=None,concentration=None,seed=None,threads=1,output_root=None,name=None,smoke_minutes=None,
            max_time=None,drug_time=None,initial_tissue='original',cells_file=None,fill_fraction=None,source_footprint='original'):
    if geometry not in GEOMETRIES or population not in POPULATIONS:raise ValueError('Invalid geometry/population')
    if diffusion is not None and (not math.isfinite(diffusion) or diffusion<=0):raise ValueError('D must be finite and >0')
    if concentration is not None and (not math.isfinite(concentration) or concentration<0):raise ValueError('C must be finite and >=0')
    if seed is not None and not 0<=seed<2**31:raise ValueError('Seed must be0..2^31−1')
    if not 1<=threads<=1024:raise ValueError('Invalid OpenMP thread count')
    if smoke_minutes is not None and (not math.isfinite(smoke_minutes) or not 0<=smoke_minutes<=1):raise ValueError('Smoke horizon must be0..1min')
    if smoke_minutes is not None and max_time is not None:raise ValueError('Use either --smoke-minutes or --max-time, not both')
    if max_time is not None and (not math.isfinite(max_time) or max_time<=0):raise ValueError('max_time must be finite and >0 min')
    if drug_time is not None and (not math.isfinite(drug_time) or drug_time<0):raise ValueError('drug_time must be finite and >=0 min')
    if initial_tissue not in INITIAL_TISSUES:raise ValueError('initial_tissue must be one of '+', '.join(INITIAL_TISSUES))
    if initial_tissue!='original' and geometry!='prism':raise ValueError('Initial-tissue presets exist only for the prism')
    if cells_file is not None and initial_tissue!='original':raise ValueError('Use either --initial-tissue or --cells-file, not both')
    if fill_fraction is not None and initial_tissue!='full-section':raise ValueError('--fill-fraction only applies to --initial-tissue full-section')
    if initial_tissue=='full-section':
        fill_fraction=0.75 if fill_fraction is None else fill_fraction
        if not math.isfinite(fill_fraction) or not 0<fill_fraction<=1:raise ValueError('fill_fraction must be in (0,1]')
    if source_footprint not in SOURCE_FOOTPRINTS:raise ValueError('source_footprint must be one of '+', '.join(SOURCE_FOOTPRINTS))
    if source_footprint!='original' and geometry!='prism':raise ValueError('--source-footprint applies only to the prism')
    if cells_file is not None and geometry not in CELLS_FROM_CSV:raise ValueError('The sphere generates its cells from tumor_radius; --cells-file does not apply')
    project=ROOT/'sample_projects_intracellular/boolean'/('physispatial_'+geometry)
    tree=ET.parse(project/'config'/population/'PhysiCell_settings.xml');root=tree.getroot();before=xml_values(tree)
    domain=[float(root.findtext('domain/'+k)) for k in ['x_min','x_max','y_min','y_max','z_min','z_max']]
    cell_rows=None
    if initial_tissue!='original':cell_rows=prism_tissue_rows(fill_fraction);cells_name=f'cells_prisma_{initial_tissue}_{fill_fraction:g}.csv'
    if cells_file is not None:cell_rows=read_cells_csv(cells_file,domain);cells_name='custom_'+re.sub(r'[^A-Za-z0-9_.-]','_',Path(cells_file).name)
    parent=Path(output_root or ROOT/'physispatial_runs').resolve()
    if not re.fullmatch(r'[A-Za-z0-9_/.-]+',str(parent)):raise ValueError('Original C++ shell-copy requires paths without spaces/metacharacters')
    name=name or geometry+'_'+population+'_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    if not re.fullmatch(r'[A-Za-z0-9_.+-]+',name) or name in ['.','..']:raise ValueError('Invalid run name')
    parent.mkdir(parents=True,exist_ok=True);run=parent/name;run.mkdir(exist_ok=False)
    shutil.copytree(project/'config',run/'config');(run/'output').mkdir()
    if diffusion is not None:root.find('microenvironment_setup/variable[@name="drug_A"]/physical_parameter_set/diffusion_coefficient').text=format(diffusion,'.17g')
    if concentration is not None:root.find('user_parameters/drug_conc').text=format(concentration,'.17g')
    if seed is not None:root.find('user_parameters/random_seed').text=str(seed)
    root.find('parallel/omp_num_threads').text=str(threads);root.find('save/folder').text='output'
    if smoke_minutes is not None:root.find('overall/max_time').text=format(smoke_minutes,'.17g')
    if max_time is not None:root.find('overall/max_time').text=format(max_time,'.17g')
    if drug_time is not None:root.find('user_parameters/time_remove_o2').text=format(drug_time,'.17g')
    if cell_rows is not None:
        positions=root.find('initial_conditions/cell_positions')
        if positions is None or positions.get('enabled','false').lower()!='true':raise ValueError('This configuration does not load cells from CSV')
        target=run/Path(positions.findtext('folder').strip())/cells_name
        assert not target.exists(),target
        with target.open('x',newline='') as f:csv.writer(f,lineterminator='\n').writerows(cell_rows)
        positions.find('filename').text=cells_name
    if source_footprint=='tube':
        # Header line on purpose: the original reader always skips the first line. No trailing
        # newline: its while(!eof) loop would otherwise read one empty extra line.
        source_path='./config/'+population+'/prisma_wall_drug_tube.tsv';target=run/source_path
        assert not target.exists(),target
        with target.open('x',newline='') as f:f.write('\n'.join(['x\ty\tz']+['\t'.join(map(str,v)) for v in prism_tube_sources(domain)]))
        root.find('user_parameters/blood_source_file').text=source_path
    after=xml_values(tree);changed={k:dict(before=before[k],after=after[k]) for k in before if before[k]!=after[k]}
    allowed={'PhysiCell_settings/microenvironment_setup[0]/variable[1]/physical_parameter_set[0]/diffusion_coefficient[0]',
      'PhysiCell_settings/user_parameters[0]/drug_conc[0]','PhysiCell_settings/user_parameters[0]/random_seed[0]',
      'PhysiCell_settings/parallel[0]/omp_num_threads[0]','PhysiCell_settings/save[0]/folder[0]','PhysiCell_settings/overall[0]/max_time[0]',
      'PhysiCell_settings/user_parameters[0]/time_remove_o2[0]','PhysiCell_settings/initial_conditions[0]/cell_positions[0]/filename[0]',
      'PhysiCell_settings/user_parameters[0]/blood_source_file[0]'}
    assert not set(changed)-allowed,changed
    config=run/'config/run.xml';tree.write(config,encoding='utf-8',xml_declaration=True)
    files={}
    for name in required_inputs(tree):
        p=Path(name);assert not p.is_absolute() and '..' not in p.parts
        files[name]=sha(run/p)
    horizon=float(root.findtext('overall/max_time'));activation=float(root.findtext('user_parameters/time_remove_o2'))
    if activation>=horizon and smoke_minutes is None:print(f'WARNING: drug activation at {activation:g} min is not before max_time {horizon:g} min; the drug never switches on',file=sys.stderr)
    positions=root.find('initial_conditions/cell_positions');cells_csv=None;n_cells=None
    if geometry in CELLS_FROM_CSV and positions is not None and positions.get('enabled','false').lower()=='true':
        cells_csv=str(Path(positions.findtext('folder').strip())/positions.findtext('filename').strip())
        try:n_cells=len(read_cells_csv(run/cells_csv,domain))
        except ValueError:n_cells=None # bookkeeping only; original inputs are used unchanged
    manifest=dict(geometry=geometry,population=population,source_profile='original_D500',state='PREPARED',
      diffusion=float(root.findtext('microenvironment_setup/variable[@name="drug_A"]/physical_parameter_set/diffusion_coefficient')),
      concentration=float(root.findtext('user_parameters/drug_conc')),seed=int(root.findtext('user_parameters/random_seed')),
      threads=threads,max_time=horizon,smoke=smoke_minutes is not None,drug_activation_time=activation,
      initial_tissue='custom' if cells_file is not None else initial_tissue,fill_fraction=fill_fraction,
      source_footprint=source_footprint,source_file=root.findtext('user_parameters/blood_source_file','').strip() or None,
      source_voxels=effective_sources(run/root.findtext('user_parameters/blood_source_file').strip()) if geometry=='prism' else None,
      cells_file_source=str(Path(cells_file).resolve()) if cells_file is not None else None,
      initial_cells_csv=cells_csv,initial_cells=n_cells,
      concentration_units='original numeric convention; unresolved unit labels; no conversion',
      diffusion_units='micron^2/min',changed_XML_elements=changed,input_sha256=files,run_xml_sha256=sha(config))
    (run/'run_manifest.json').write_text(json.dumps(manifest,indent=2));return run
def build(geometry,population,jobs=2):
    if not 1<=jobs<=16:raise ValueError('jobs must be1..16')
    work=ROOT/'physispatial_work';work.mkdir(exist_ok=True)
    with (work/'build.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        project=ROOT/'sample_projects_intracellular/boolean'/('physispatial_'+geometry)
        h=hashlib.sha256()
        for folder in [project,ROOT/'core',ROOT/'BioFVM',ROOT/'modules',ROOT/'addons/PhysiBoSS/src']:
            for f in sorted(folder.rglob('*')):
                if f.is_file():h.update(str(f.relative_to(ROOT)).encode());h.update(f.read_bytes())
        compiler=os.environ.get('PHYSICELL_CPP','g++');version=subprocess.check_output([compiler,'--version'],text=True).splitlines()[0]
        h.update(version.encode());h.update((ROOT/'physispatial_tools/projects.mk').read_bytes())
        tag=h.hexdigest();cache=work/'executables'/(geometry+'_'+population+'_'+tag[:16]);cache.mkdir(parents=True,exist_ok=True)
        executable=cache/('physispatial_'+geometry);record=cache/'build_manifest.json'
        if record.exists() and executable.is_file() and json.loads(record.read_text())['executable_sha256']==sha(executable):return executable
        # The normal sample loading/build path, serialized across array tasks.
        with (cache/'build.log').open('a') as log:
            subprocess.run(['make','physispatial-'+geometry,'POPULATION='+population],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
            subprocess.run(['make','-j'+str(jobs),'ARCH=x86-64','CC='+compiler],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        shutil.copy2(ROOT/('physispatial_'+geometry),executable)
        record.write_text(json.dumps(dict(geometry=geometry,population=population,source_fingerprint=tag,
           compiler=version,architecture='x86-64',MAXNODES=256,executable_sha256=sha(executable)),indent=2))
        return executable
def execute(run,jobs=2,timeout=None,memory_gb=None):
    run=Path(run).resolve();manifest_path=run/'run_manifest.json';m=json.loads(manifest_path.read_text())
    if m['state']!='PREPARED' or any((run/'output').iterdir()):raise ValueError('Refusing an already-started or nonempty run')
    assert sha(run/'config/run.xml')==m['run_xml_sha256']
    for name,digest in m['input_sha256'].items():assert sha(run/name)==digest
    executable=build(m['geometry'],m['population'],jobs)
    claim=run/'execution.claim'
    with claim.open('x') as f:f.write('This run cannot be automatically restarted.\n')
    m.update(state='RUNNING',executable_sha256=sha(executable));manifest_path.write_text(json.dumps(m,indent=2))
    env=dict(os.environ,OMP_NUM_THREADS=str(m['threads']));started=time.monotonic();cap=None
    if memory_gb is not None:
        if not math.isfinite(memory_gb) or memory_gb<=0:raise ValueError('Invalid memory cap')
        import resource
        def cap():resource.setrlimit(resource.RLIMIT_AS,(int(memory_gb*1024**3),int(memory_gb*1024**3)))
    try:
        with (run/'simulation.log').open('x') as log:
            result=subprocess.run([str(executable),'config/run.xml'],cwd=run,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout,preexec_fn=cap)
        m.update(returncode=result.returncode,state='FINISHED' if result.returncode==0 else 'FAILED')
        if result.returncode==0:
            try:
                actual=float(ET.parse(run/'output/final.xml').findtext('.//current_time'));m['final_time']=actual
                if actual<m['max_time']-1e-8:m['state']='INCOMPLETE'
            except (OSError,ET.ParseError,ValueError):m['state']='INCOMPLETE'
    except subprocess.TimeoutExpired:m.update(state='TIMEOUT',returncode=None)
    m['wall_seconds']=time.monotonic()-started;manifest_path.write_text(json.dumps(m,indent=2))
    if m['state']!='FINISHED':raise RuntimeError('Not completed: '+str(run))
    return run
def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter);p.add_argument('--geometry',choices=GEOMETRIES,required=True)
    p.add_argument('--population',choices=POPULATIONS,default='BM0');p.add_argument('--diffusion',type=float);p.add_argument('--concentration',type=float)
    p.add_argument('--seed',type=int);p.add_argument('--threads',type=int,default=1);p.add_argument('--output-root');p.add_argument('--name')
    p.add_argument('--prepare-only',action='store_true');p.add_argument('--smoke-minutes',type=float,help='short test horizon, 0..1 min')
    p.add_argument('--timeout',type=float);p.add_argument('--memory-gb',type=float);p.add_argument('--jobs',type=int,default=2)
    t=p.add_argument_group('TFM options')
    t.add_argument('--max-time',type=float,help='simulated horizon in min (overall/max_time); default: original 300000')
    t.add_argument('--drug-time',type=float,help='minute at which drug sources switch on (user_parameters/time_remove_o2); 0 = from the start; default: original (35000 prism, 30000 cylinder/sphere)')
    t.add_argument('--initial-tissue',choices=INITIAL_TISSUES,default='original',help='prism only: original (1216 cells, x -470..-110, y,z -70..70) or full-section (10x10 section y,z -70..110, from the end cap at x=-490; length set by --fill-fraction)')
    t.add_argument('--fill-fraction',type=float,help='with full-section: fraction of the tube interior filled, rounded to whole 20 micron slices; default 0.75 (38 slices, 3800 cells, front at x=250)')
    t.add_argument('--source-footprint',choices=SOURCE_FOOTPRINTS,default='original',help='prism only: original (y,z -90..90, 99 voxels used) or tube (y,z -70..110, all 100 voxels used, matching the tube interior)')
    t.add_argument('--cells-file',help='prism/cylinder: own CSV with x,y,z,type per line (micron, no header); copied into the run')
    a=p.parse_args()
    try:
        run=prepare(a.geometry,a.population,a.diffusion,a.concentration,a.seed,a.threads,a.output_root,a.name,a.smoke_minutes,
                    a.max_time,a.drug_time,a.initial_tissue,a.cells_file,a.fill_fraction,a.source_footprint)
        print(run,flush=True)
        if not a.prepare_only:execute(run,a.jobs,a.timeout,a.memory_gb)
    except (ValueError,AssertionError,RuntimeError,OSError,subprocess.CalledProcessError) as error:p.exit(1,str(error)+'\n')
if __name__=='__main__':main()
