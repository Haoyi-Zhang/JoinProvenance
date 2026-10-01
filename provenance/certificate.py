"""A separate recurrence and packet checker for hierarchical transfer certificates.

No compiler routine or polynomial expansion is called. The source factors,
frontier and weights are trusted inputs; the packet, hierarchy and DP table are
untrusted. Optimality is only for the validated hierarchy, which MUST equal
the trusted caller-supplied hierarchy argument.
"""
from __future__ import annotations
from collections import defaultdict


def verify_transfer(left,right,emitted,transfer,*,hierarchy,left_weights=None,right_weights=None,header=0):
    """Validate ``transfer`` and return recomputed summary statistics.

    The return value is an ordinary statistics dictionary whose ``checked``
    field is ``True``.  It is not an immutable checked-packet capability and
    does not bind the caller to the validated object after this call.  The
    checker reconstructs the sparse normal form and its cost but deliberately
    does not expand all row--column pairs; dense coefficient expansion belongs
    to the independent bitset observer used by the finite experiments.
    """
    def require(ok,message):
        if not ok:raise ValueError(message)
    left,right=tuple(left),tuple(right)
    require(all(hasattr(transfer,name) for name in
                ('order','nodes','root','blocks','cost','states','decisions')),
            'malformed transfer object')
    require(all(hasattr(hierarchy,name) for name in ('order','nodes','root')),
            'malformed trusted hierarchy')
    require(type(header) is int and header>=0,'invalid header')
    require(len(set(left))==len(left) and len(set(right))==len(right),'duplicate input ID')
    lw=dict(left_weights) if left_weights is not None else dict.fromkeys(left,1)
    rw=dict(right_weights) if right_weights is not None else dict.fromkeys(right,1)
    require(set(lw)==set(left) and set(rw)==set(right),'weight domains')
    require(all(type(x) is int and x>0 for x in list(lw.values())+list(rw.values())),'positive weights required')
    seen=set(); exceptions=defaultdict(set)
    for pair in emitted:
        i,j=pair
        pair=(i,j)
        require(pair not in seen and i in lw and j in rw,'invalid frontier')
        seen.add(pair); exceptions[i].add(j)
    if not left or not right:
        require(tuple(hierarchy.order)==tuple(left) or
                (len(hierarchy.order)==len(left) and set(hierarchy.order)==set(left)),
                'empty-input hierarchy domain')
        require(tuple(transfer.order)==tuple(left) and not transfer.nodes and
                transfer.root==-1 and not transfer.blocks and type(transfer.cost) is int and
                transfer.cost==0 and not transfer.states and not transfer.decisions,
                'nonempty empty-input certificate')
        return {'cost':0,'states':0,'blocks':0,'checked':True}
    order=tuple(transfer.order);nodes=list(transfer.nodes);root=transfer.root
    require(type(root) is int and type(transfer.cost) is int and transfer.cost>=0,
            'invalid packet scalar')
    require(isinstance(transfer.states,list) and isinstance(transfer.blocks,list) and
            isinstance(transfer.decisions,dict),'invalid packet container')
    require(order==hierarchy.order and tuple(nodes)==hierarchy.nodes and
            root==hierarchy.root,'packet hierarchy differs from trusted format')
    require(len(order)==len(left) and set(order)==set(left),'invalid row permutation')
    require(0<=root<len(nodes),'root out of range')
    parents={}; reached=set(); depths={}; post=[]
    stack=[(root,False,0)]
    while stack:
        v,exit,d=stack.pop()
        if exit:post.append(v);continue
        require(v not in reached,'cycle or reused tree node')
        require(0<=v<len(nodes),'invalid child ID')
        reached.add(v);depths[v]=d;node=nodes[v]
        require(0<=node.lo<node.hi<=len(order),'invalid node interval')
        require(len(node.children) in (0,2),'tree must be proper binary')
        stack.append((v,True,d))
        if node.children:
            a,b=node.children
            require(0<=a<len(nodes) and 0<=b<len(nodes),'invalid children')
            an,bn=nodes[a],nodes[b]
            require(an.lo==node.lo and an.hi==bn.lo and bn.hi==node.hi,'children do not partition rows')
            parents[a]=parents[b]=v
            stack.append((b,False,d+1));stack.append((a,False,d+1))
    require(len(reached)==len(nodes),'unreachable extra tree nodes')
    require(nodes[root].lo==0 and nodes[root].hi==len(order),'root not full')
    bad={};born={};bweight={}; fixed={}
    prefix=[0]
    for i in order:prefix.append(prefix[-1]+lw[i])
    for v in post:
        node=nodes[v]
        fixed[v]=header+prefix[node.hi]-prefix[node.lo]
        if not node.children:
            patterns=[exceptions[i] for i in order[node.lo:node.hi]]
            require(all(p==patterns[0] for p in patterns),'nonuniform terminal row group')
            bad[v]=set(patterns[0])
        else:
            bad[v]=set()
            for c in node.children:bad[v].update(bad[c])
    for v in reached:
        born[v]=(set(right)-bad[v]) if v==root else (bad[parents[v]]-bad[v])
        bweight[v]=sum(rw[j] for j in born[v])
    table={}; by_node=defaultdict(list)
    required_fields={'node','weight','cost','blocks','take'}
    for row in transfer.states:
        require(isinstance(row,dict) and set(row)==required_fields,'invalid DP state schema')
        require(type(row['node']) is int and type(row['weight']) is int,
                'noninteger DP key')
        key=(row['node'],row['weight'])
        require(key not in table and key[0] in reached,'duplicate or invalid DP state')
        require(key[1]>=0,'invalid DP weight')
        require(type(row['cost']) is int and type(row['blocks']) is int and
                row['cost']>=0 and row['blocks']>=0,'invalid DP value')
        require(type(row['take']) is bool,'nonboolean decision')
        table[key]=row
        by_node[key[0]].append((key,row))
    def value(v,k):
        require((v,k) in table,'missing DP child state')
        row=table[v,k]
        return row['cost'],row['blocks']
    # Children are checked first, so a consistent table is an induction certificate.
    for v in post:
        node=nodes[v]
        for (sv,k),row in by_node[v]:
            if not node.children:
                expected=(fixed[v]+k,1) if k else (0,0)
                take=bool(k)
            else:
                vals=[value(c,k+bweight[c]) for c in node.children]
                no=(sum(x[0] for x in vals),sum(x[1] for x in vals))
                if k:
                    vals=[value(c,bweight[c]) for c in node.children]
                    yes=(fixed[v]+k+sum(x[0] for x in vals),1+sum(x[1] for x in vals))
                    take=yes<=no;expected=yes if take else no
                else:take=False;expected=no
            require(value(v,k)==expected and row['take']==take,'false optimality recurrence')
    required=set(); agenda=[(root,bweight[root])]
    while agenda:
        v,k=agenda.pop()
        if (v,k) in required:continue
        required.add((v,k))
        require((v,k) in table,'missing reachable DP state')
        for child in nodes[v].children:
            agenda.append((child,k+bweight[child]))
            if k:agenda.append((child,bweight[child]))
    require(required==set(table),'extraneous DP state')
    require(len(required)<=sum(d+1 for d in depths.values()),'ancestry state bound')
    optimum=value(root,bweight[root])
    blocks=[];decisions={};right_order={j:k for k,j in enumerate(right)}
    stack=[(root,born[root])]
    while stack:
        v,columns=stack.pop();node=nodes[v];k=sum(rw[j] for j in columns)
        require((v,k) in table,'missing reconstruction state')
        take=table[v,k]['take'];decisions[v]=take
        if take:
            blocks.append((order[node.lo:node.hi],
                           tuple(sorted(columns,key=right_order.__getitem__))))
            columns=set()
        for child in reversed(node.children):
            require(not columns.intersection(born[child]),'column born twice on a path')
            stack.append((child,columns|born[child]))
    require(all(hasattr(b,'left') and hasattr(b,'right') for b in transfer.blocks),
            'malformed packet block')
    supplied=[(tuple(b.left),tuple(b.right)) for b in transfer.blocks]
    require(len(supplied)==len(blocks),'packet block count differs')
    for (a,b),(ea,eb) in zip(supplied,blocks):
        require(tuple(a)==tuple(ea) and tuple(b)==tuple(eb) and
                len(set(b))==len(b),
                'packet differs from certified normal form')
    require(all(type(k) is int and type(v) is bool for k,v in transfer.decisions.items()),
            'invalid decision map')
    require(transfer.decisions==decisions,'decision certificate differs from packet traversal')
    actual=sum(header+sum(lw[i] for i in a)+sum(rw[j] for j in b) for a,b in blocks)
    require((actual,len(blocks))==optimum and actual==transfer.cost,'false packet cost')
    return {'cost':actual,'states':len(table),'blocks':len(blocks),'checked':True,
            'height':max(depths.values())}
