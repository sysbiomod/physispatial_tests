"""Prepare a Cartesian D/C/seed grid, or run ONE explicit index. Never submits jobs."""
import argparse,itertools,json
from pathlib import Path
from run import prepare,execute,ROOT,GEOMETRIES,POPULATIONS
def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('prepare');q.add_argument('--geometry',choices=GEOMETRIES,required=True)
    q.add_argument('--diffusions',type=float,nargs='+',required=True);q.add_argument('--concentrations',type=float,nargs='+',required=True)
    q.add_argument('--populations',choices=POPULATIONS,nargs='+',default=['BM0']);q.add_argument('--seeds',type=int,nargs='+',required=True)
    q.add_argument('--threads',type=int,default=8);q.add_argument('--directory',required=True)
    q=sub.add_parser('run');q.add_argument('--directory',required=True);q.add_argument('--index',type=int,required=True)
    q.add_argument('--jobs',type=int,default=2);q.add_argument('--timeout',type=float)
    a=p.parse_args();dest=Path(a.directory).resolve()
    if a.command=='prepare':
        combinations=list(itertools.product(a.populations,a.diffusions,a.concentrations,a.seeds))
        if not combinations:raise ValueError('Empty sweep')
        # Validate every parameter before allocating the sweep directory.
        import math
        if any(not math.isfinite(d) or d<=0 for d in a.diffusions) or any(not math.isfinite(c) or c<0 for c in a.concentrations):raise ValueError('Invalid D/C')
        if any(not 0<=s<2**31 for s in a.seeds):raise ValueError('Invalid seed')
        dest.mkdir(parents=True,exist_ok=False);runs=[]
        for i,(pop,d,c,seed) in enumerate(combinations):
            run=prepare(a.geometry,pop,d,c,seed,a.threads,dest,f'run_{i:05d}')
            runs.append(dict(index=i,path=run.name,geometry=a.geometry,population=pop,D=d,C=c,seed=seed))
        (dest/'sweep.json').write_text(json.dumps(runs,indent=2));print('Prepared only:',len(runs),'runs in',dest)
    else:
        rows=json.loads((dest/'sweep.json').read_text())
        if not 0<=a.index<len(rows):raise ValueError('Index outside sweep')
        row=rows[a.index];assert Path(row['path']).name==row['path']
        execute(dest/row['path'],a.jobs,a.timeout)
if __name__=='__main__':main()
