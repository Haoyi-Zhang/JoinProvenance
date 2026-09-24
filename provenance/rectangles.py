"""Exact positive/Boolean rectangular decompositions of small binary matrices.

Bit i*n+j denotes the pending derivation x_i*y_j.  A positive block is a
Cartesian product without an internal exclusion predicate.  Input storage,
bitmap encodings, DAG gate complexity and physical bytes are not block width.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from math import comb
from typing import Iterable

@dataclass(frozen=True)
class Block:
    left: tuple[int, ...]
    right: tuple[int, ...]

    def pairs(self):
        for i in self.left:
            for j in self.right:
                yield i, j

    @property
    def memberships(self) -> int:
        return len(self.left) + len(self.right)


def polynomial(blocks: Iterable[Block]) -> Counter:
    """Coefficients, not merely a set of monomials; do not deduplicate."""
    answer = Counter()
    for b in blocks:
        if not b.left or not b.right:
            raise ValueError('empty factor in positive block')
        if len(set(b.left)) != len(b.left) or len(set(b.right)) != len(b.right):
            raise ValueError('duplicate identity inside a factor')
        answer.update(b.pairs())
    return answer


def row_partition(pairs: Iterable[tuple[int, int]]) -> list[Block]:
    rows: dict[int, set[int]] = {}
    for i, j in pairs:
        rows.setdefault(i, set()).add(j)
    groups: dict[tuple[int, ...], list[int]] = {}
    for i in sorted(rows):
        groups.setdefault(tuple(sorted(rows[i])), []).append(i)
    return [Block(tuple(a), b) for b, a in sorted(groups.items()) if b]


def column_partition(pairs: Iterable[tuple[int, int]]) -> list[Block]:
    return [Block(b.right, b.left) for b in row_partition((j, i) for i, j in pairs)]


def as_mask(pairs: Iterable[tuple[int, int]], m: int, n: int) -> int:
    ans = 0
    for i, j in pairs:
        if not (0 <= i < m and 0 <= j < n):
            raise ValueError('pair outside matrix')
        ans |= 1 << (i*n+j)
    return ans


def mask_pairs(mask: int, m: int, n: int):
    if mask < 0 or mask >= 1 << (m*n):
        raise ValueError('invalid mask')
    for i in range(m):
        for j in range(n):
            if (mask >> (i*n+j)) & 1:
                yield i, j


def rectangles(m: int, n: int) -> list[tuple[int, Block]]:
    result = []
    for a in range(1, 1 << m):
        aa = tuple(i for i in range(m) if (a >> i) & 1)
        for b in range(1, 1 << n):
            bb = tuple(j for j in range(n) if (b >> j) & 1)
            block = Block(aa, bb)
            result.append((as_mask(block.pairs(), m, n), block))
    return result


def all_optima(m: int, n: int):
    """One DAG shortest-path calculation for ALL m by n masks.

    dp[M] = fewest rectangles whose union is exactly M.  Positive transitions
    require a disjoint new rectangle; Boolean transitions allow overlap.
    No target-specific restriction is lost: a path ending at M never adds a
    cell outside M because union is monotone.  An ascending integer order
    is topological.  Limited to sixteen cells by an explicit admission gate.
    """
    if m < 1 or n < 1 or m*n > 16:
        raise ValueError('exact oracle admits 1..16 cells only')
    rs = rectangles(m,n)
    count = 1 << (m*n)
    positive, boolean = bytearray([m*n+1])*count, bytearray([m*n+1])*count
    positive[0] = boolean[0] = 0
    for mask in range(count):
        pv, bv = positive[mask]+1, boolean[mask]+1
        for rect, _ in rs:
            target = mask | rect
            if target == mask:
                continue
            if bv < boolean[target]:
                boolean[target] = bv
            if not (mask & rect) and pv < positive[target]:
                positive[target] = pv
    return positive, boolean


def optimal_blocks(mask: int, m: int, n: int, *, boolean=False) -> list[Block]:
    """Target-specific shortest path, with an independent predecessor witness."""
    if m*n > 16 or m < 1 or n < 1:
        raise ValueError('exact decoder admits 1..16 cells only')
    mask_pairs_check = list(mask_pairs(mask,m,n))
    rs = [(x,b) for x,b in rectangles(m,n) if x & mask == x]
    distance = {0: 0}
    pred: dict[int, tuple[int, Block]] = {}
    for state in range(mask+1):
        if state not in distance:
            continue
        for bits, block in rs:
            if not boolean and state & bits:
                continue
            new = state | bits
            if new != state and distance.get(new, m*n+1) > distance[state]+1:
                distance[new] = distance[state]+1
                pred[new] = state, block
    out = []
    current = mask
    while current:
        prev, block = pred[current]
        out.append(block)
        current = prev
    out.reverse()
    expanded = polynomial(out)
    target = Counter({p:1 for p in mask_pairs_check})
    if boolean:
        assert set(expanded) == set(target)
    else:
        assert expanded == target
    return out


def rational_rank(mask: int, m: int, n: int) -> int:
    """Fraction-free integer row elimination; exact rank over Q."""
    from math import gcd
    rows = [[(mask >> (i*n+j)) & 1 for j in range(n)] for i in range(m)]
    rank = 0
    for col in range(n):
        pivot = next((i for i in range(rank,m) if rows[i][col]), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        a = rows[rank][col]
        for i in range(rank+1,m):
            b = rows[i][col]
            if b:
                rows[i] = [a*x-b*y for x,y in zip(rows[i],rows[rank])]
                g = 0
                for x in rows[i]:
                    g = gcd(g,abs(x))
                if g > 1:
                    rows[i] = [x//g for x in rows[i]]
        rank += 1
        if rank == m:
            break
    return rank


def crown(n: int) -> list[tuple[int, int]]:
    return [(i,j) for i in range(n) for j in range(n) if i != j]


def crown_boolean_width(n: int) -> int:
    if n < 1:
        raise ValueError('n must be positive')
    if n == 1:
        return 0
    k = 1
    while comb(k,k//2) < n:
        k += 1
    return k


def crown_cover(n: int) -> list[Block]:
    k = crown_boolean_width(n)
    if not k:
        return []
    from itertools import islice
    codes = [set(c) for c in islice(combinations(range(k),k//2),n)]
    return [Block(tuple(i for i,s in enumerate(codes) if t in s),
                  tuple(j for j,s in enumerate(codes) if t not in s))
            for t in range(k)]


def remove_pair(blocks: list[Block], pair: tuple[int,int]) -> list[Block]:
    """Remove precisely one owned monomial; split its block disjointly."""
    i,j = pair
    out, owners = [], 0
    for b in blocks:
        if i not in b.left or j not in b.right:
            out.append(b)
            continue
        owners += 1
        a = tuple(x for x in b.left if x != i)
        c = tuple(y for y in b.right if y != j)
        if a:
            out.append(Block(a,b.right))
        if c:
            out.append(Block((i,),c))
    if owners != 1:
        raise ValueError(f'expected one owner, found {owners}')
    return out


def sparse_complement(left: tuple[int,...], right: tuple[int,...],
                      emitted: Iterable[tuple[int,int]]) -> list[Block]:
    """Compile a sparse exception frontier to disjoint positive rectangles.

    No Cartesian product is enumerated. Stable integer IDs are the factor
    elements. For d affected rows and e emitted pairs, h=ceil(log2 d), the
    output has <=2*d nonempty blocks and <=m+2*n+(d+2*e)*h memberships
    (for d=0, one block with m+n memberships). Empty sides produce no block.
    Expected-time hash-set operations; explicit lists, not shared DAGs.
    """
    if len(set(left)) != len(left) or len(set(right)) != len(right):
        raise ValueError('source factors contain duplicate IDs')
    if not left or not right:
        if any(True for _ in emitted):
            raise ValueError('emissions outside an empty region')
        return []
    ls, rs = set(left), set(right)
    forbidden: dict[int,set[int]] = {}
    seen = set()
    for pair in emitted:
        i,j = pair
        if i not in ls or j not in rs or pair in seen:
            raise ValueError('invalid or duplicate emission')
        seen.add(pair)
        forbidden.setdefault(i,set()).add(j)
    affected = tuple(i for i in left if i in forbidden)
    unaffected = tuple(i for i in left if i not in forbidden)
    if not affected:
        return [Block(left,right)]
    out = [Block(unaffected,right)] if unaffected else []

    def visit(rows: tuple[int,...], cols: tuple[int,...]):
        # Each forbidden pair participates in at most one node per level.
        bad = set()
        for i in rows:
            bad.update(forbidden[i])
        safe_cols = tuple(j for j in cols if j not in bad)
        bad_cols = tuple(j for j in cols if j in bad)
        if safe_cols:
            out.append(Block(rows,safe_cols))
        if len(rows) > 1 and bad_cols:
            middle = len(rows)//2
            visit(rows[:middle],bad_cols)
            visit(rows[middle:],bad_cols)
        # At a leaf all remaining columns are forbidden, hence discarded.
    visit(affected,right)
    return out


def row_complement(left: tuple[int,...], right: tuple[int,...],
                   emitted: Iterable[tuple[int,int]]) -> list[Block]:
    """Obvious exact baseline: compute each row's remaining right factor.
    Equal rows are grouped; construction can scan m*n candidate pairs.
    Inputs are validated so the baseline cannot silently ignore a malformed
    frontier or duplicate source identity.
    """
    left,right=tuple(left),tuple(right)
    if len(set(left)) != len(left) or len(set(right)) != len(right):
        raise ValueError('source factors contain duplicate IDs')
    ls,rs=set(left),set(right);seen=set();forbidden: dict[int,set[int]] = {}
    for pair in emitted:
        i,j=pair
        if pair in seen or i not in ls or j not in rs:
            raise ValueError('invalid or duplicate emission')
        seen.add(pair);forbidden.setdefault(i,set()).add(j)
    groups: dict[tuple[int,...],list[int]] = {}
    for i in left:
        cols = tuple(j for j in right if j not in forbidden.get(i,()))
        if cols:
            groups.setdefault(cols,[]).append(i)
    return [Block(tuple(rows),cols) for cols,rows in groups.items()]


def verify_partition_bits(left, right, emitted, blocks):
    """Independent exact checker using row bitsets, not the compiler recursion.

    Validation memory is O(m*n) bits; this is an observer, not migration state.
    It rejects overlaps before union, then compares each row with its exact
    complement. It does not use area equality as a proxy for provenance.
    """
    if len(set(left)) != len(left) or len(set(right)) != len(right):
        raise ValueError('duplicate source IDs')
    ix={v:i for i,v in enumerate(left)}; jx={v:j for j,v in enumerate(right)}
    expected=[(1 << len(right))-1 for _ in left]
    seen=set()
    for i,j in emitted:
        if (i,j) in seen or i not in ix or j not in jx:
            raise ValueError('invalid emission')
        seen.add((i,j)); expected[ix[i]] &= ~(1 << jx[j])
    owned=[0 for _ in left]
    for block in blocks:
        if not block.left or not block.right:
            raise ValueError('empty block')
        if len(set(block.left))!=len(block.left) or len(set(block.right))!=len(block.right):
            raise ValueError('repeated factor ID')
        bits=0
        for j in block.right:
            if j not in jx: raise ValueError('unknown column')
            bits |= 1 << jx[j]
        for i in block.left:
            if i not in ix: raise ValueError('unknown row')
            if owned[ix[i]] & bits: raise ValueError('multiple ownership')
            owned[ix[i]] |= bits
    if owned != expected:
        raise ValueError('missing, replayed, or spurious derivation')
    return True
