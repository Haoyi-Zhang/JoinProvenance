"""The maximal-safe baseline consumes the same physical dictionary as the DP."""
import itertools
import unittest
from collections import Counter

from provenance.hierarchy_campaign import greedy
from provenance.laminar import Hierarchy, TreeNode, weighted_cost
from provenance.rectangles import polynomial


class GreedyNumberingTests(unittest.TestCase):
    def test_root_first_ids_and_noncanonical_source_order(self):
        left, right = (20, 10), (9, 1, 7)
        tree = Hierarchy(left, (TreeNode(0, 2, (1, 2)),
                               TreeNode(0, 1, ()), TreeNode(1, 2, ())), 0)
        holes = {(20, 1), (10, 7)}
        blocks = greedy(left, right, holes, tree)
        expected = Counter({(i, j): 1 for i in left for j in right if (i, j) not in holes})
        self.assertEqual(polynomial(blocks), expected)
        self.assertEqual(weighted_cost(blocks, dict.fromkeys(left, 1), dict.fromkeys(right, 1)), 7)

    def test_all_numberings_preserve_partition_and_cost(self):
        left, right = (20, 10, 30), (9, 1, 7)
        nodes = (TreeNode(0, 1, ()), TreeNode(1, 2, ()), TreeNode(2, 3, ()),
                 TreeNode(1, 3, (1, 2)), TreeNode(0, 3, (0, 3)))
        holes = {(20, 1), (10, 7), (30, 9)}
        original = greedy(left, right, holes, Hierarchy(left, nodes, 4))
        expected = polynomial(original)
        weights = (dict.fromkeys(left, 1), dict.fromkeys(right, 1))
        cost = weighted_cost(original, *weights)
        for order in itertools.permutations(range(len(nodes))):
            renumber = {old: new for new, old in enumerate(order)}
            shuffled = tuple(TreeNode(nodes[old].lo, nodes[old].hi,
                                      tuple(renumber[c] for c in nodes[old].children))
                             for old in order)
            blocks = greedy(left, right, holes, Hierarchy(left, shuffled, renumber[4]))
            self.assertEqual(polynomial(blocks), expected)
            self.assertEqual(weighted_cost(blocks, *weights), cost)

    def test_tall_dictionary_does_not_use_python_recursion(self):
        size = 1101
        left = tuple(range(size))
        nodes = [TreeNode(i, i + 1, ()) for i in left]
        root = size - 1
        for i in range(size - 2, -1, -1):
            nodes.append(TreeNode(i, size, (i, root)))
            root = len(nodes) - 1
        holes = {(i, i % 2) for i in left}
        blocks = greedy(left, (0, 1), holes, Hierarchy(left, tuple(nodes), root))
        self.assertEqual(polynomial(blocks), Counter({(i, 1 - i % 2): 1 for i in left}))


if __name__ == '__main__':
    unittest.main()
