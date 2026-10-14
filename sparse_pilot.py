from provenance.gates import require
from provenance.resources import apply_limits, peak_rss_kib
import sys,time,json,os
from pathlib import Path
import argparse
_parser=argparse.ArgumentParser()
_parser.add_argument('--out',type=Path,default=Path(__file__).resolve().parent/'results')
_output=_parser.parse_args().out
_output.mkdir(parents=True,exist_ok=True)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from provenance.rectangles import *
apply_limits()
t=time.perf_counter();c=time.process_time();cases=0
for m,n in [(1,1),(1,4),(2,3),(3,3)]:
 full={(i,j) for i in range(m) for j in range(n)}
 for mask in range(1 << (m*n)):
  emitted=set(mask_pairs(mask,m,n))
  got=sparse_complement(tuple(range(m)),tuple(range(n)),emitted)
  require((polynomial(got)==Counter({p:1 for p in full-emitted})), 'sparse_pilot.py: scientific check 1')
  d=len({i for i,j in emitted});e=len(emitted);h=(d-1).bit_length() if d else 0
  require((len(got)<=2*d if d else len(got)<=1), 'sparse_pilot.py: scientific check 2')
  require((sum(b.memberships for b in got)<=m+2*n+(d+2*e)*h), 'sparse_pilot.py: scientific check 3')
  cases+=1
n=2048;emitted=[(i,i) for i in range(n)]
start=time.perf_counter();blocks=sparse_complement(tuple(range(n)),tuple(range(n)),emitted);elapsed=time.perf_counter()-start
require((len(blocks)==2*(n-1)), 'sparse_pilot.py: scientific check 4')
require((sum(b.memberships for b in blocks)==2*n*11), 'sparse_pilot.py: scientific check 5')
report={'small_cases':cases,'mismatches':0,'scale_n':n,'scale_emissions':n,'scale_blocks':len(blocks),'scale_memberships':sum(b.memberships for b in blocks),'scale_seconds':elapsed,'wall_seconds':time.perf_counter()-t,'cpu_seconds':time.process_time()-c,'peak_rss_kib':peak_rss_kib(),'workers':1}
(_output/'sparse_pilot.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
