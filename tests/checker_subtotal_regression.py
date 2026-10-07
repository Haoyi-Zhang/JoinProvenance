"""Portable, untimed checker regression with a literal weighted partition oracle.

No historical implementation, private paths, timers, campaign execution, network,
child processes or third-party dependencies. Run explicitly, not test_* discovery.
"""
from __future__ import annotations
import copy
from collections import Counter
from functools import lru_cache
from itertools import product
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from provenance.laminar import Hierarchy, TreeNode, compile_transfer, build_hierarchy
from provenance.certificate import verify_transfer

COUNTS = {}


def count(name):
    COUNTS[name] = COUNTS.get(name, 0) + 1


def tree(left, shape):
    order, nodes = [], []
    def visit(branch):
        lo = len(order)
        if type(branch) is int:
            order.append(left[branch]); children = ()
        else:
            children = tuple(visit(part) for part in branch)
        nodes.append(TreeNode(lo, len(order), children))
        return len(nodes) - 1
    root = visit(shape)
    return Hierarchy(tuple(order), tuple(nodes), root)


def literal_optimum(left, right, holes, hierarchy, weights):
    """Enumerate literal rectangles and exact disjoint covers; no DP recurrence."""
    pairs = list(product(left, right))
    if len(pairs) > 12:
        raise ValueError("test oracle admits at most 12 cells")
    bits = {pair: 1 << k for k, pair in enumerate(pairs)}
    pending = set(pairs) - set(holes)
    full = sum(bits[pair] for pair in pending)
    candidates = []
    for node in hierarchy.nodes:
        rows = hierarchy.order[node.lo:node.hi]
        for mask in range(1, 1 << len(right)):
            columns = tuple(j for k, j in enumerate(right) if mask & (1 << k))
            cells = set(product(rows, columns))
            if cells <= pending:
                cost = (weights['header'] + sum(weights['left_weights'][i] for i in rows)
                        + sum(weights['right_weights'][j] for j in columns))
                candidates.append((sum(bits[pair] for pair in cells), cost))
    @lru_cache(None)
    def cover(mask):
        if mask == 0:
            return 0, 0
        first = mask & -mask
        answers = []
        for rectangle, cost in candidates:
            if rectangle & first and rectangle & mask == rectangle:
                tail = cover(mask ^ rectangle)
                answers.append((cost + tail[0], 1 + tail[1]))
        if not answers:
            raise ValueError("literal support has no legal partition")
        return min(answers)
    return cover(full)


def cases():
    for m in (1, 2, 3):
        shapes = [0] if m == 1 else [(0, 1)] if m == 2 else [((0, 1), 2), (0, (2, 1))]
        for n in (1, 2, 3):
            left, right = (20, 10, 30)[:m], (9, 1, 7)[:n]
            pairs = list(product(left, right))
            for shape in shapes:
                hierarchy = tree(left, shape)
                for regime in (0, 1, 2):
                    weights = dict(header=(0, 7, 2**150)[regime],
                                   left_weights={i: (1, 2 + k, 2**200 + k)[regime] for k, i in enumerate(left)},
                                   right_weights={j: (1, 2 + 5*k, 2**180 + 3*k)[regime] for k, j in enumerate(right)})
                    for mask in range(1 << len(pairs)):
                        holes = {pair for k, pair in enumerate(pairs) if not mask & (1 << k)}
                        yield left, right, holes, hierarchy, weights


def multiweight_case():
    left, right = (20, 10, 30, 40), (9, 1, 7)
    holes = {(30, 1), (40, 1), (10, 7), (30, 7), (40, 7)}
    hierarchy = tree(left, ((0, 1), (2, 3)))
    weights = dict(header=0, left_weights=dict.fromkeys(left, 1), right_weights={9: 2, 1: 5, 7: 13})
    return left, right, holes, hierarchy, weights


def packet_for(case):
    left, right, holes, hierarchy, weights = case
    return compile_transfer(left, right, holes, hierarchy=hierarchy, **weights)


def check_case(case, packet, checker=verify_transfer):
    left, right, holes, hierarchy, weights = case
    return checker(left, right, holes, packet, hierarchy=hierarchy, **weights)


def mutants(packet):
    for index in range(len(packet.states)):
        for field, value in (('cost', packet.states[index]['cost'] + 1),
                             ('blocks', packet.states[index]['blocks'] + 1),
                             ('take', not packet.states[index]['take'])):
            damaged = copy.deepcopy(packet); damaged.states[index][field] = value
            yield f'row-{index}-{field}', damaged
        for field in ('node', 'weight', 'cost', 'blocks', 'take'):
            damaged = copy.deepcopy(packet); del damaged.states[index][field]
            yield f'missing-row-{index}-{field}', damaged
        damaged = copy.deepcopy(packet); damaged.states.pop(index)
        yield f'missing-state-{index}', damaged
    for label, alter in (
            ('duplicate-state', lambda p: p.states.append(p.states[0].copy())),
            ('extra-state', lambda p: p.states.append(dict(node=p.root, weight=10**70, cost=0, blocks=0, take=False))),
            ('false-packet-cost', lambda p: setattr(p, 'cost', p.cost + 1)),
            ('wrong-decision', lambda p: p.decisions.__setitem__(p.root, not p.decisions[p.root])),
            ('missing-block', lambda p: p.blocks.pop()),
            ('duplicate-block', lambda p: p.blocks.append(p.blocks[0])),
            ('bad-value', lambda p: p.states[0].__setitem__('cost', True)),
            ('bad-key', lambda p: p.states[0].__setitem__('node', True)),
            ('bad-take', lambda p: p.states[0].__setitem__('take', 1)),
            ('bad-weight', lambda p: p.states[0].__setitem__('weight', -1)),
            ('bad-container', lambda p: setattr(p, 'states', tuple(p.states))),
            ('missing-packet-field', lambda p: delattr(p, 'states'))):
        damaged = copy.deepcopy(packet); alter(damaged)
        yield label, damaged


class ReadingDict(dict):
    """Accepted dict subclass whose observable read sequence must be preserved."""
    def __init__(self, row):
        super().__init__(row); self.reads = []
    def __getitem__(self, key):
        self.reads.append(key)
        return super().__getitem__(key)


class CheckerSubtotalRegression(unittest.TestCase):
    def test_literal_weighted_partitions_and_all_stats(self):
        for case in cases():
            left, right, holes, hierarchy, weights = case
            packet = packet_for(case)
            before = copy.deepcopy(vars(packet))
            stats = check_case(case, packet)
            expected = literal_optimum(left, right, holes, hierarchy, weights)
            self.assertEqual((packet.cost, len(packet.blocks)), expected)
            coefficients = Counter(pair for b in packet.blocks for pair in product(b.left, b.right))
            self.assertEqual(coefficients, Counter({pair: 1 for pair in product(left, right) if pair not in holes}))
            self.assertEqual(stats, dict(cost=expected[0], states=len(packet.states), blocks=expected[1],
                                         checked=True, height=packet.metrics['height']))
            self.assertEqual(vars(packet), before)
            count('literal_weighted_cases')

    def test_multiweight_zero_tie_reordering_and_empty(self):
        case = multiweight_case(); packet = packet_for(case)
        positive = [row['weight'] for row in packet.states if row['node'] == 2 and row['weight'] > 0]
        self.assertGreaterEqual(len(set(positive)), 2)
        expected = check_case(case, packet)
        for order in (list(reversed(packet.states)), sorted(packet.states, key=lambda row: (row['weight'], row['node']))):
            other = copy.deepcopy(packet); other.states = copy.deepcopy(order)
            self.assertEqual(check_case(case, other), expected); count('reordered_packets')
        left, right = (0, 1), (9, 1)
        hierarchy = tree(left, (0, 1))
        tie = compile_transfer(left, right, {(1, 1)}, hierarchy=hierarchy)
        self.assertEqual((tie.cost, len(tie.blocks)), (5, 2))
        self.assertTrue(next(row['take'] for row in tie.states if row['node'] == tie.root))
        self.assertTrue(verify_transfer(left, right, {(1, 1)}, tie, hierarchy=hierarchy)['checked'])
        for holes in (set(product(left, right)), set()):
            p = compile_transfer(left, right, holes, hierarchy=hierarchy)
            self.assertTrue(verify_transfer(left, right, holes, p, hierarchy=hierarchy)['checked'])
            if holes:
                self.assertTrue(all(row['weight'] == 0 for row in p.states)); self.assertEqual(p.cost, 0)
            count('zero_or_full_cases')
        for a, b in (((), ()), ((), (9,)), ((20,), ())):
            h = build_hierarchy(a, [])
            p = compile_transfer(a, b, [], hierarchy=h)
            self.assertEqual(verify_transfer(a, b, [], p, hierarchy=h), dict(cost=0, states=0, blocks=0, checked=True))
            count('empty_cases')

    def test_every_row_including_losing_branches_and_mutants(self):
        case = multiweight_case(); packet = packet_for(case)
        for label, damaged in mutants(packet):
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    check_case(case, damaged)
            count('rejected_mutants')
        # A schema error must still precede recurrence, closure and packet errors.
        damaged = copy.deepcopy(packet); del damaged.states[-1]['take']; damaged.cost += 1
        with self.assertRaisesRegex(ValueError, '^invalid DP state schema$'):
            check_case(case, damaged)

    def test_dict_subclasses_remain_accepted(self):
        case = multiweight_case(); packet = packet_for(case)
        expected = check_case(case, packet)
        packet.states = [ReadingDict(row) for row in packet.states]
        self.assertEqual(check_case(case, packet), expected)
        self.assertTrue(all(row.reads for row in packet.states))
        count('subclass_packets')


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CheckerSubtotalRegression))
    print(json.dumps(dict(tests=result.testsRun, successful=result.wasSuccessful(), finite_counts=COUNTS), sort_keys=True))
    sys.exit(0 if result.wasSuccessful() else 1)
