"""A migration interpreter with disjoint regions and sparse local frontiers."""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass, field
from .rectangles import Block, polynomial, sparse_complement, row_complement
from .engine import TupleRecord

@dataclass
class Region:
    block: Block
    emitted: set[tuple[int,int]] = field(default_factory=set)

    def remaining(self):
        for pair in self.block.pairs():
            if pair not in self.emitted:
                yield pair

class RegionEngine:
    def __init__(self):
        self.left: dict[int,TupleRecord] = {}
        self.right: dict[int,TupleRecord] = {}
        self.regions: list[Region] = []
        self.epoch = 0

    def pending(self) -> Counter:
        # Observer/checker only. sparse migration itself never expands pairs.
        c = Counter()
        for region in self.regions:
            c.update(region.remaining())
        return c

    def reference(self) -> Counter:
        return Counter({(i,j):1 for i,x in self.left.items()
                        for j,y in self.right.items() if x.key == y.key})

    def check(self, sink: Counter):
        p = self.pending()
        if p + sink != self.reference():
            raise AssertionError('region conservation fails')
        if any(v != 1 for v in p.values()) or any(v != 1 for v in sink.values()):
            raise AssertionError('nonunique derivation owner')

    def insert_epoch(self, left: list[TupleRecord], right: list[TupleRecord], bound: int):
        if len(left)+len(right)>bound:
            raise ValueError('drift budget exceeded')
        for batch,old in [(left,self.left),(right,self.right)]:
            if len({r.identity for r in batch}) != len(batch) or any(r.identity in old for r in batch):
                raise ValueError('reused base identity')
        old_left = dict(self.left)
        self.right.update({x.identity:x for x in right})
        for key in sorted({x.key for x in right}):
            a = tuple(i for i,x in old_left.items() if x.key == key)
            b = tuple(x.identity for x in right if x.key == key)
            if a and b:
                self.regions.append(Region(Block(a,b)))
        self.left.update({x.identity:x for x in left})
        for key in sorted({x.key for x in left}):
            a = tuple(x.identity for x in left if x.key == key)
            b = tuple(i for i,x in self.right.items() if x.key == key)
            if a and b:
                self.regions.append(Region(Block(a,b)))
        self.epoch += 1

    def emit(self, pair: tuple[int,int]) -> tuple[int,int]:
        i,j = pair
        owners = [r for r in self.regions if i in r.block.left and j in r.block.right and pair not in r.emitted]
        if len(owners) != 1:
            raise ValueError('emission must have one pending owner')
        owners[0].emitted.add(pair)
        return pair

    def migrate(self, method: str):
        if method not in {'sparse', 'row', 'column', 'laminar'}:
            raise ValueError('unknown migration method')
        converted = []
        for region in self.regions:
            a,b = region.block.left,region.block.right
            if method == 'laminar':
                from .laminar import build_hierarchy, compile_transfer
                from .certificate import verify_transfer
                # The source dictionary is frozen before the untrusted packet.
                hierarchy = build_hierarchy(a,region.emitted)
                packet = compile_transfer(a,b,region.emitted,hierarchy=hierarchy)
                verify_transfer(a,b,region.emitted,packet,hierarchy=hierarchy)
                blocks=packet.blocks
            elif method == 'sparse':
                blocks = sparse_complement(a,b,region.emitted)
            elif method == 'row':
                blocks = row_complement(a,b,region.emitted)
            elif method == 'column':
                blocks = [Block(x.right,x.left) for x in
                          sparse_complement(b,a,((j,i) for i,j in region.emitted))]
            else:
                raise ValueError('unknown migration method')
            converted.extend(Region(block) for block in blocks)
        # Install occurs only after the new regions have been constructed.
        self.regions = converted
