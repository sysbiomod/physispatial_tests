"""Load an original geometry like a conventional PhysiBoSS sample project."""
import argparse,datetime,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def select(geometry,population):
    project=ROOT/'sample_projects_intracellular/boolean'/('physispatial_'+geometry)
    # Match normal sample loading (four components); preserve previous working files.
    # No simulation outputs are removed and core/BioFVM/modules are NEVER rewritten.
    previous=ROOT/'physispatial_work/backups'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    previous.mkdir(parents=True,exist_ok=False)
    for name in ['main.cpp','Makefile','custom_modules','config']:
        target=ROOT/name
        if target.exists():shutil.move(str(target),str(previous/name))
    shutil.copy2(project/'profiles'/population/'main.cpp',ROOT/'main.cpp')
    shutil.copy2(project/'Makefile',ROOT/'Makefile')
    shutil.copytree(project/'custom_modules',ROOT/'custom_modules')
    shutil.copytree(project/'config',ROOT/'config')
    shutil.copy2(project/'config'/population/'PhysiCell_settings.xml',ROOT/'config/PhysiCell_settings.xml')
    # Standard reset expects this backup XML, including in historical makefiles.
    shutil.copy2(ROOT/'config/PhysiCell_settings.xml',ROOT/'config/PhysiCell_settings-backup.xml')
    # Never reuse objects from a different geometry/compiler variant. Move, do not delete.
    for obj in ROOT.glob('*.o'):shutil.move(str(obj),str(previous/obj.name))
    for exe in ['physispatial_prism','physispatial_cylinder','physispatial_sphere']:
        if (ROOT/exe).is_file():shutil.move(str(ROOT/exe),str(previous/exe))
    selection=dict(geometry=geometry,population=population,project=str(project.relative_to(ROOT)),backup=str(previous.relative_to(ROOT)))
    (ROOT/'physispatial_work/active_project.json').write_text(json.dumps(selection,indent=2))
    print('Loaded',geometry,population,'from',project.relative_to(ROOT));print('Compile: make -j2 ARCH=x86-64')
    print('Run (original long horizon): ./physispatial_'+geometry+' config/PhysiCell_settings.xml')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--geometry',choices=['prism','cylinder','sphere'],required=True)
    p.add_argument('--population',choices=['BM0','BM1','BM2'],default='BM0');a=p.parse_args();select(a.geometry,a.population)
if __name__=='__main__':main()
