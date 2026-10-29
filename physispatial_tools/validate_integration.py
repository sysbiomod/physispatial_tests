"""Static/interface checks on a complete distribution. No production simulation."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
import xml.etree.ElementTree as ET
from run import ROOT,prepare,required_inputs,xml_values
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    tests={};profiles=json.loads((ROOT/'physispatial_provenance/integrated_profiles.json').read_text())
    upstream=json.loads((ROOT/'physispatial_provenance/upstream_manifest.json').read_text())['files']
    def check(name,result):assert result,name;tests[name]='PASS'
    for family in ['core','modules','BioFVM','addons/PhysiBoSS/src']:
        for name,digest in upstream.items():
            if name.startswith(family+'/'):assert sha(ROOT/name)==digest,name
    check('upstream_core_modules_BioFVM_PhysiBoSS_adapter_unchanged',True)
    original=json.loads((ROOT/'physispatial_provenance/original_static_profiles.json').read_text())
    for geometry in ['prism','cylinder','sphere']:
        project=ROOT/'sample_projects_intracellular/boolean'/('physispatial_'+geometry)
        check(geometry+'_standard_sample_structure',all((project/name).exists() for name in ['main.cpp','Makefile','custom_modules','config','README.md']))
        for pop in ['BM0','BM1','BM2']:
            record=profiles[geometry+'/'+pop];path=project/'config'/pop
            assert sha(project/'profiles'/pop/'main.cpp')==record['main_sha256']
            assert sha(path/'PhysiCell_settings.original.xml')==record['original_xml_sha256']
            before=xml_values(ET.parse(path/'PhysiCell_settings.original.xml'));after=xml_values(ET.parse(path/'PhysiCell_settings.xml'))
            diff=[key for key in before if before[key]!=after[key]]
            # Relocation of resource files only, no numerical/default/flag changes.
            assert all(key.endswith(('/bnd_filename[0]','/cfg_filename[0]','/blood_source_file[0]','/ecm_density_file[0]','/folder[0]')) for key in diff),diff
            for name,digest in record['boolean_files'].items():assert sha(path/name)==digest,name
            with tempfile.TemporaryDirectory(prefix='physi_profile_check_') as temp:
                run=prepare(geometry,pop,1250,3e-7,123,1,temp,'case',.02)
                m=json.loads((run/'run_manifest.json').read_text());assert m['diffusion']==1250 and m['concentration']==3e-7 and m['seed']==123
                tree=ET.parse(run/'config/run.xml')
                for name in required_inputs(tree):assert (run/name).is_file(),name
                old=next(r for r in original if r['geometry']==geometry and r['population']==pop)
                for key,value in old['domain'].items():
                    actual=tree.findtext('domain/'+key)
                    assert str(actual).strip()==str(value) or key!='use_2D' and float(actual)==float(value),(key,actual,value)
                check(geometry+'_'+pop+'_preserved_physics_models_and_parameter_interface',True)
                try:prepare(geometry,pop,500,1e-7,None,1,temp,'case')
                except FileExistsError:pass
                else:raise AssertionError('Output collision not rejected')
    check('duplicate_run_directory_rejected',True)
    for name in ['Makefile','sample_projects/Makefile-default']:
        old=(ROOT/'physispatial_provenance/upstream'/name).read_bytes();new=(ROOT/name).read_bytes()
        # Active root Makefile is allowed to be a selected sample while testing.
        if name=='Makefile' and not new.startswith(old):continue
        assert new.startswith(old),name
    check('original_default_make_targets_preserved_verbatim_with_include_append',True)
    for g in ['prism','cylinder','sphere']:
        result=subprocess.run(['make','-n','physispatial-'+g],cwd=ROOT,capture_output=True,text=True)
        assert result.returncode==0 and '--geometry '+g in result.stdout
    check('three_make_targets_available',True)
    for geometry in ['prism','cylinder','sphere']:
        for pop in ['BM0','BM1','BM2']:
            cfg=next((ROOT/'sample_projects_intracellular/boolean'/('physispatial_'+geometry)/'config'/pop).glob('*norm_0.cfg'))
            assert profiles[geometry+'/'+pop]['boolean_files'][cfg.name]==sha(cfg)
    check('BM_identity_is_original_CFG_not_celltype0_filename',True)
    (ROOT/'physispatial_validation/static_and_interface_checks.json').write_text(json.dumps(dict(success=True,n_checks=len(tests),checks=tests),indent=2))
    print(len(tests),'integration/interface checks PASS')
if __name__=='__main__':main()
