"""Paired end-to-end local receiver costs on the existing benchmark inputs.

No new workload matrix or remote traffic. The same source, supplied hierarchy,
weights, deterministic packet and output guarantee are used by both protocols.
Timers cover producer compilation, JSON encoding/decoding, receiver validation
and local immutable-tuple installation. Retained context size is separate;
JSON is an explicitly authored measurement format, not a database wire format.
"""
import argparse,csv,hashlib,json,statistics,time
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from provenance.laminar import compile_transfer,build_hierarchy,TreeNode
from provenance.certificate import verify_transfer
from provenance.direct import verify_direct
from provenance.rectangles import Block,verify_partition_bits
from provenance.gates import require

def encode(packet,certified):
    obj=dict(order=packet.order,nodes=[asdict(n) for n in packet.nodes],root=packet.root,
             blocks=[asdict(b) for b in packet.blocks],cost=packet.cost)
    if certified:obj.update(states=packet.states,decisions=packet.decisions)
    return json.dumps(obj,separators=(',',':')).encode('utf-8')

def decode(wire):
    obj=json.loads(wire)
    obj['order']=tuple(obj['order'])
    obj['nodes']=[TreeNode(n['lo'],n['hi'],tuple(n['children'])) for n in obj['nodes']]
    obj['blocks']=[Block(tuple(b['left']),tuple(b['right'])) for b in obj['blocks']]
    if 'decisions' in obj:obj['decisions']={int(k):v for k,v in obj['decisions'].items()}
    return SimpleNamespace(**obj)

def verify_recompile(left,right,holes,packet,*,hierarchy,**weights):
    """Simplest trusted sparse recomputation; shares the producer implementation."""
    expected=compile_transfer(left,right,holes,hierarchy=hierarchy,**weights)
    require(type(packet.cost) is int and packet.cost==expected.cost,'recompile: cost')
    require(packet.order==expected.order and packet.nodes==expected.nodes and packet.root==expected.root,
            'recompile: dictionary')
    require(packet.blocks==expected.blocks,'recompile: packet binding')
    return dict(checked=True,cost=expected.cost,blocks=len(expected.blocks))

def run_case(source,repeats=3):
    n=source['n'];left=right=tuple(range(n));holes=tuple(map(tuple,source['holes']))
    tree=build_hierarchy(left,holes)
    weights=dict(header=source['header'],left_weights={int(i):v for i,v in source['left_weights'].items()},
                 right_weights={int(i):v for i,v in source['right_weights'].items()})
    context=dict(left=left,right=right,emitted=holes,hierarchy=asdict(tree),**weights)
    context_bytes=len(json.dumps(context,separators=(',',':')).encode('utf-8'))
    digest=hashlib.sha256(json.dumps(source,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    rows=[]
    for repeat in range(repeats):
        observations={}
        # Rotate all three orders, not only a fixed first/last position.
        methods=('certificate','direct','recompile')
        methods=methods[repeat%3:]+methods[:repeat%3]
        for method in methods:
            start=time.perf_counter()
            packet=compile_transfer(left,right,holes,hierarchy=tree,**weights)
            compiled=time.perf_counter()
            wire=encode(packet,method=='certificate');encoded=time.perf_counter()
            received=decode(wire);decoded=time.perf_counter()
            verifier={'certificate':verify_transfer,'direct':verify_direct,'recompile':verify_recompile}[method]
            stats=verifier(left,right,holes,received,hierarchy=tree,**weights)
            checked=time.perf_counter()
            installed=tuple((tuple(b.left),tuple(b.right)) for b in received.blocks)
            finished=time.perf_counter()
            require(stats['checked'] is True,'receiver did not accept')
            observations[method]=(packet.cost,installed)
            if repeat==0:verify_partition_bits(left,right,holes,received.blocks)
            rows.append(dict(n=n,family=source['family'],seed=source['seed'],regime=source['regime'],
                repeat=repeat,method=method,input_sha256=digest,cost=packet.cost,blocks=len(installed),
                wire_bytes=len(wire),context_json_bytes=context_bytes,
                compile_seconds=compiled-start,encode_seconds=encoded-compiled,
                decode_seconds=decoded-encoded,verify_seconds=checked-decoded,
                install_seconds=finished-checked,total_seconds=finished-start))
        require(observations['certificate']==observations['direct']==observations['recompile'],
                'same-contract receiver disagreement')
    return rows

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--n',type=int,required=True,choices=[32,128,512,2048])
    ap.add_argument('--source',type=Path,default=Path(__file__).resolve().parent/'results')
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--first',type=int,default=0)
    ap.add_argument('--count',type=int,default=18)
    a=ap.parse_args()
    require(0<=a.first<18 and 1<=a.count<=18-a.first,'invalid existing-input chunk')
    sources=[];seen=set()
    for f in sorted(a.source.glob(f'hierarchy_bench_{a.n}_*_inputs.jsonl')):
        for line in f.read_text().splitlines():
            s=json.loads(line)
            # Nonrandom seed labels repeat the identical support. Keep it once.
            key=(s['family'],s['regime'],s['seed'] if s['family']=='random' else 'fixed')
            if key in seen:continue
            seen.add(key);sources.append(s)
    require(len(sources)==18,'expected existing 18 weighted inputs at each size')
    sources=sources[a.first:a.first+a.count]
    rows=[]
    for source in sources:rows.extend(run_case(source))
    stem=f'receiver_{a.n}'+(f'_{a.first}_{a.count}' if a.first or a.count!=18 else '')
    a.out.mkdir(parents=True,exist_ok=True)
    with (a.out/(stem+'.csv')).open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    with (a.out/(stem+'_inputs.jsonl')).open('w',newline='\n',encoding='utf-8') as f:
        for source in sources:f.write(json.dumps(source,separators=(',',':'))+'\n')
    pairs={}
    for row in rows:pairs.setdefault((row['family'],row['seed'],row['regime'],row['repeat']),{})[row['method']]=row
    ratios=[p['certificate']['total_seconds']/p['direct']['total_seconds'] for p in pairs.values()]
    reratios=[p['certificate']['total_seconds']/p['recompile']['total_seconds'] for p in pairs.values()]
    result=dict(n=a.n,first=a.first,count=a.count,weighted_inputs=len(sources),paired_repeats=len(pairs),method_rows=len(rows),
                same_output_mismatches=0,certificate_over_direct_total_median=statistics.median(ratios),
                certificate_faster_pairs=sum(r<1 for r in ratios),
                certificate_over_recompile_total_median=statistics.median(reratios),
                certificate_faster_than_recompile_pairs=sum(r<1 for r in reratios),
                direct_omits_producer_certificate=True,independent_authorship=False,
                timing_scope='compile+encode+decode+verify+local tuple install; no transport/executor')
    (a.out/(stem+'_summary.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
if __name__=='__main__':main()
