import os, sys, time, json, resource
from pathlib import Path
import argparse
_parser=argparse.ArgumentParser()
_parser.add_argument('--out',type=Path,default=Path(__file__).resolve().parent/'results')
_output=_parser.parse_args().out
_output.mkdir(parents=True,exist_ok=True)
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
resource.setrlimit(resource.RLIMIT_AS,(3*1024**3,3*1024**3))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from provenance.rectangles import *
from provenance.engine import *
t=time.perf_counter(); c=time.process_time()
p,b=all_optima(3,3)
for mask in range(512):
 assert rational_rank(mask,3,3)<=p[mask]
 assert b[mask]<=p[mask]<=3
 assert len(optimal_blocks(mask,3,3))==p[mask]
 assert len(optimal_blocks(mask,3,3,boolean=True))==b[mask]
e=Engine(); sink=Counter()
steps=0
for turn in range(12):
 left=[TupleRecord(turn,turn%2,0)] if turn%3 else []
 right=[TupleRecord(turn,(turn+1)%2,0)] if not left else []
 e.insert_epoch(left,right,1);e.check(sink);steps+=1
 for order in ['row','column']:
  e.migrate(order);e.check(sink);steps+=1
  pairs=list(polynomial(e.pending))
  if pairs:
   sink[e.emit(pairs[len(pairs)//2])]+=1;e.check(sink);steps+=1
while e.pending:
 pair=next(iter(polynomial(e.pending)));sink[e.emit(pair)]+=1;e.check(sink);steps+=1
# Decisive negative control: Sperner cover of six crown vertices double-counts.
cover=polynomial(crown_cover(6));expected=Counter({p:1 for p in crown(6)})
assert set(cover)==set(expected) and cover!=expected
report={'oracle_dimensions':[3,3],'masks':512,'oracle_mismatches':0,'engine_transitions':steps,'engine_mismatches':0,
'negative_control':{'n':6,'positive_width':6,'boolean_width':4,'support_equal':True,'coefficients_equal':False,'max_coefficient':max(cover.values())},
'wall_seconds':time.perf_counter()-t,'cpu_seconds':time.process_time()-c,'peak_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'workers':1}
(_output/'pilot.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
