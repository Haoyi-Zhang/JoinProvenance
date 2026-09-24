"""Bounded, resumable evidence campaign. No network or third-party packages."""
from __future__ import annotations
import argparse, csv, json, math, os, random, resource, statistics, time
from collections import Counter
from pathlib import Path
from .rectangles import *
from .engine import TupleRecord
from .regions import RegionEngine

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results'


def limits():
    if hasattr(os,'sched_setaffinity'):
        os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    if hasattr(resource,'RLIMIT_AS'):
        cap = 3*1024**3
        old = resource.getrlimit(resource.RLIMIT_AS)
        maximum = cap if old[1] == resource.RLIM_INFINITY else min(cap,old[1])
        resource.setrlimit(resource.RLIMIT_AS,(maximum,maximum))
    resource.setrlimit(resource.RLIMIT_CPU,(40,45))


def save_csv(path,rows,fields=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields or list(rows[0]))
        writer.writeheader();writer.writerows(rows)


def exact(m,n):
    positive,boolean=all_optima(m,n)
    full={(i,j) for i in range(m) for j in range(n)}
    rows=[]; mismatches=0
    for mask in range(1 << (m*n)):
        pending=set(mask_pairs(mask,m,n));emitted=full-pending
        blocks=sparse_complement(tuple(range(m)),tuple(range(n)),emitted)
        expanded=polynomial(blocks)
        assert expanded==Counter({p:1 for p in pending})
        rank=rational_rank(mask,m,n)
        rp=len(row_partition(pending));sp=len(blocks)
        assert rank<=positive[mask]<=min(rp,m,n)
        assert boolean[mask]<=positive[mask]
        d=len({i for i,j in emitted}); e=len(emitted)
        h=(d-1).bit_length() if d else 0
        w=sum(b.memberships for b in blocks)
        assert sp <= (2*d if d else 1)
        assert w<=m+2*n+(d+2*e)*h
        rows.append({'mask':mask,'pending':mask.bit_count(),'emitted':e,'positive_width':positive[mask],
                     'boolean_width':boolean[mask],'rational_rank':rank,'row_width':rp,
                     'sparse_width':sp,'sparse_memberships':w})
    save_csv(OUT/f'exact_{m}x{n}.csv',rows)
    return {'m':m,'n':n,'masks':len(rows),'mismatches':mismatches,
            'boolean_gap_cases':sum(x['boolean_width']<x['positive_width'] for x in rows),
            'rank_gap_cases':sum(x['rational_rank']<x['positive_width'] for x in rows),
            'row_suboptimal_cases':sum(x['row_width']>x['positive_width'] for x in rows),
            'sparse_suboptimal_cases':sum(x['sparse_width']>x['positive_width'] for x in rows)}


def frontier(family,n,seed):
    rng=random.Random(seed)
    if family=='empty': return []
    if family=='diagonal': return [(i,i) for i in range(n)]
    if family=='row': return [(0,j) for j in range(n)]
    if family=='column': return [(i,0) for i in range(n)]
    if family=='band': return [(i,(i+d)%n) for i in range(n) for d in (0,1)]
    if family=='cluster':
        side=math.ceil(math.sqrt(n))
        return [(i//side,i%side) for i in range(n)]
    if family=='random':
        return [(x//n,x%n) for x in sorted(rng.sample(range(n*n),n))]
    raise ValueError('unknown family')


def bench(n, *, scale_only=False):
    rows=[]
    families=['diagonal'] if scale_only else ['empty','diagonal','row','column','band','cluster','random']
    source=[]
    for family in families:
        for seed in [101,202,303]:
            emitted=frontier(family,n,seed)
            source.append({'family':family,'n':n,'seed':seed,'emitted':emitted})
            emitted_set=set(emitted)
            a=tuple(range(n));b=tuple(range(n))
            methods=['sparse'] if scale_only else ['row','sparse']
            for repeat in range(3):
                # Alternate order to reduce a fixed order/cache confound.
                for method in (methods if repeat%2==0 else list(reversed(methods))):
                    fn=sparse_complement if method=='sparse' else row_complement
                    t=time.perf_counter_ns();c=time.process_time_ns()
                    blocks=fn(a,b,emitted)
                    cpu=time.process_time_ns()-c;elapsed=time.perf_counter_ns()-t
                    pairs=sum(len(x.left)*len(x.right) for x in blocks)
                    assert pairs==n*n-len(emitted)
                    if n<=128:
                        assert polynomial(blocks)==Counter({(i,j):1 for i in a for j in b if (i,j) not in emitted_set})
                    if repeat==0:
                        verify_partition_bits(a,b,emitted,blocks)
                    rows.append({'n':n,'family':family,'seed':seed,'repeat':repeat,'method':method,
                                 'emitted':len(emitted),'blocks':len(blocks),
                                 'memberships':sum(x.memberships for x in blocks),
                                 'covered_pairs':pairs,'cpu_ns':cpu,'wall_ns':elapsed})
                    del blocks
    name=f'scale_{n}' if scale_only else f'bench_{n}'
    save_csv(OUT/(name+'.csv'),rows)
    # Exact inputs, not an external generator or a seed alone.
    with (OUT/(name+'_inputs.jsonl')).open('w') as f:
        for item in source:f.write(json.dumps(item,separators=(',',':'))+'\n')
    return {'n':n,'records':len(rows),'families':families,'mismatches':0}


def stream(seed_start,seed_count):
    results=[]; events=[]
    for seed in range(seed_start,seed_start+seed_count):
        for drift in [0,1,2,4]:
            rng=random.Random(10000+seed*31+drift)
            engine=RegionEngine();sink=Counter();transitions=0;max_regions=0;max_mem=0
            engine.insert_epoch([TupleRecord(i,i%3,0) for i in range(6)],
                                [TupleRecord(i,i%3,0) for i in range(6)],12)
            engine.check(sink);transitions+=1
            nextleft=nextright=6
            prefix={'seed':seed,'drift':drift}
            events.append(dict(prefix,event='initialize',left=[[i,i%3,0] for i in range(6)],right=[[i,i%3,0] for i in range(6)]))
            for epoch in range(16):
                left=[];right=[]
                for _ in range(rng.randrange(drift+1)):
                    key=rng.randrange(3)
                    if rng.randrange(2):
                        left.append(TupleRecord(nextleft,key,0));nextleft+=1
                    else:
                        right.append(TupleRecord(nextright,key,0));nextright+=1
                engine.insert_epoch(left,right,drift);engine.check(sink);transitions+=1
                events.append(dict(prefix,event='insert',epoch=epoch,left=[[x.identity,x.key,x.value] for x in left],right=[[x.identity,x.key,x.value] for x in right]))
                for _ in range(rng.randrange(4)):
                    pairs=sorted(engine.pending())
                    if pairs:
                        pair=rng.choice(pairs);sink[engine.emit(pair)]+=1;engine.check(sink);transitions+=1
                        events.append(dict(prefix,event='emit',pair=pair))
                method=['sparse','row','column'][(epoch+seed)%3]
                old=engine.pending();engine.migrate(method)
                assert engine.pending()==old
                engine.check(sink);transitions+=1
                events.append(dict(prefix,event='migrate',method=method))
                max_regions=max(max_regions,len(engine.regions))
                max_mem=max(max_mem,sum(r.block.memberships for r in engine.regions))
            for pair in sorted(engine.pending()):
                sink[engine.emit(pair)]+=1
            engine.check(sink);transitions+=1
            assert sink==engine.reference()
            events.append(dict(prefix,event='drain'))
            results.append(dict(prefix,epochs=16,transitions=transitions,left=len(engine.left),right=len(engine.right),
                                output_terms=len(sink),max_regions=max_regions,max_memberships=max_mem,mismatches=0))
    name=f'stream_{seed_start}_{seed_count}'
    save_csv(OUT/(name+'.csv'),results)
    with (OUT/(name+'_events.jsonl')).open('w') as f:
        for item in events:f.write(json.dumps(item,separators=(',',':'))+'\n')
    return {'traces':len(results),'transitions':sum(r['transitions'] for r in results),'mismatches':0}


def replay(path):
    engines={};sinks={};checks=0
    for line in path.read_text().splitlines():
        event=json.loads(line);key=(event['seed'],event['drift'])
        if event['event']=='initialize':
            engines[key]=RegionEngine();sinks[key]=Counter()
        e=engines[key];s=sinks[key]
        kind=event['event']
        if kind in ['initialize','insert']:
            e.insert_epoch([TupleRecord(*x) for x in event['left']],
                           [TupleRecord(*x) for x in event['right']],12 if kind=='initialize' else event['drift'])
        elif kind=='emit':s[e.emit(tuple(event['pair']))]+=1
        elif kind=='migrate':e.migrate(event['method'])
        elif kind=='drain':
            for pair in sorted(e.pending()):s[e.emit(pair)]+=1
        else:raise ValueError('unknown event')
        e.check(s);checks+=1
    for key,e in engines.items():assert sinks[key]==e.reference()
    return {'traces':len(engines),'event_checks':checks,'mismatches':0}


def mutations():
    def c(pairs):return Counter(pairs)
    expected=c([(0,0),(0,1),(1,0),(1,1)])
    cases=[('drop_obligation',expected,c([(0,0),(0,1),(1,0)])),
           ('duplicate_owner',expected,c([(0,0),(0,1),(1,0),(1,1),(1,1)])),
           ('replay_acknowledged',expected,c([(0,0),(0,1),(1,0),(1,1),(0,0)])),
           ('project_and_deduplicate',expected,c([(0,0)])),
           ('miss_old_new_delta',expected,c([(0,0),(1,0),(1,1)])),
           ('rename_identity',expected,c([(2,0),(2,1),(1,0),(1,1)])),
           ('same_count_wrong_pairing',c([(0,0),(1,1)]),c([(0,1),(1,0)])),
           ('boolean_cover_as_positive',Counter({p:1 for p in crown(6)}),polynomial(crown_cover(6)))]
    rows=[];raw=[]
    for name,good,bad in cases:
        def lineage(poly):return ({i for i,j in poly},{j for i,j in poly})
        row={'case':name,'existence_detects':bool(good)!=bool(bad),
             'count_detects':sum(good.values())!=sum(bad.values()),
             'input_lineage_detects':lineage(good)!=lineage(bad),
             'monomial_support_detects':set(good)!=set(bad),'exact_coefficients_detect':good!=bad}
        assert row['exact_coefficients_detect']
        rows.append(row)
        raw.append({'case':name,'expected':[[*p,v] for p,v in sorted(good.items())],
                    'actual':[[*p,v] for p,v in sorted(bad.items())]})
    save_csv(OUT/'mutations.csv',rows)
    (OUT/'mutation_inputs.json').write_text(json.dumps(raw,indent=2)+'\n')
    return {'cases':len(rows),'exact_detected':len(rows),'support_detected':sum(x['monomial_support_detects'] for x in rows),
            'count_detected':sum(x['count_detects'] for x in rows),'lineage_detected':sum(x['input_lineage_detects'] for x in rows)}


def dag_boundary():
    from .dag import crown_circuit
    rows = []
    for n in [2,4,8,16,32,128,512,2048,8192,32768]:
        begin=time.perf_counter_ns()
        circuit=crown_circuit(n)
        elapsed=time.perf_counter_ns()-begin
        assert circuit.gates==5*n-7
        if n<=16:
            expected=Counter({tuple(sorted((f'x{i}',f'y{j}'))):1
                              for i in range(n) for j in range(n) if i!=j})
            assert circuit.expand()==expected
        rows.append({'n':n,'input_nodes':2*n,'binary_gates':circuit.gates,
                     'wires':circuit.wires,'total_nodes':len(circuit.nodes),
                     'constructor_wall_ns':elapsed,'expanded_check':int(n<=16)})
        del circuit
    save_csv(OUT/'dag_boundary.csv',rows)
    return {'instances':len(rows),'expanded_instances':sum(r['expanded_check'] for r in rows),
            'mismatches':0}


def main():
    global OUT
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('exact');p.add_argument('m',type=int);p.add_argument('n',type=int)
    p=sub.add_parser('bench');p.add_argument('n',type=int)
    p=sub.add_parser('scale');p.add_argument('n',type=int)
    p=sub.add_parser('stream');p.add_argument('start',type=int);p.add_argument('count',type=int)
    p=sub.add_parser('replay');p.add_argument('path',type=Path)
    sub.add_parser('mutations')
    sub.add_parser('dag')
    # All subcommands support a separate output directory.
    for command_parser in sub.choices.values():
        command_parser.add_argument('--out', type=Path, default=ROOT/'results')
    args=parser.parse_args();OUT=args.out;limits();OUT.mkdir(parents=True,exist_ok=True)
    start=time.perf_counter();cpu=time.process_time()
    if args.command=='exact': result=exact(args.m,args.n);name=f'exact_{args.m}x{args.n}'
    elif args.command in ['bench','scale']:
        result=bench(args.n,scale_only=args.command=='scale');name=f'{args.command}_{args.n}'
    elif args.command=='stream':result=stream(args.start,args.count);name=f'stream_{args.start}_{args.count}'
    elif args.command=='replay':result=replay(args.path);name='replay_'+args.path.stem
    elif args.command=='dag':result=dag_boundary();name='dag_boundary'
    else:result=mutations();name='mutations'
    result.update(cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-start,
                  peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,workers=1)
    (OUT/(name+'_summary.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
