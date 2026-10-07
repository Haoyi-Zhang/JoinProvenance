"""Portable untimed pure compiler regression; explicit, not test_* discovery.

Literal oracle enumerates column subsets/partitions, not the laminar recurrence.
No historical copies, private paths, campaign imports, resource substitutes,
subprocesses, network, files written, timers, or dependencies beyond stdlib.
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

from provenance.laminar import Hierarchy, TreeNode, build_hierarchy, compile_transfer
from provenance.certificate import verify_transfer
from provenance.oracle import minimum_costs
from provenance.regions import RegionEngine
from provenance.engine import TupleRecord

COUNTS = {}


def count(key):
    COUNTS[key] = COUNTS.get(key, 0) + 1


def literal_partition(left, right, pending, clusters, lw, rw, header):
    """All legal rectangles, then exact disjoint partition of a literal relation."""
    pairs = list(product(left, right))
    if len(pairs) > 16:
        raise ValueError("test-local literal oracle admits at most 16 cells")
    bit = {pair: 1 << index for index, pair in enumerate(pairs)}
    target = sum(bit[pair] for pair in pending)
    rectangles = []
    for rows in clusters:
        for subset in range(1, 1 << len(right)):
            columns = [right[j] for j in range(len(right)) if subset & (1 << j)]
            rectangle = set(product(rows, columns))
            if rectangle <= pending:
                cost = header + sum(lw[i] for i in rows) + sum(rw[j] for j in columns)
                rectangles.append((sum(bit[pair] for pair in rectangle), cost))

    @lru_cache(None)
    def solve(remaining):
        if not remaining:
            return 0, 0
        first = remaining & -remaining
        candidates = []
        for mask, cost in rectangles:
            if mask & first and mask & remaining == mask:
                tail = solve(remaining ^ mask)
                candidates.append((cost + tail[0], 1 + tail[1]))
        if not candidates:
            raise ValueError("reference support has no allowed positive partition")
        return min(candidates)

    return solve(target)


def tree(left, shape):
    """Small declared tree shape, independently indexed into interval nodes."""
    order, nodes = [], []

    def visit(branch):
        start = len(order)
        if isinstance(branch, int):
            order.append(left[branch])
            children = ()
        else:
            children = tuple(visit(child) for child in branch)
        nodes.append(TreeNode(start, len(order), children))
        return len(nodes) - 1

    root = visit(shape)
    return Hierarchy(tuple(order), tuple(nodes), root)


def regimes(left, right):
    return [dict(header=0, left_weights=dict.fromkeys(left, 1), right_weights=dict.fromkeys(right, 1)),
            dict(header=7, left_weights={i: 2 + 3 * k for k, i in enumerate(left)},
                 right_weights={j: 1 + 5 * k for k, j in enumerate(right)}),
            dict(header=2**90, left_weights={i: 2**100 + k for k, i in enumerate(left)},
                 right_weights={j: 2**95 + 2 * k for k, j in enumerate(right)})]


def finite_cases():
    for m in range(1, 4):
        shapes = [0] if m == 1 else [(0, 1)] if m == 2 else [((0, 1), 2), (0, (1, 2)), ((0, 2), 1)]
        for n in range(1, 4):
            left, right = (20, 10, 30)[:m], (9, 1, 7)[:n]
            pairs = list(product(left, right))
            for shape in shapes:
                hierarchy = tree(left, shape)
                for weights in regimes(left, right):
                    for mask in range(1 << len(pairs)):
                        holes = {pair for index, pair in enumerate(pairs) if not mask & (1 << index)}
                        yield left, right, holes, hierarchy, weights
    left, right = (20, 10, 30, 40), (9, 1, 7, 3)
    pairs = list(product(left, right))
    for shape in (((0, 1), (2, 3)), (((0, 1), 2), 3)):
        hierarchy = tree(left, shape)
        for weights in regimes(left, right):
            for mask in (0, 65535, 0x8421, 0x7BDE, 0xF00F, 0xA5A5, 0x3333, 0x5555):
                holes = {pair for index, pair in enumerate(pairs) if not mask & (1 << index)}
                yield left, right, holes, hierarchy, weights


def literal_state_keys(left, right, holes, hierarchy, rw):
    """Enumerate every ancestor-boundary suffix; no producer closure helper."""
    clusters = [set(hierarchy.order[node.lo:node.hi]) for node in hierarchy.nodes]
    bad = [{j for i, j in holes if i in rows} for rows in clusters]
    parents = {child: parent for parent, node in enumerate(hierarchy.nodes) for child in node.children}
    births = [set(right) - bad[v] if v == hierarchy.root else bad[parents[v]] - bad[v]
              for v in range(len(hierarchy.nodes))]
    keys = set()
    for v in range(len(hierarchy.nodes)):
        path = [v]
        while path[-1] in parents:
            path.append(parents[path[-1]])
        path.reverse()
        for boundary in range(len(path)):
            columns = set().union(*(births[node] for node in path[boundary:]))
            keys.add((v, sum(rw[j] for j in columns)))
    return keys


def snapshot(packet):
    # Retain record and traversal order as well as every scientific scalar.
    return {"order": packet.order, "nodes": [(n.lo, n.hi, n.children) for n in packet.nodes],
            "root": packet.root, "blocks": [(b.left, b.right) for b in packet.blocks],
            "cost": packet.cost, "states": copy.deepcopy(packet.states),
            "decisions": list(packet.decisions.items()), "metrics": packet.metrics.copy()}


def certificate_mutants(packet):
    for field in ("order", "nodes", "root", "blocks", "cost", "states", "decisions"):
        damaged = copy.deepcopy(packet)
        delattr(damaged, field)
        yield "missing-packet-" + field, damaged
    for index, _ in enumerate(packet.states):
        for field in ("node", "weight", "cost", "blocks", "take"):
            damaged = copy.deepcopy(packet)
            del damaged.states[index][field]
            yield f"missing-row-{index}-{field}", damaged
        for field, value in (("node", True), ("weight", -1), ("cost", True),
                             ("blocks", -1), ("take", 0)):
            damaged = copy.deepcopy(packet)
            damaged.states[index][field] = value
            yield f"bad-row-{index}-{field}", damaged
    for label, alter in (("false-cost", lambda p: setattr(p, "cost", p.cost + 1)),
                         ("missing-state", lambda p: p.states.pop()),
                         ("duplicate-state", lambda p: p.states.append(p.states[0].copy())),
                         ("wrong-decision", lambda p: p.decisions.__setitem__(p.root, not p.decisions[p.root])),
                         ("missing-block", lambda p: p.blocks.pop()),
                         ("duplicate-block", lambda p: p.blocks.append(p.blocks[0]))):
        damaged = copy.deepcopy(packet)
        alter(damaged)
        yield label, damaged


def compiler_errors():
    for weights in ({"header": True}, {"header": -1}, {"header": 0.5}, {"header": "0"},
                    {"left_weights": {0: 0}}, {"right_weights": {0: True}},
                    {"left_weights": {1: 1}}, {"right_weights": {}}):
        yield (0,), (0,), [], weights
    for left, right, holes in (((0, 0), (0,), []), ((0,), (0, 0), []),
                               ((0,), (0,), [(0, 0), (0, 0)]), ((0,), (0,), [(1, 0)]),
                               ((0,), (0,), [(0, 1)]), ((), (0,), [(0, 0)])):
        yield left, right, holes, {}
    yield (0, 1), (0, 1), {(0, 0)}, {"hierarchy": Hierarchy((0, 1), (TreeNode(0, 2, ()),), 0)}
    yield (0, 1), (0,), [], {"hierarchy": Hierarchy((0, 1), (TreeNode(0, 1, ()),), 0)}


class SubtotalRegression(unittest.TestCase):
    def test_literal_finite_partitions_states_and_coefficients(self):
        for left, right, holes, hierarchy, weights in finite_cases():
            packet = compile_transfer(left, right, holes, hierarchy=hierarchy, **weights)
            stats = verify_transfer(left, right, holes, packet, hierarchy=hierarchy, **weights)
            pending = set(product(left, right)) - holes
            clusters = [hierarchy.order[node.lo:node.hi] for node in hierarchy.nodes]
            expected = literal_partition(left, right, pending, clusters,
                                         weights["left_weights"], weights["right_weights"], weights["header"])
            self.assertEqual((packet.cost, len(packet.blocks)), expected)
            actual = Counter(pair for block in packet.blocks for pair in product(block.left, block.right))
            self.assertEqual(actual, Counter({pair: 1 for pair in pending}))
            self.assertEqual({(row["node"], row["weight"]) for row in packet.states},
                             literal_state_keys(left, right, holes, hierarchy, weights["right_weights"]))
            self.assertEqual(stats["states"], len(packet.states))
            self.assertEqual(stats["cost"], expected[0])
            self.assertEqual(stats["blocks"], expected[1])
            self.assertEqual(packet.metrics["states"], len(packet.states))
            count("weighted_finite_cases")

    def test_complete_tie_zero_uniform_and_tall_tree(self):
        left, right, holes = (0, 1), (9, 1), {(1, 1)}
        hierarchy = tree(left, (0, 1))
        packet = compile_transfer(left, right, holes, hierarchy=hierarchy)
        self.assertEqual((packet.cost, len(packet.blocks)), (5, 2))
        self.assertTrue(next(row for row in packet.states if row["node"] == packet.root)["take"])
        for left, right, holes in (
                ((), (), []), ((), (0,), []), ((0,), (), []),
                ((0, 1), (9, 1), list(product((0, 1), (9, 1)))),
                ((0, 1, 2, 3), (9, 1), [(2, 1), (3, 1)])):
            hierarchy = build_hierarchy(left, holes)
            packet = compile_transfer(left, right, holes, hierarchy=hierarchy)
            self.assertTrue(verify_transfer(left, right, holes, packet, hierarchy=hierarchy)["checked"])
            count("empty_uniform_cases")
        hierarchy = Hierarchy((0, 1), (TreeNode(0, 2, ()),), 0)
        packet = compile_transfer((0, 1), (9, 1), [(0, 1), (1, 1)], hierarchy=hierarchy)
        self.assertEqual(packet.cost, 3)
        self.assertTrue(verify_transfer((0, 1), (9, 1), [(0, 1), (1, 1)], packet, hierarchy=hierarchy)["checked"])
        count("uniform_nonempty_frontier")
        m = 1101
        nodes = [TreeNode(0, 1, ())]
        root = 0
        for index in range(1, m):
            leaf = len(nodes)
            nodes.append(TreeNode(index, index + 1, ()))
            nodes.append(TreeNode(0, index + 1, (root, leaf)))
            root = len(nodes) - 1
        hierarchy = Hierarchy(tuple(range(m)), tuple(nodes), root)
        packet = compile_transfer(hierarchy.order, (9,), [], hierarchy=hierarchy)
        self.assertEqual(packet.cost, m + 1)
        self.assertEqual(packet.metrics["height"], m - 1)
        self.assertTrue(verify_transfer(hierarchy.order, (9,), [], packet, hierarchy=hierarchy)["checked"])
        count("tall_tree")

    def test_malformed_inputs_and_certificates(self):
        for left, right, holes, weights in compiler_errors():
            with self.assertRaises(ValueError):
                compile_transfer(left, right, holes, **weights)
            count("compiler_errors")
        left, right, holes = (20, 10, 30, 40), (9, 1, 7), {(20, 1), (10, 7), (30, 1)}
        hierarchy = tree(left, ((0, 1), (2, 3)))
        packet = compile_transfer(left, right, holes, hierarchy=hierarchy)
        for label, damaged in certificate_mutants(packet):
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    verify_transfer(left, right, holes, damaged, hierarchy=hierarchy)
                count("certificate_mutants")

    def test_oracle_caps_and_exact_large_total(self):
        with self.assertRaisesRegex(ValueError, "16 cells"):
            minimum_costs(tuple(range(17)), (0,), [(i,) for i in range(17)], dict.fromkeys(range(17), 1), {0: 1}, 0)
        with self.assertRaisesRegex(ValueError, "oracle cost admission bound"):
            minimum_costs((0,), (0,), [(0,)], {0: 10**99}, {0: 1}, 0)
        left = tuple(range(12))
        weights = dict(header=0, left_weights=dict.fromkeys(left, 9 * 10**98), right_weights={0: 1})
        hierarchy = build_hierarchy(left, [], singleton_leaves=True)
        packet = compile_transfer(left, (0,), [(i, 0) for i in left[1:]], hierarchy=hierarchy, **weights)
        self.assertIs(type(packet.cost), int)
        self.assertTrue(verify_transfer(left, (0,), [(i, 0) for i in left[1:]], packet, hierarchy=hierarchy, **weights)["checked"])
        costs, _ = minimum_costs(left, (0,), [(i,) for i in left], weights["left_weights"], {0: 1}, 0)
        self.assertEqual(costs[-1], (12 * (9 * 10**98 + 1), 12))
        self.assertGreater(costs[-1][0], 10**100)
        full_packet = compile_transfer(left, (0,), [], hierarchy=hierarchy, **weights)
        self.assertEqual(full_packet.cost, 12 * (9 * 10**98) + 1)
        self.assertGreater(full_packet.cost, 10**100)
        self.assertTrue(verify_transfer(left, (0,), [], full_packet, hierarchy=hierarchy, **weights)["checked"])
        count("oracle_cap_groups")

    def test_sequential_insert_acknowledge_and_migration(self):
        engine, sink = RegionEngine(), Counter()
        batches = [([TupleRecord(0, 0, 9), TupleRecord(1, 1, 9)], [TupleRecord(0, 0, 9)], 3),
                   ([TupleRecord(2, 0, 9)], [TupleRecord(1, 0, 9), TupleRecord(2, 1, 9)], 3),
                   ([], [], 0)]
        for left, right, bound in batches:
            engine.insert_epoch(left, right, bound)
            engine.check(sink)
            count("sequential_checks")
            for method in ("laminar", "row", "column", "laminar"):
                before = engine.pending()
                engine.migrate(method)
                self.assertEqual(engine.pending(), before)
                engine.check(sink)
                count("sequential_checks")
            pending = sorted(engine.pending())
            if pending:
                sink[engine.emit(pending[0])] += 1
                engine.check(sink)
                count("sequential_checks")
        for pair in sorted(engine.pending()):
            sink[engine.emit(pair)] += 1
            engine.check(sink)
            count("sequential_checks")
        self.assertEqual(sink, engine.reference())


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SubtotalRegression))
    print(json.dumps({"tests": result.testsRun, "successful": result.wasSuccessful(), "finite_counts": COUNTS}, sort_keys=True))
    sys.exit(0 if result.wasSuccessful() else 1)
