#!/usr/bin/env python3
"""Serial, resumable execution and discrete-result comparison. Standard library only.

The ledger records measurements, not hashes or environment fingerprints.
Each child has a 44-second wall deadline. Campaign children additionally pin one
CPU and enforce a 3 GiB address-space / 40-second CPU limit internally.
"""
import argparse,csv,json,os,resource,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def jobs():
    out=[]
    def add(label,module,*args):out.append((label,['-m',module,*map(str,args)]))
    out.append(('unit-tests',['-m','unittest','discover','-s','tests','-v']))
    out.append(('running-example',['example.py']))
    for filename in ['pilot.py','sparse_pilot.py','laminar_pilot.py']:
        out.append((filename[:-3],[filename]))
    for m,n in [(1,1),(1,4),(2,2),(2,3),(3,2),(3,3),(3,4),(4,3),(4,4)]:
        add(f'width-{m}-{n}','provenance.campaign','exact',m,n)
    for n in [32,128,512,2048]:add(f'baseline-{n}','provenance.campaign','bench',n)
    for n in [8192,32768]:add(f'baseline-scale-{n}','provenance.campaign','scale',n)
    add('baseline-stream','provenance.campaign','stream',0,24)
    add('baseline-replay','provenance.campaign','replay','@OUT@/stream_0_24_events.jsonl')
    add('coefficient-controls','provenance.campaign','mutations')
    add('shared-circuit','provenance.campaign','dag')
    for start in range(0,65536,8192):
        add(f'weighted-4-4-{start}','provenance.hierarchy_campaign','exact',4,4,start,8192,0)
    for tree in range(15):
        add(f'weighted-4-3-tree-{tree}','provenance.hierarchy_campaign','exact',4,3,0,4096,tree)
    add('laminar-boundary','provenance.hierarchy_campaign','boundary')
    for height in range(1,9):
        for weight in [16,1024]:add(f'height-{height}-{weight}','provenance.hierarchy_campaign','gap',height,weight)
    for n in [32,128,512,2048]:
        for family in ['empty','diagonal','row','column','band','cluster','random']:
            add(f'hierarchical-{n}-{family}','provenance.hierarchy_campaign','bench',n,family)
    for n in [8192,32768]:add(f'hierarchical-scale-{n}','provenance.hierarchy_campaign','scale',n)
    add('certificate-controls','provenance.hierarchy_campaign','mutations')
    add('hierarchical-stream','provenance.hierarchy_campaign','stream')
    add('hierarchical-replay','provenance.hierarchy_campaign','replay','@OUT@/hierarchy_stream_events.jsonl')
    return out


def normalized_json(x):
    ignored={'cpu_seconds','wall_seconds','peak_rss_kib','elapsed_seconds','compile_seconds','certificate_seconds'}
    if isinstance(x,dict):return {k:normalized_json(v) for k,v in x.items() if k not in ignored and not (k.endswith('_seconds') or k.endswith('_ns'))}
    if isinstance(x,list):return [normalized_json(v) for v in x]
    return x


def compare(out):
    compared=[];failures=[];missing=[]
    for f in sorted(out.iterdir()):
        if f.name in {'run-ledger.csv','comparison.json'} or f.is_dir():continue
        expected=ROOT/'results'/f.name
        if not expected.exists():missing.append(f.name);continue
        if f.suffix=='.csv':
            def discrete(path):
                rows=list(csv.DictReader(path.open()))
                return [{k:v for k,v in row.items() if not (k.endswith('_seconds') or k.endswith('_ns'))} for row in rows]
            ok=discrete(f)==discrete(expected)
        elif f.suffix=='.json':ok=normalized_json(json.loads(f.read_text()))==normalized_json(json.loads(expected.read_text()))
        elif f.suffix=='.jsonl':ok=f.read_text()==expected.read_text()
        else:continue
        compared.append(f.name)
        if not ok:failures.append(f.name)
    retained_missing=[]
    generated={f.name for f in out.iterdir() if f.is_file()}
    for expected in sorted((ROOT/'results').iterdir()):
        if expected.is_file() and expected.suffix in {'.csv','.json','.jsonl'} and expected.name not in generated:
            retained_missing.append(expected.name)
    report={'compared_files':len(compared),'discrete_mismatches':failures,
            'new_files_without_retained_counterpart':missing,
            'retained_files_without_reproduced_counterpart':retained_missing,
            'timings_compared_for_equality':False}
    (out/'comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))
    return not failures and not missing and not retained_missing


def child_limits():
    if hasattr(os,'sched_setaffinity'):
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU,(40,45))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--next',type=int,default=1)
    ap.add_argument('--out',default='reproduction-results');ap.add_argument('--list',action='store_true')
    ap.add_argument('--compare',action='store_true');a=ap.parse_args()
    if a.next<1:ap.error('--next must be positive')
    sequence=jobs()
    if a.list:
        for i,(label,cmd) in enumerate(sequence):print(i,label,' '.join(cmd))
        return
    out=(ROOT/a.out).resolve();out.mkdir(parents=True,exist_ok=True)
    if a.compare:raise SystemExit(0 if compare(out) else 1)
    ledger=out/'run-ledger.csv';records=list(csv.DictReader(ledger.open())) if ledger.exists() else []
    completed={x['label'] for x in records if x['exit_code']=='0'}
    remaining=[x for x in sequence if x[0] not in completed]
    for label,args in remaining[:a.next]:
        args=[s.replace('@OUT@',str(out)) for s in args]
        if (len(args)>1 and args[1] in {'provenance.campaign','provenance.hierarchy_campaign'}) or args[0] in {'pilot.py','sparse_pilot.py','laminar_pilot.py'}:args+=['--out',str(out)]
        cmd=[sys.executable,*args]
        before=resource.getrusage(resource.RUSAGE_CHILDREN);t=time.perf_counter()
        try:
            cp=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=44,preexec_fn=child_limits)
            code=cp.returncode;log=cp.stdout+cp.stderr
        except subprocess.TimeoutExpired as exc:
            code=124;log='Wall timeout after 44 seconds.\n'
        after=resource.getrusage(resource.RUSAGE_CHILDREN)
        row={'label':label,'exit_code':code,'wall_seconds':time.perf_counter()-t,
             'child_cpu_seconds':after.ru_utime+after.ru_stime-before.ru_utime-before.ru_stime,
             'cumulative_child_peak_rss_kib':after.ru_maxrss,'workers':1}
        records.append(row)
        (out/'logs').mkdir(exist_ok=True);(out/'logs'/(label+'.txt')).write_text(log)
        with ledger.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(row));w.writeheader();w.writerows(records)
        print(json.dumps(row),flush=True)
        if code:raise SystemExit(code)
    done=len(completed)+min(a.next,len(remaining))
    print(f'Completed {done}/{len(sequence)} jobs; repeat --next to resume.',flush=True)
if __name__=='__main__':main()
