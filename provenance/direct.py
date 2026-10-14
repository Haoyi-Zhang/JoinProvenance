"""Dense, certificate-independent receiver baseline for the SAME packet optimum.

This deliberately computes full-column masks from literal row complements,
and indexes choices by the last active ancestor, not sparse births or summed
inherited weights. It calls neither the compiler nor certificate checker.
It is independently coded here, not independently authored or mechanized.
"""
from dataclasses import dataclass
from .rectangles import Block
from .gates import require

@dataclass(frozen=True)
class DirectResult:
    blocks: tuple[Block, ...]
    cost: int
    states: int

def optimize_direct(left,right,emitted,*,hierarchy,left_weights=None,right_weights=None,header=0):
    left,right=tuple(left),tuple(right)
    require(type(header) is int and header>=0,'direct: header')
    require(len(set(left))==len(left) and len(set(right))==len(right),'direct: duplicate identity')
    lw=dict.fromkeys(left,1) if left_weights is None else dict(left_weights)
    rw=dict.fromkeys(right,1) if right_weights is None else dict(right_weights)
    require(set(lw)==set(left) and set(rw)==set(right),'direct: weight domains')
    require(all(type(x) is int and x>0 for x in [*lw.values(),*rw.values()]),'direct: weights')
    rank={j:k for k,j in enumerate(right)};rows=dict.fromkeys(left,(1<<len(right))-1);seen=set()
    for i,j in emitted:
        require(i in rows and j in rank and (i,j) not in seen,'direct: frontier')
        seen.add((i,j));rows[i]&=~(1<<rank[j])
    if not left or not right:
        require(len(hierarchy.order)==len(left) and set(hierarchy.order)==set(left),'direct: empty hierarchy')
        return DirectResult((),0,0)
    order=tuple(hierarchy.order);nodes=tuple(hierarchy.nodes);root=hierarchy.root
    require(len(order)==len(left) and set(order)==set(left),'direct: row dictionary')
    require(type(root) is int and 0<=root<len(nodes),'direct: root')
    post=[];reached=set();stack=[(root,0,len(left),False)]
    while stack:
        v,lo,hi,exit=stack.pop()
        if exit:post.append(v);continue
        require(type(v) is int and 0<=v<len(nodes) and v not in reached,'direct: tree node')
        reached.add(v);node=nodes[v]
        require((node.lo,node.hi)==(lo,hi) and lo<hi,'direct: interval')
        require(len(node.children) in (0,2),'direct: binary tree')
        stack.append((v,lo,hi,True))
        if node.children:
            a,b=node.children
            require(all(type(c) is int and 0<=c<len(nodes) for c in (a,b)),'direct: children')
            mid=nodes[a].hi
            stack.extend([(b,mid,hi,False),(a,lo,mid,False)])
        else:
            require(all(rows[i]==rows[order[lo]] for i in order[lo:hi]),'direct: nonuniform leaf')
    require(len(reached)==len(nodes),'direct: extra nodes')
    full={};fixed={};prefix=[0]
    for i in order:prefix.append(prefix[-1]+lw[i])
    for v in post:
        node=nodes[v];fixed[v]=header+prefix[node.hi]-prefix[node.lo]
        full[v]=(full[node.children[0]] & full[node.children[1]]) if node.children else rows[order[node.lo]]
    needed={v:set() for v in reached};stack=[(root,-1)]
    def available(v,ancestor):return full[v] & ~(full[ancestor] if ancestor>=0 else 0)
    while stack:
        v,ancestor=stack.pop()
        if ancestor in needed[v]:continue
        needed[v].add(ancestor)
        for c in nodes[v].children:
            stack.append((c,ancestor))
            if available(v,ancestor):stack.append((c,v))
    def columns(mask):
        while mask:
            bit=mask & -mask; yield right[bit.bit_length()-1];mask^=bit
    weights={0:0};values={};take={}
    for v in post:
        for ancestor in needed[v]:
            mask=available(v,ancestor)
            if mask not in weights:weights[mask]=sum(rw[j] for j in columns(mask))
            own=(fixed[v]+weights[mask],1) if mask else (0,0)
            children=nodes[v].children
            if not children:
                values[v,ancestor]=own;take[v,ancestor]=bool(mask)
            else:
                no=tuple(sum(values[c,ancestor][k] for c in children) for k in (0,1))
                yes=tuple(own[k]+sum(values[c,v][k] for c in children) for k in (0,1)) if mask else None
                take[v,ancestor]=yes is not None and yes<=no
                values[v,ancestor]=yes if take[v,ancestor] else no
    blocks=[];stack=[(root,-1)]
    while stack:
        v,ancestor=stack.pop();node=nodes[v]
        if take[v,ancestor]:
            blocks.append(Block(order[node.lo:node.hi],tuple(columns(available(v,ancestor)))));ancestor=v
        stack.extend((c,ancestor) for c in reversed(node.children))
    total=sum(header+sum(lw[i] for i in b.left)+sum(rw[j] for j in b.right) for b in blocks)
    require((total,len(blocks))==values[root,-1],'direct: reconstruction')
    return DirectResult(tuple(blocks),total,len(values))

def verify_direct(left,right,emitted,packet,*,hierarchy,**weights):
    """Check packet semantics/optimality by recomputation, NOT producer DP rows.

    Its wire protocol omits states/decisions. It certifies the same output
    guarantee, not the truth of a discarded producer certificate.
    """
    expected=optimize_direct(left,right,emitted,hierarchy=hierarchy,**weights)
    require(type(packet.cost) is int and packet.cost==expected.cost,'direct: packet cost')
    if left and right:
        require(tuple(packet.order)==tuple(hierarchy.order) and tuple(packet.nodes)==tuple(hierarchy.nodes)
                and packet.root==hierarchy.root,'direct: packet dictionary')
    else:
        require(tuple(packet.order)==tuple(left) and not packet.nodes and packet.root==-1,'direct: empty packet')
    supplied=tuple(Block(tuple(b.left),tuple(b.right)) for b in packet.blocks)
    require(supplied==expected.blocks,'direct: packet binding')
    return dict(checked=True,cost=expected.cost,blocks=len(expected.blocks),states=expected.states)
