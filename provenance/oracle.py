"""Independent exhaustive weighted rectangle-cover and partition oracle.

Enumerates EVERY nonempty column subset for every allowed row set; it does
not use laminarity, the all-or-none lemma, or the compiler recurrence.
Admitted inputs have at most sixteen possible pairs. Every target support
mask is solved, including infeasible masks for restricted row dictionaries.
"""
from .rectangles import Block, as_mask
from math import inf

def minimum_costs(left,right,row_sets,lw,rw,header):
    if len(left)*len(right)>16:raise ValueError('oracle admission limit: 16 cells')
    li={x:i for i,x in enumerate(left)};ri={x:i for i,x in enumerate(right)}
    # A bound on one candidate does not bound a complete partition's cost.
    # Keep every reachable cost as an exact integer; infinity marks only
    # unreachable supports and cannot collide with an admitted finite total.
    unreachable=(inf,inf); total=1<<(len(left)*len(right))
    positive=[unreachable]*total;boolean=[unreachable]*total;positive[0]=boolean[0]=(0,0)
    candidates=[]
    for rows in row_sets:
        if not rows:continue
        for mask in range(1,1<<len(right)):
            cols=tuple(x for x in right if mask>>ri[x]&1)
            bits=sum(1<<(li[i]*len(right)+ri[j]) for i in rows for j in cols)
            cost=header+sum(lw[i] for i in rows)+sum(rw[j] for j in cols)
            if cost>=10**99:raise ValueError('oracle cost admission bound')
            candidates.append((bits,cost))
    for old in range(total):
        for bits,cost in candidates:
            new=old|bits
            if new==old:continue
            value=(boolean[old][0]+cost,boolean[old][1]+1)
            if value<boolean[new]:boolean[new]=value
            if old&bits:continue
            value=(positive[old][0]+cost,positive[old][1]+1)
            if value<positive[new]:positive[new]=value
    return positive,boolean
