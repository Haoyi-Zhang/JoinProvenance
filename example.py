"""A two-row source whose canonical transfer costs 7, but the optimum costs 6."""
from provenance.laminar import build_hierarchy, compile_transfer
from provenance.certificate import verify_transfer
from provenance.hierarchy_campaign import greedy
from provenance.rectangles import polynomial
left=(0,1);right=(0,1,2);emitted={(0,1),(1,2)}
hierarchy=build_hierarchy(left,emitted,singleton_leaves=True)
packet=compile_transfer(left,right,emitted,hierarchy=hierarchy)
check_stats=verify_transfer(left,right,emitted,packet,hierarchy=hierarchy)
canonical=greedy(left,right,emitted,hierarchy)
print('canonical membership cost:',sum(b.memberships for b in canonical))
print('checker statistics:',check_stats)
print('blocks:',packet.blocks)
assert packet.cost==6
assert polynomial(packet.blocks)==polynomial(canonical)
