"""Exact positive transfer optimization over a supplied row hierarchy.

Cost is additive: header + left-entry weights + right-entry weights for each
nonempty block. All entry weights are positive integers. No sharing, exclusion
predicate, padding-dependent encoding, or global optimality over hierarchies.

The compiler groups unaffected rows into one leaf and balances affected rows.
The DP remembers only the total weight of inherited full columns. At each node
an optimal normal form either takes every available full column or takes none.
"""
from __future__ import annotations
from dataclasses import dataclass
from collections import Counter
from .rectangles import Block

@dataclass(frozen=True)
class TreeNode:
    lo: int
    hi: int
    children: tuple[int, ...]

@dataclass(frozen=True)
class Hierarchy:
    order: tuple[int, ...]
    nodes: tuple[TreeNode, ...]
    root: int


def build_hierarchy(left, emitted, *, singleton_leaves=False):
    """Choose the physical row dictionary BEFORE invoking the optimizer.

    A trusted caller must preserve this value and pass it to the checker.
    This builder does not choose an optimal hierarchy. It groups unaffected
    rows and balances affected rows, or fixes a singleton-leaf hierarchy.
    """
    left=tuple(left)
    if len(set(left)) != len(left): raise ValueError('duplicate row identity')
    affected_ids={i for i,j in emitted}
    if not affected_ids.issubset(set(left)):raise ValueError('foreign row identity')
    unaffected=tuple(i for i in left if i not in affected_ids)
    affected=tuple(i for i in left if i in affected_ids)
    order=left if singleton_leaves else unaffected+affected
    nodes=[]
    def add(lo,hi,children=()):
        nodes.append(TreeNode(lo,hi,tuple(children)));return len(nodes)-1
    def balanced(lo,hi):
        if hi-lo==1:return add(lo,hi)
        mid=(lo+hi)//2
        return add(lo,hi,(balanced(lo,mid),balanced(mid,hi)))
    if not left:root=-1
    elif singleton_leaves or not unaffected:root=balanced(0,len(order))
    elif not affected:root=add(0,len(order))
    else:
        u=add(0,len(unaffected));v=balanced(len(unaffected),len(order))
        root=add(0,len(order),(u,v))
    return Hierarchy(order,tuple(nodes),root)


@dataclass
class Transfer:
    order: tuple[int, ...]
    nodes: list[TreeNode]
    root: int
    blocks: list[Block]
    cost: int
    states: list[dict]
    decisions: dict[int, bool]
    metrics: dict


def compile_transfer(left: tuple[int, ...], right: tuple[int, ...], emitted,
                     *, left_weights=None, right_weights=None, header=0,
                     singleton_leaves=False, hierarchy=None) -> Transfer:
    """Return an exact optimal packet in the generated hierarchy.

    Tree nodes are contiguous ranges in a stable reordered identity array.
    A tree is fixed before optimization and is not part of the minimization.
    The optional singleton hierarchy is used for exact finite-oracle comparisons.
    """
    left, right = tuple(left), tuple(right)
    if type(header) is not int or header < 0:
        raise ValueError('header must be a nonnegative integer')
    if len(set(left)) != len(left) or len(set(right)) != len(right):
        raise ValueError('duplicate source identity')
    lw = dict(left_weights) if left_weights is not None else dict.fromkeys(left,1)
    rw = dict(right_weights) if right_weights is not None else dict.fromkeys(right,1)
    if set(lw)!=set(left) or set(rw)!=set(right):
        raise ValueError('weight domain differs from factor domain')
    if any(type(x) is not int or x<=0 for x in [*lw.values(),*rw.values()]):
        raise ValueError('entry weights must be positive integers')
    ls,rs=set(left),set(right); holes=set(); forbidden={i:set() for i in left}
    for i,j in emitted:
        if i not in ls or j not in rs or (i,j) in holes:
            raise ValueError('invalid or duplicate frontier pair')
        holes.add((i,j));forbidden[i].add(j)
    if not left or not right:
        return Transfer(left,[], -1, [],0,[],{}, {'nodes':0,'states':0,'height':0,'holes':len(holes)})
    selected = hierarchy if hierarchy is not None else build_hierarchy(
        left, holes, singleton_leaves=singleton_leaves)
    order,nodes,root=selected.order,list(selected.nodes),selected.root
    # The compiler accepts only postorder interval trees. The separate checker
    # additionally revalidates every node and binds to the caller's dictionary.
    if len(order)!=len(left) or set(order)!=set(left) or root!=len(nodes)-1:
        raise ValueError('invalid supplied hierarchy')
    reached=set(); pending=[(root,0,len(order))]
    while pending:
        v,lo,hi=pending.pop()
        if v in reached or not 0<=v<len(nodes):raise ValueError('invalid tree node')
        reached.add(v); node=nodes[v]
        if (node.lo,node.hi)!=(lo,hi) or not lo<hi:raise ValueError('invalid interval')
        if len(node.children) not in (0,2):raise ValueError('binary hierarchy required')
        if node.children:
            a,b=node.children
            if not 0<=a<v or not 0<=b<v:raise ValueError('postorder required')
            mid=nodes[a].hi
            pending.extend([(b,mid,hi),(a,lo,mid)])
        elif any(forbidden[i]!=forbidden[order[lo]] for i in order[lo:hi]):
            raise ValueError('nonuniform terminal group')
    if len(reached)!=len(nodes):raise ValueError('unreachable tree node')
    prefix=[0]
    for i in order: prefix.append(prefix[-1]+lw[i])
    bad=[]; q=[set() for _ in nodes]; new_weight=[0 for _ in nodes]
    for v,node in enumerate(nodes):
        if not node.children:
            # The only multi-row leaf created by the builder is unaffected.
            sets=[forbidden[i] for i in order[node.lo:node.hi]]
            assert all(s==sets[0] for s in sets)
            bad.append(set(sets[0]))
        else:
            bad.append(bad[node.children[0]]|bad[node.children[1]])
    q[root]=rs-bad[root]
    for v,node in enumerate(nodes):
        for child in node.children:q[child]=bad[v]-bad[child]
    for v in range(len(nodes)):new_weight[v]=sum(rw[j] for j in q[v])
    state_rows={};choices={};right_order={j:k for k,j in enumerate(right)}
    # Build only the root-reachable ancestry weights. Explicit stacks avoid a
    # language recursion limit even for a valid tall caller-supplied tree.
    needed=[set() for _ in nodes]; pending=[(root,new_weight[root])]
    while pending:
        v,k=pending.pop()
        if k in needed[v]:continue
        needed[v].add(k)
        for c in nodes[v].children:
            pending.append((c,k+new_weight[c]))
            if k:pending.append((c,new_weight[c]))
    values={}
    for v,node in enumerate(nodes):
      fixed=header+prefix[node.hi]-prefix[node.lo]
      active_subtotal=None
      for k in needed[v]:
        if not node.children:
            result=(fixed+k,1) if k else (0,0);take=bool(k)
        else:
            children=[values[c,k+new_weight[c]] for c in node.children]
            notake=(sum(x[0] for x in children),sum(x[1] for x in children))
            if k:
                if active_subtotal is None:
                    children=[values[c,new_weight[c]] for c in node.children]
                    active_subtotal=(sum(x[0] for x in children),sum(x[1] for x in children))
                take_cost=(fixed+k+active_subtotal[0],1+active_subtotal[1])
                take=take_cost<=notake;result=take_cost if take else notake
            else:take=False;result=notake
        values[v,k]=result
        state_rows[v,k]={'node':v,'weight':k,'cost':result[0],'blocks':result[1],'take':take}
    optimum=values[root,new_weight[root]];blocks=[];pending=[(root,q[root])]
    while pending:
        v,available=pending.pop()
        k=sum(rw[j] for j in available);take=state_rows[v,k]['take'];choices[v]=take
        node=nodes[v]
        if take:
            blocks.append(Block(order[node.lo:node.hi],
                                tuple(sorted(available,key=right_order.__getitem__))))
            available=set()
        for child in reversed(node.children):
            assert not available.intersection(q[child])
            pending.append((child,available|q[child]))
    actual=sum(header+sum(lw[i] for i in b.left)+sum(rw[j] for j in b.right) for b in blocks)
    assert actual==optimum[0] and len(blocks)==optimum[1]
    depth=[0]*len(nodes);pending=[root]
    while pending:
        v=pending.pop()
        for c in nodes[v].children:depth[c]=depth[v]+1;pending.append(c)
    return Transfer(order,nodes,root,blocks,optimum[0],
                    list(state_rows.values()),choices,
                    {'nodes':len(nodes),'states':len(state_rows),'height':max(depth),
                     'holes':len(holes),'bad_memberships':sum(map(len,bad)),
                     'born_memberships':sum(map(len,q))})


def weighted_cost(blocks, left_weights, right_weights, header=0):
    return sum(header+sum(left_weights[i] for i in b.left)+sum(right_weights[j] for j in b.right)
               for b in blocks)
