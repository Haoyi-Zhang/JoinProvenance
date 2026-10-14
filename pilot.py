from provenance.gates import require
from provenance.resources import apply_limits, peak_rss_kib
import os, sys, time, json
from pathlib import Path
import argparse
_parser=argparse.ArgumentParser()
_parser.add_argument('--out',type=Path,default=Path(__file__).resolve().parent/'results')
_output=_parser.parse_args().out
_output.mkdir(parents=True,exist_ok=True)
apply_limits()
sys.path.insert(0, str(Path(__file__).resolve().parent))
from provenance.rectangles import *
from provenance.engine import *
t=time.perf_counter(); c=time.process_time()
p,b=all_optima(3,3)
for mask in range(512):
 require((rational_rank(mask,3,3)<=p[mask]), 'pilot.py: scientific check 1')
 require((b[mask]<=p[mask]<=3), 'pilot.py: scientific check 2')
 require((len(optimal_blocks(mask,3,3))==p[mask]), 'pilot.py: scientific check 3')
 require((len(optimal_blocks(mask,3,3,boolean=True))==b[mask]), 'pilot.py: scientific check 4')
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
require((set(cover)==set(expected) and cover!=expected), 'pilot.py: scientific check 5')
report={'oracle_dimensions':[3,3],'masks':512,'oracle_mismatches':0,'engine_transitions':steps,'engine_mismatches':0,
'negative_control':{'n':6,'positive_width':6,'boolean_width':4,'support_equal':True,'coefficients_equal':False,'max_coefficient':max(cover.values())},
'wall_seconds':time.perf_counter()-t,'cpu_seconds':time.process_time()-c,'peak_rss_kib':peak_rss_kib(),'workers':1}
(_output/'pilot.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
