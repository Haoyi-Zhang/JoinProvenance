import os,sys,time,resource,json
from pathlib import Path
import argparse
_parser=argparse.ArgumentParser()
_parser.add_argument('--out',type=Path,default=Path(__file__).resolve().parent/'results')
_output=_parser.parse_args().out
_output.mkdir(parents=True,exist_ok=True)
from collections import Counter
sys.path.insert(0,str(Path(__file__).resolve().parent))
from provenance.laminar import *
from provenance.certificate import verify_transfer
from provenance.rectangles import *
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
t=time.perf_counter();cpu=time.process_time();cases=0;improvements=0;example=None
# Independent exact weighted shortest-path oracle, with arbitrary allowed column subsets.
for m,n in [(1,1),(2,3),(3,3),(4,3)]:
 full=set((i,j) for i in range(m) for j in range(n))
 pos,_=all_optima(m,n)
 # Hierarchy is fixed across every support mask by singleton_leaves=True.
 base=compile_transfer(tuple(range(m)),tuple(range(n)),[],singleton_leaves=True)
 candidates=[]
 for node in base.nodes:
  for colmask in range(1,1<<n):
   b=Block(tuple(range(node.lo,node.hi)),tuple(j for j in range(n) if colmask>>j&1))
   candidates.append((as_mask(b.pairs(),m,n),b))
 for header,lw,rw in [(0,{i:1 for i in range(m)},{j:1 for j in range(n)}),
                      (3,{i:1+i for i in range(m)},{j:1+2*j for j in range(n)})]:
  dp=[(10**9,10**9)]*(1<<(m*n));dp[0]=(0,0)
  for mask in range(len(dp)):
   for bits,b in candidates:
    if bits&mask:continue
    cost=header+sum(lw[i] for i in b.left)+sum(rw[j] for j in b.right)
    new=mask|bits;val=(dp[mask][0]+cost,dp[mask][1]+1)
    if val<dp[new]:dp[new]=val
  for mask in range(1<<(m*n)):
   e=full-set(mask_pairs(mask,m,n))
   packet=compile_transfer(tuple(range(m)),tuple(range(n)),e,left_weights=lw,right_weights=rw,header=header,singleton_leaves=True)
   verify_transfer(tuple(range(m)),tuple(range(n)),e,packet,hierarchy=build_hierarchy(tuple(range(m)),e,singleton_leaves=True),left_weights=lw,right_weights=rw,header=header)
   assert polynomial(packet.blocks)==Counter({p:1 for p in full-e})
   assert (packet.cost,len(packet.blocks))==dp[mask]
   # Compare with the existing first-safe compiler only where the hierarchy agrees.
   baseline=sparse_complement(tuple(range(m)),tuple(range(n)),e)
   bc=weighted_cost(baseline,lw,rw,header)
   if packet.cost<bc:
    improvements+=1
    if example is None:example={'m':m,'n':n,'mask':mask,'header':header,'optimal_cost':packet.cost,'greedy_cost':bc}
   cases+=1
n=2048;a=tuple(range(n));e=[(i,i) for i in a]
start=time.perf_counter();packet=compile_transfer(a,a,e);compile_s=time.perf_counter()-start
start=time.perf_counter();verify_transfer(a,a,e,packet,hierarchy=build_hierarchy(a,e));verify_s=time.perf_counter()-start
verify_partition_bits(a,a,e,packet.blocks)
result={'oracle_cases':cases,'mismatches':0,'greedy_improvement_observations':improvements,
        'first_example':example,'scale_n':n,'scale_cost':packet.cost,'scale_blocks':len(packet.blocks),
        'scale_states':packet.metrics['states'],'scale_height':packet.metrics['height'],
        'compile_seconds':compile_s,'certificate_seconds':verify_s,
        'cpu_seconds':time.process_time()-cpu,'wall_seconds':time.perf_counter()-t,
        'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'workers':1}
(_output/'laminar_pilot.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
