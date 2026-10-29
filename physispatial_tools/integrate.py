"""One-time integration from checksum-verified recovered MN5 sources. Not a simulator."""
import datetime,difflib,hashlib,json,shutil,subprocess
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT.parent/'PhysiSpatial-Geometry-Tests'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=ROOT/'physispatial_provenance';p.mkdir(exist_ok=True)
    (p/'upstream').mkdir(exist_ok=True);(ROOT/'physispatial_validation').mkdir(exist_ok=True)
    upstream={}
    for f in ROOT.rglob('*'):
        if f.is_file() and '.git' not in f.parts and not f.relative_to(ROOT).parts[0].startswith('physispatial_'):
            upstream[str(f.relative_to(ROOT))]=sha(f)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if not (p/'upstream_manifest.json').exists():
        (p/'upstream_manifest.json').write_text(json.dumps(dict(repository='https://github.com/PhysiBoSS/PhysiBoSS',tag='v2.2.3',commit=commit,files=upstream),indent=2))
    for name in ['Makefile','README.md','sample_projects/Makefile-default']:
        target=p/'upstream'/name;target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():shutil.copy2(ROOT/name,target)
    for name in ['original_manifest.json','recovery_catalog.json']:
        shutil.copy2(OLD/'provenance'/name,p/name)
    shutil.copy2(OLD/'validation/static_profiles.json',p/'original_static_profiles.json')
    shutil.copy2(OLD/'validation/remote_original_integrity.json',p/'previous_remote_original_integrity.json')
    engine=OLD/'src/vendor/41f348acd1fbc384/addons/PhysiBoSS/MaBoSS'
    if not (ROOT/'addons/PhysiBoSS/MaBoSS').exists():shutil.copytree(engine,ROOT/'addons/PhysiBoSS/MaBoSS')
    profiles=json.loads((p/'recovery_catalog.json').read_text())['profiles'];recovered={};changes=[]
    for geometry in ['prism','cylinder','sphere']:
        project=ROOT/'sample_projects_intracellular/boolean'/('physispatial_'+geometry)
        if project.exists():
            backup=ROOT/'physispatial_work/integration_revisions'/datetime.datetime.now().strftime('%Y%m%dT%H%M%S%f')
            backup.mkdir(parents=True);shutil.move(str(project),str(backup/project.name))
        project.mkdir(exist_ok=False);(project/'custom_modules').mkdir();(project/'config').mkdir();(project/'profiles').mkdir()
        for population in ['BM0','BM1','BM2']:
            source=OLD/'geometries'/geometry/'original'/population;meta=profiles[geometry+'/'+population]
            for name,info in meta['science'].items():assert sha(source/name)==info['sha256'],source/name
            for name,info in meta['config'].items():assert sha(source/name)==info['sha256'],source/name
            popdir=project/'profiles'/population;popdir.mkdir();shutil.copy2(source/'main.cpp',popdir/'main.cpp')
            if population=='BM0':
                shutil.copy2(source/'main.cpp',project/'main.cpp')
                for f in (source/'custom_modules').iterdir():
                    if f.is_file():shutil.copy2(f,project/'custom_modules'/f.name)
            else:
                for f in (source/'custom_modules').iterdir():
                    if f.is_file():assert f.read_bytes()==(project/'custom_modules'/f.name).read_bytes(),'Unexpected population-dependent custom code'
            config=project/'config'/population;config.mkdir()
            original=source/'config/PhysiCell_settings_0.xml';tree=ET.parse(original);root=tree.getroot()
            shutil.copy2(original,config/'PhysiCell_settings.original.xml')
            references=[]
            for e in root.findall('.//bnd_filename')+root.findall('.//cfg_filename'):
                old=e.text.strip();basename=Path(old).name
                shutil.copy2(source/old,config/basename);e.text='./config/'+population+'/'+basename
                references.append((old,e.text))
            for field in ['blood_source_file','ecm_density_file']:
                e=root.find('user_parameters/'+field)
                if e is None:continue
                old=e.text.strip();basename=Path(old).name;shutil.copy2(source/old,config/basename)
                e.text='./config/'+population+'/'+basename;references.append((old,e.text))
            cell=root.find('initial_conditions/cell_positions')
            # Keep even disabled/redundant inputs if named by the original XML.
            if cell is not None:
                folder=cell.find('folder');filename=cell.findtext('filename')
                originalfile=source/str(Path(folder.text.strip())/filename)
                if originalfile.is_file():shutil.copy2(originalfile,config/filename)
                folder.text='./config/'+population
            rules=root.find('cell_rules')
            if rules is not None and rules.find('folder') is not None:
                f=source/str(Path(rules.findtext('folder').strip())/rules.findtext('filename'))
                if f.is_file():shutil.copy2(f,config/f.name)
                rules.find('folder').text='./config/'+population
            tree.write(config/'PhysiCell_settings.xml',encoding='utf-8',xml_declaration=True)
            recovered[geometry+'/'+population]=dict(original_source=meta['source_path'],framework_id=meta['framework_id'],
                main_sha256=sha(popdir/'main.cpp'),original_xml_sha256=sha(original),
                portable_xml_sha256=sha(config/'PhysiCell_settings.xml'),path_adaptations=references,
                default_D=float(root.findtext('microenvironment_setup/variable[@name="drug_A"]/physical_parameter_set/diffusion_coefficient')),
                default_C=float(root.findtext('user_parameters/drug_conc')),boolean_files={f.name:sha(f) for f in config.glob('*') if f.suffix in ['.bnd','.cfg']})
        shutil.copy2(project/'config/BM0/PhysiCell_settings.xml',project/'config/PhysiCell_settings.xml')
        vendor=OLD/'src/vendor'/profiles[geometry+'/BM0']['framework_id'];overrides=[]
        for family in ['core','BioFVM','modules','addons/PhysiBoSS/src']:
            for f in (vendor/family).rglob('*'):
                if f.is_file() and f.suffix in ['.cpp','.h']:
                    rel=f.relative_to(vendor);assert (ROOT/rel).is_file(),rel
                    if f.read_bytes()!=(ROOT/rel).read_bytes():
                        assert f.suffix=='.cpp','A header override requires explicit review'
                        dest=project/'custom_modules'/('historical_'+f.name);shutil.copy2(f,dest)
                        overrides.append((str(rel),str(dest.relative_to(project))))
                        patch=''.join(difflib.unified_diff((ROOT/rel).read_text().splitlines(True),f.read_text().splitlines(True),fromfile='upstream/'+str(rel),tofile=geometry+'/'+str(rel)))
                        (p/(geometry+'_'+f.name+'.patch')).write_text(patch)
                        changes.append(dict(geometry=geometry,upstream_path=str(rel),upstream_sha256=sha(ROOT/rel),historical_sha256=sha(f),compiled_from=str(dest.relative_to(ROOT))))
        # Base is the ORIGINAL geometry Makefile. Only plumbing/build portability changes.
        make=(OLD/'geometries'/geometry/'original/BM0/Makefile').read_text()
        make=make.replace('PROGRAM_NAME := project','PROGRAM_NAME := physispatial_'+geometry)
        import re
        make=re.sub(r'^PROGRAM_NAME := .*$', 'PROGRAM_NAME := physispatial_'+geometry,make,flags=re.M)
        for original,override in overrides:
            objectname=Path(original).stem+'.o'
            old=objectname+': ./'+original+'\n\t$(COMPILE_COMMAND) -c ./'+original
            new=objectname+': ./'+override+'\n\t$(COMPILE_COMMAND) -I./'+str(Path(original).parent)+' -c ./'+override+' -o '+objectname
            assert old in make,(geometry,original);make=make.replace(old,new)
        # Header existence is NOT sufficient to prove the static library was built.
        make+='''\n# PhysiSpatial: offline, bundled MaBoSS build; does not call the download helper.\nMABOSS_STATIC := $(MABOSS_DIR)/lib/libMaBoSS_$(MABOSS_MAX_NODES)n-static.a\nall static: $(MABOSS_STATIC)\n$(MABOSS_STATIC):\n\ttouch $(MABOSS_DIR)/src/depend.mk\n\t$(MAKE) -C $(MABOSS_DIR)/src -f Makefile.maboss MAXNODES=$(MABOSS_MAX_NODES) CXX=$(CC) init\n\t$(MAKE) -C $(MABOSS_DIR)/src -f Makefile.maboss MAXNODES=$(MABOSS_MAX_NODES) CXX=$(CC) libMaBoSS_$(MABOSS_MAX_NODES)n-static.a\n\tmkdir -p $(MABOSS_DIR)/lib\n\tcp $(MABOSS_DIR)/src/libMaBoSS_$(MABOSS_MAX_NODES)n-static.a $@\n\n-include physispatial_tools/projects.mk\n'''
        # Original reset removes flat custom_modules files safely (no new subdirectories).
        make+='\n# Prevent variant objects leaking into an upstream sample after standard reset.\nreset: clean\n'
        (project/'Makefile').write_text(make)
    for name in ['Makefile','sample_projects/Makefile-default']:
        with (ROOT/name).open('a') as f:f.write('\n# Additional projects; original targets above are unchanged.\n-include physispatial_tools/projects.mk\n')
    (p/'integrated_profiles.json').write_text(json.dumps(recovered,indent=2))
    (p/'framework_differences.json').write_text(json.dumps(changes,indent=2))
    protected={}
    for f in OLD.rglob('*'):
        if f.is_file() and '.git' not in f.parts and '__pycache__' not in f.parts and f.suffix not in ['.o','.a'] and not f.relative_to(OLD).parts[0] in ['build','runs']:
            s=f.stat();protected[str(f)]=dict(size=s.st_size,mtime_ns=s.st_mtime_ns,sha256=sha(f))
    (p/'protected_predecessor_manifest.json').write_text(json.dumps(protected,indent=2))
    shutil.copy2('/home/amadrid/.codex/attachments/a8f97d6a-db2c-4751-ac57-982cec42198e/Pasted text.txt',p/'TASK_REQUEST.txt')
    print('Integrated9 original profiles into full PhysiBoSS',commit)
if __name__=='__main__':main()
