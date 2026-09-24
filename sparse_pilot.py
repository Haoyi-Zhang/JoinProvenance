import sys,time,json,resource,os
from pathlib import Path
import argparse
_parser=argparse.ArgumentParser()
_parser.add_argument('--out',type=Path,default=Path(__file__).resolve().parent/'results')
_output=_parser.parse_args().out
_output.mkdir(parents=True,exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from provenance.rectangles import *
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
t=time.perf_counter();c=time.process_time();cases=0
for m,n in [(1,1),(1,4),(2,3),(3,3)]:
 full={(i,j) for i in range(m) for j in range(n)}
 for mask in range(1 << (m*n)):
  emitted=set(mask_pairs(mask,m,n))
  got=sparse_complement(tuple(range(m)),tuple(range(n)),emitted)
  assert polynomial(got)==Counter({p:1 for p in full-emitted})
  d=len({i for i,j in emitted});e=len(emitted);h=(d-1).bit_length() if d else 0
  assert len(got)<=2*d if d else len(got)<=1
  assert sum(b.memberships for b in got)<=m+2*n+(d+2*e)*h
  cases+=1
n=2048;emitted=[(i,i) for i in range(n)]
start=time.perf_counter();blocks=sparse_complement(tuple(range(n)),tuple(range(n)),emitted);elapsed=time.perf_counter()-start
assert len(blocks)==2*(n-1)
assert sum(b.memberships for b in blocks)==2*n*11
report={'small_cases':cases,'mismatches':0,'scale_n':n,'scale_emissions':n,'scale_blocks':len(blocks),'scale_memberships':sum(b.memberships for b in blocks),'scale_seconds':elapsed,'wall_seconds':time.perf_counter()-t,'cpu_seconds':time.process_time()-c,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'workers':1}
(_output/'sparse_pilot.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
