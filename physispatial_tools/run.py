"""Prepare isolated runs or execute them; never silently overwrite outputs."""
import argparse,datetime,fcntl,hashlib,json,math,os,re,shutil,subprocess,time
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
GEOMETRIES=['prism','cylinder','sphere'];POPULATIONS=['BM0','BM1','BM2']
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
def prepare(geometry,population,diffusion=None,concentration=None,seed=None,threads=1,output_root=None,name=None,smoke_minutes=None):
    if geometry not in GEOMETRIES or population not in POPULATIONS:raise ValueError('Invalid geometry/population')
    if diffusion is not None and (not math.isfinite(diffusion) or diffusion<=0):raise ValueError('D must be finite and >0')
    if concentration is not None and (not math.isfinite(concentration) or concentration<0):raise ValueError('C must be finite and >=0')
    if seed is not None and not 0<=seed<2**31:raise ValueError('Seed must be0..2^31−1')
    if not 1<=threads<=1024:raise ValueError('Invalid OpenMP thread count')
    if smoke_minutes is not None and (not math.isfinite(smoke_minutes) or not 0<=smoke_minutes<=1):raise ValueError('Smoke horizon must be0..1min')
    project=ROOT/'sample_projects_intracellular/boolean'/('physispatial_'+geometry)
    parent=Path(output_root or ROOT/'physispatial_runs').resolve()
    if not re.fullmatch(r'[A-Za-z0-9_/.-]+',str(parent)):raise ValueError('Original C++ shell-copy requires paths without spaces/metacharacters')
    name=name or geometry+'_'+population+'_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    if not re.fullmatch(r'[A-Za-z0-9_.+-]+',name) or name in ['.','..']:raise ValueError('Invalid run name')
    parent.mkdir(parents=True,exist_ok=True);run=parent/name;run.mkdir(exist_ok=False)
    shutil.copytree(project/'config',run/'config');(run/'output').mkdir()
    tree=ET.parse(project/'config'/population/'PhysiCell_settings.xml');root=tree.getroot();before=xml_values(tree)
    if diffusion is not None:root.find('microenvironment_setup/variable[@name="drug_A"]/physical_parameter_set/diffusion_coefficient').text=format(diffusion,'.17g')
    if concentration is not None:root.find('user_parameters/drug_conc').text=format(concentration,'.17g')
    if seed is not None:root.find('user_parameters/random_seed').text=str(seed)
    root.find('parallel/omp_num_threads').text=str(threads);root.find('save/folder').text='output'
    if smoke_minutes is not None:root.find('overall/max_time').text=format(smoke_minutes,'.17g')
    after=xml_values(tree);changed={k:dict(before=before[k],after=after[k]) for k in before if before[k]!=after[k]}
    allowed={'PhysiCell_settings/microenvironment_setup[0]/variable[1]/physical_parameter_set[0]/diffusion_coefficient[0]',
      'PhysiCell_settings/user_parameters[0]/drug_conc[0]','PhysiCell_settings/user_parameters[0]/random_seed[0]',
      'PhysiCell_settings/parallel[0]/omp_num_threads[0]','PhysiCell_settings/save[0]/folder[0]','PhysiCell_settings/overall[0]/max_time[0]'}
    assert not set(changed)-allowed,changed
    config=run/'config/run.xml';tree.write(config,encoding='utf-8',xml_declaration=True)
    files={}
    for name in required_inputs(tree):
        p=Path(name);assert not p.is_absolute() and '..' not in p.parts
        files[name]=sha(run/p)
    manifest=dict(geometry=geometry,population=population,source_profile='original_D500',state='PREPARED',
      diffusion=float(root.findtext('microenvironment_setup/variable[@name="drug_A"]/physical_parameter_set/diffusion_coefficient')),
      concentration=float(root.findtext('user_parameters/drug_conc')),seed=int(root.findtext('user_parameters/random_seed')),
      threads=threads,max_time=float(root.findtext('overall/max_time')),smoke=smoke_minutes is not None,
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
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--geometry',choices=GEOMETRIES,required=True)
    p.add_argument('--population',choices=POPULATIONS,default='BM0');p.add_argument('--diffusion',type=float);p.add_argument('--concentration',type=float)
    p.add_argument('--seed',type=int);p.add_argument('--threads',type=int,default=1);p.add_argument('--output-root');p.add_argument('--name')
    p.add_argument('--prepare-only',action='store_true');p.add_argument('--smoke-minutes',type=float);p.add_argument('--timeout',type=float)
    p.add_argument('--memory-gb',type=float);p.add_argument('--jobs',type=int,default=2);a=p.parse_args()
    try:
        run=prepare(a.geometry,a.population,a.diffusion,a.concentration,a.seed,a.threads,a.output_root,a.name,a.smoke_minutes)
        print(run,flush=True)
        if not a.prepare_only:execute(run,a.jobs,a.timeout,a.memory_gb)
    except (ValueError,AssertionError,RuntimeError,OSError,subprocess.CalledProcessError) as error:p.exit(1,str(error)+'\n')
if __name__=='__main__':main()
