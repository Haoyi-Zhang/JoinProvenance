"""Bounded prospective checks of the certified hierarchical transfer method."""
import argparse,csv,json,os,resource,time,random,copy
from pathlib import Path
from dataclasses import asdict
from collections import Counter
from .laminar import compile_transfer,build_hierarchy,Hierarchy,TreeNode,weighted_cost
from .certificate import verify_transfer
from .rectangles import Block,polynomial,verify_partition_bits,mask_pairs
from .oracle import minimum_costs
from .regions import RegionEngine
from .engine import TupleRecord
ROOT=Path(__file__).resolve().parent.parent

def greedy(left,right,holes,hierarchy):
    # Direct canonical maximal-safe-node traversal in the SAME dictionary.
    blocked={i:set() for i in left}
    for i,j in holes:blocked[i].add(j)
    bad={};out=[]
    for v,node in enumerate(hierarchy.nodes):
        bad[v]=set()
        if node.children:
            for child in node.children:bad[v].update(bad[child])
        else:
            for i in hierarchy.order[node.lo:node.hi]:bad[v].update(blocked[i])
    def visit(v,columns):
        node=hierarchy.nodes[v];safe=columns-bad[v]
        if safe:out.append(Block(hierarchy.order[node.lo:node.hi],tuple(safe)))
        rest=columns-safe
        for child in node.children:visit(child,rest)
    if hierarchy.root>=0 and right:visit(hierarchy.root,set(right))
    return out

def binary_hierarchies(labels):
    # Each unordered rooted full binary tree occurs once (small finite oracle).
    from itertools import combinations
    def shapes(xs):
        if len(xs)==1:return [xs[0]]
        result=[];first,*rest=xs
        for k in range(len(rest)):
            for chosen in combinations(rest,k):
                a=(first,)+chosen;b=tuple(x for x in rest if x not in chosen)
                for x in shapes(a):
                    for y in shapes(b):result.append((x,y))
        return result
    result=[]
    for shape in shapes(tuple(labels)):
        order=[];nodes=[]
        def build(s):
            lo=len(order)
            if isinstance(s,int):order.append(s);children=()
            else:children=(build(s[0]),build(s[1]))
            nodes.append(TreeNode(lo,len(order),children));return len(nodes)-1
        root=build(shape);result.append(Hierarchy(tuple(order),tuple(nodes),root))
    return result

def exact(m,n,start,count,tree_index):
    left=tuple(range(m));right=tuple(range(n));full=set((i,j) for i in left for j in right)
    trees=binary_hierarchies(left)
    tree=trees[tree_index]
    row_sets=[tree.order[v.lo:v.hi] for v in tree.nodes]
    rows=[];cases=0;better=0;bool_mismatch=0;end=min(start+count,1<<(m*n))
    regimes=[('unit',0,dict.fromkeys(left,1),dict.fromkeys(right,1)),
             ('skew',7,{i:2+3*i for i in left},{j:1+5*j for j in right}),
             ('large_integer',2**70,{i:2**65+i for i in left},{j:2**63+2*j for j in right})]
    for name,h,lw,rw in regimes:
        pos,boo=minimum_costs(left,right,row_sets,lw,rw,h)
        for mask in range(start,end):
            holes=full-set(mask_pairs(mask,m,n))
            packet=compile_transfer(left,right,holes,hierarchy=tree,left_weights=lw,right_weights=rw,header=h)
            verify_transfer(left,right,holes,packet,hierarchy=tree,left_weights=lw,right_weights=rw,header=h)
            assert polynomial(packet.blocks)==Counter({p:1 for p in full-holes})
            assert (packet.cost,len(packet.blocks))==pos[mask]
            # With positive entry weights, every optimal Boolean cover is disjoint.
            assert pos[mask]==boo[mask]
            gb=greedy(left,right,holes,tree);gc=weighted_cost(gb,lw,rw,h)
            assert packet.cost<=gc
            assert gc<=(packet.metrics['height']+1)*packet.cost if packet.cost else gc==0
            rows.append({'regime':name,'mask':mask,'cost':packet.cost,'blocks':len(packet.blocks),
                         'greedy_cost':gc,'greedy_blocks':len(gb),'states':len(packet.states)})
            cases+=1;better+=packet.cost<gc
    return rows,{'cases':cases,'mismatches':0,'greedy_improved_cases':better,'tree_index':tree_index,
                 'tree_count':len(trees),'m':m,'n':n,'start':start,'end':end,
                 'all_column_subsets_enumerated':True,'weight_regimes':3}

def boundary():
    # All row dictionaries containing the singleton sets on a three-row domain.
    m=n=3;left=right=tuple(range(3));singles=[(0,),(1,),(2,)]
    extras=[(0,1),(0,2),(1,2),(0,1,2)];records=[]
    for family_mask in range(16):
        family=singles+[x for k,x in enumerate(extras) if family_mask>>k&1]
        laminar=all(not(set(a)&set(b)) or set(a)<=set(b) or set(b)<=set(a) for a in family for b in family)
        pos,boo=minimum_costs(left,right,family,dict.fromkeys(left,1),dict.fromkeys(right,1),20)
        gaps=[mask for mask in range(512) if pos[mask][0]>boo[mask][0]]
        assert bool(gaps)==(not laminar)
        records.append({'family_mask':family_mask,'laminar':int(laminar),'support_masks':512,
                        'strict_gap_masks':len(gaps),'first_gap_mask':gaps[0] if gaps else ''})
    return records,{'dictionaries':16,'support_cases':8192,'mismatches':0}

def gap(height,weight):
    m=1<<height;left=tuple(range(m));tree=build_hierarchy(left,[],singleton_leaves=True)
    right=tuple(range(len(tree.nodes)))
    holes=[(i,j) for i in left for j,node in enumerate(tree.nodes) if i not in tree.order[node.lo:node.hi]]
    lw=dict.fromkeys(left,weight);rw=dict.fromkeys(right,1)
    packet=compile_transfer(left,right,holes,hierarchy=tree,left_weights=lw,right_weights=rw)
    verify_transfer(left,right,holes,packet,hierarchy=tree,left_weights=lw,right_weights=rw)
    baseline=greedy(left,right,holes,tree)
    gc=weighted_cost(baseline,lw,rw)
    assert gc==weight*m*(height+1)+(2*m-1)
    if weight>height:assert packet.cost==m*(weight+height+1)
    verify_partition_bits(left,right,holes,packet.blocks)
    rows=[{'height':height,'m':m,'n':len(right),'holes':len(holes),'left_weight':weight,
           'optimum':packet.cost,'greedy':gc,'ratio':gc/packet.cost,'states':len(packet.states)}]
    return rows,{'cases':1,'mismatches':0}

def benchmarks(n,family):
    left=right=tuple(range(n));records=[];inputs=[]
    for seed in [1701,2718,3141]:
        rng=random.Random(seed)
        if family=='diagonal':holes={(i,i) for i in left}
        elif family=='empty':holes=set()
        elif family=='row':holes={(0,j) for j in right}
        elif family=='column':holes={(i,0) for i in left}
        elif family=='band':holes={(i,i) for i in left}|{(i,(i+1)%n) for i in left}
        elif family=='cluster':
            width=max(1,int(n**.5));holes={(i//width,i%width) for i in range(n)}
        elif family=='random':
            holes=set()
            while len(holes)<n:holes.add((rng.randrange(n),rng.randrange(n)))
        else:raise ValueError('unknown family')
        tree=build_hierarchy(left,holes)
        for regime,h,lw,rw in [('unit',0,dict.fromkeys(left,1),dict.fromkeys(right,1)),
                    ('encoded',16,{i:16+8*(i%4) for i in left},{j:8 for j in right})]:
            inputs.append({'n':n,'family':family,'seed':seed,'regime':regime,'header':h,
                           'left_weights':lw,'right_weights':rw,'holes':sorted(holes)})
            for rep in range(3):
                # Alternate compiler order; certificate validation is timed separately.
                def optimized():return compile_transfer(left,right,holes,hierarchy=tree,left_weights=lw,right_weights=rw,header=h)
                def canonical():return greedy(left,right,holes,tree)
                times={};values={}
                for method,fn in ([('optimized',optimized),('canonical',canonical)] if rep%2==0 else
                                   [('canonical',canonical),('optimized',optimized)]):
                    t=time.perf_counter();values[method]=fn();times[method]=time.perf_counter()-t
                packet=values['optimized'];baseline=values['canonical']
                t=time.perf_counter();verify_transfer(left,right,holes,packet,hierarchy=tree,left_weights=lw,right_weights=rw,header=h);cs=time.perf_counter()-t
                if rep==0:
                    verify_partition_bits(left,right,holes,packet.blocks)
                    verify_partition_bits(left,right,holes,baseline)
                gc=weighted_cost(baseline,lw,rw,h);assert packet.cost<=gc
                records.append({'n':n,'family':family,'seed':seed,'regime':regime,'repeat':rep,
                    'holes':len(holes),'optimized_cost':packet.cost,'canonical_cost':gc,
                    'optimized_blocks':len(packet.blocks),'canonical_blocks':len(baseline),
                    'states':len(packet.states),'height':packet.metrics['height'],
                    'optimized_seconds':times['optimized'],'canonical_seconds':times['canonical'],
                    'certificate_seconds':cs,'payload_memberships':sum(len(b.left)+len(b.right) for b in packet.blocks)})
    return records,{'timing_rows':len(records),'mismatches':0,'independent_instances':3 if family=='random' else 1},inputs

def scale(n):
    left=right=tuple(range(n));holes=[(i,i) for i in left]
    tree=build_hierarchy(left,holes)
    t=time.perf_counter();packet=compile_transfer(left,right,holes,hierarchy=tree);opt_s=time.perf_counter()-t
    t=time.perf_counter();verify_transfer(left,right,holes,packet,hierarchy=tree);cert_s=time.perf_counter()-t
    # A separate, potentially quadratic-bit observer; not charged to compiler state.
    verify_partition_bits(left,right,holes,packet.blocks)
    return [{'n':n,'holes':n,'cost':packet.cost,'blocks':len(packet.blocks),'states':len(packet.states),
             'height':packet.metrics['height'],'optimized_seconds':opt_s,'certificate_seconds':cert_s}],{'cases':1,'mismatches':0}

def mutations():
    left=tuple(range(4));right=tuple(range(3));holes={(0,1),(1,2),(2,1)}
    tree=build_hierarchy(left,holes,singleton_leaves=True)
    original=compile_transfer(left,right,holes,hierarchy=tree)
    records=[]
    def check(name,alter,source_holes=holes,source_tree=tree):
        packet=copy.deepcopy(original);alter(packet)
        try:verify_transfer(left,right,source_holes,packet,hierarchy=source_tree)
        except (ValueError,KeyError,TypeError,IndexError):detected=True
        else:detected=False
        records.append({'case':name,'detected':int(detected)})
        assert detected
    check('missing-block',lambda p:p.blocks.pop())
    check('duplicate-block',lambda p:p.blocks.append(p.blocks[0]))
    check('false-cost',lambda p:setattr(p,'cost',p.cost+1))
    check('false-state-value',lambda p:p.states[0].__setitem__('cost',p.states[0]['cost']+1))
    check('missing-state',lambda p:p.states.pop())
    check('extra-state',lambda p:p.states.append({'node':0,'weight':10000,'cost':10001,'blocks':1,'take':True}))
    check('false-decision',lambda p:p.states[0].__setitem__('take',not p.states[0]['take']))
    check('wrong-dictionary',lambda p:None,source_tree=binary_hierarchies(left)[0])
    check('changed-source-frontier',lambda p:None,source_holes=holes|{(3,2)})
    def repeated_member(p):
        b=p.blocks[0];p.blocks[0]=Block(b.left,b.right+(b.right[0],))
    check('repeated-column-member',repeated_member)
    check('wrong-traversal-decision',lambda p:p.decisions.__setitem__(tree.root,not p.decisions[tree.root]))
    check('boolean-state-cost',lambda p:p.states[0].__setitem__('cost',True))
    check('missing-state-field',lambda p:p.states[0].pop('take'))
    def noncanonical_right_order(p):
        k=next(i for i,b in enumerate(p.blocks) if len(b.right)>1)
        b=p.blocks[k];p.blocks[k]=Block(b.left,tuple(reversed(b.right)))
    check('noncanonical-right-order',noncanonical_right_order)
    def empty_factor(p):
        b=p.blocks[0];p.blocks[0]=Block((),b.right)
    check('empty-left-factor',empty_factor)
    return records,{'fixtures':len(records),'detected':sum(x['detected'] for x in records),'mismatches':0}

def stream():
    records=[];events=[];checks=0
    for seed in range(601,625):
      for drift in [0,1,2,4]:
        rng=random.Random(seed);engine=RegionEngine();sink=Counter();lid=rid=0
        def log(event):
            nonlocal checks
            engine.check(sink);checks+=1
            events.append({'seed':seed,'drift':drift,**event})
        left=[TupleRecord(i,i%3,0) for i in range(6)]
        right=[TupleRecord(i,i%3,0) for i in range(6)]
        engine.insert_epoch(left,right,12);lid=rid=6
        log({'kind':'insert','bound':12,'left':[asdict(x) for x in left],'right':[asdict(x) for x in right]})
        switches=0
        for epoch in range(16):
            batch=rng.randrange(drift+1);nl=rng.randrange(batch+1);nr=batch-nl
            a=[TupleRecord(lid+i,rng.randrange(3),0) for i in range(nl)];lid+=nl
            b=[TupleRecord(rid+i,rng.randrange(3),0) for i in range(nr)];rid+=nr
            engine.insert_epoch(a,b,drift)
            log({'kind':'insert','bound':drift,'left':[asdict(x) for x in a],'right':[asdict(x) for x in b]})
            for _ in range(rng.randrange(4)):
                pending=sorted(engine.pending())
                if not pending:break
                pair=rng.choice(pending);sink[engine.emit(pair)]+=1
                log({'kind':'emit','pair':pair})
            method=['laminar','column','laminar','row'][epoch%4]
            engine.migrate(method);switches+=1;log({'kind':'migrate','method':method})
        # Each final emission is observed, rather than only a final batch check.
        for pair in sorted(engine.pending()):
            sink[engine.emit(pair)]+=1;log({'kind':'emit','pair':pair})
        assert sink==engine.reference()
        records.append({'seed':seed,'drift':drift,'switches':switches,'final_left':lid,'final_right':rid,'output_pairs':len(sink)})
    return records,{'traces':len(records),'checked_transitions':checks,'mismatches':0},events

def replay(path):
    current=None;engine=None;sink=None;checks=0;traces=0
    for line in Path(path).read_text().splitlines():
        e=json.loads(line);key=e['seed'],e['drift']
        if key!=current:
            if engine is not None:assert sink==engine.reference()
            current=key;engine=RegionEngine();sink=Counter();traces+=1
        if e['kind']=='insert':engine.insert_epoch([TupleRecord(**x) for x in e['left']],[TupleRecord(**x) for x in e['right']],e['bound'])
        elif e['kind']=='emit':sink[engine.emit(tuple(e['pair']))]+=1
        elif e['kind']=='migrate':engine.migrate(e['method'])
        else:raise ValueError('unknown event')
        engine.check(sink);checks+=1
    assert sink==engine.reference()
    return [],{'traces':traces,'checked_transitions':checks,'mismatches':0}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['exact','boundary','gap','bench','scale','mutations','stream','replay'])
    ap.add_argument('args',nargs='*');ap.add_argument('--out',default=str(ROOT/'results'))
    a=ap.parse_args();os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
    resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(40,45))
    wall=time.perf_counter();cpu=time.process_time();inputs=None
    if a.mode=='exact':rows,meta=exact(*map(int,a.args))
    elif a.mode=='boundary':rows,meta=boundary()
    elif a.mode=='gap':rows,meta=gap(*map(int,a.args))
    elif a.mode=='bench':rows,meta,inputs=benchmarks(int(a.args[0]),a.args[1])
    elif a.mode=='scale':rows,meta=scale(int(a.args[0]))
    elif a.mode=='mutations':rows,meta=mutations()
    elif a.mode=='stream':rows,meta,inputs=stream()
    elif a.mode=='replay':rows,meta=replay(a.args[0])
    meta.update(cpu_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-wall,
                peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,workers=1)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    name='hierarchy_'+a.mode+('_'+'_'.join(Path(x).stem for x in a.args) if a.args else '')
    if rows:
        with (out/(name+'.csv')).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    if inputs is not None:
        with (out/(name+('_events' if a.mode=='stream' else '_inputs')+'.jsonl')).open('w') as f:
            for x in inputs:f.write(json.dumps(x,separators=(',',':'))+'\n')
    (out/(name+'_summary.json')).write_text(json.dumps(meta,indent=2)+'\n')
    print(json.dumps(meta))
if __name__=='__main__':main()
