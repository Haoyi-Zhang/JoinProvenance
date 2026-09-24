"""Insert-only, fail-free, atomic-emission equijoin interpreter.

The target retains base inputs for future arrivals and positive pending blocks,
not the sink history. The sink Counter is an external test observer. There is
no network, database connection, concurrency, deletion or crash protocol.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import dataclass
from .rectangles import Block, polynomial, row_partition, column_partition, remove_pair

@dataclass(frozen=True)
class TupleRecord:
    identity: int
    key: int
    value: int

class Engine:
    def __init__(self):
        self.left: dict[int,TupleRecord] = {}
        self.right: dict[int,TupleRecord] = {}
        self.pending: list[Block] = []
        self.epoch = 0

    def insert_epoch(self, left: list[TupleRecord], right: list[TupleRecord], bound: int):
        if len(left)+len(right) > bound:
            raise ValueError('drift budget exceeded')
        if len({x.identity for x in left}) != len(left) or any(x.identity in self.left for x in left):
            raise ValueError('reused left identity')
        if len({x.identity for x in right}) != len(right) or any(x.identity in self.right for x in right):
            raise ValueError('reused right identity')
        # Old-left x new-right and new-left x all-right are disjoint.
        old_left = dict(self.left)
        self.right.update({x.identity:x for x in right})
        for key in sorted({x.key for x in right}):
            a = tuple(i for i,x in old_left.items() if x.key == key)
            b = tuple(x.identity for x in right if x.key == key)
            if a and b:
                self.pending.append(Block(a,b))
        self.left.update({x.identity:x for x in left})
        for key in sorted({x.key for x in left}):
            a = tuple(x.identity for x in left if x.key == key)
            b = tuple(i for i,x in self.right.items() if x.key == key)
            if a and b:
                self.pending.append(Block(a,b))
        self.epoch += 1

    def migrate(self, orientation: str):
        before = polynomial(self.pending)
        if any(v != 1 for v in before.values()):
            raise ValueError('source ownership already invalid')
        if orientation == 'row':
            after = row_partition(before)
        elif orientation == 'column':
            after = column_partition(before)
        else:
            raise ValueError('unknown physical orientation')
        self.install(after, before)

    def install(self, after: list[Block], expected: Counter):
        actual = polynomial(after)
        if actual != expected or any(v != 1 for v in actual.values()):
            raise ValueError('transfer changes exact residual provenance')
        for i,j in actual:
            if i not in self.left or j not in self.right or self.left[i].key != self.right[j].key:
                raise ValueError('invalid join derivation')
        self.pending = after

    def emit(self, pair: tuple[int,int]) -> tuple[int,int]:
        self.pending = remove_pair(self.pending,pair)
        # Publication and retirement are one abstract atomic transition.
        return pair

    def reference(self) -> Counter:
        # Independent specification: direct input join, not pending blocks.
        return Counter({(a.identity,b.identity):1 for a in self.left.values()
                        for b in self.right.values() if a.key == b.key})

    def check(self, sink: Counter):
        pending=polynomial(self.pending)
        if any(v != 1 for v in pending.values()) or any(v != 1 for v in sink.values()):
            raise AssertionError('coefficient multiplicity failed')
        if sink + pending != self.reference():
            raise AssertionError('conservation failed')
