"""Small adversarial checks of the trusted hierarchy and installation boundary."""
import copy
import unittest
from collections import Counter
from unittest.mock import patch
from provenance.laminar import build_hierarchy, compile_transfer, weighted_cost, Hierarchy, TreeNode
from provenance.certificate import verify_transfer
from provenance.rectangles import polynomial, Block
from provenance.regions import RegionEngine
from provenance.engine import TupleRecord
from provenance.hierarchy_campaign import greedy

class HierarchyTests(unittest.TestCase):
    def check(self, left, right, holes, **weights):
        tree=build_hierarchy(left, holes)
        packet=compile_transfer(left,right,holes,hierarchy=tree,**weights)
        verify_transfer(left,right,holes,packet,hierarchy=tree,**weights)
        target=Counter({(i,j):1 for i in left for j in right if (i,j) not in set(map(tuple,holes))})
        self.assertEqual(polynomial(packet.blocks),target)
        return tree,packet

    def test_empty_factors_and_all_emitted(self):
        for a,b,e in [((),(),[]),((),(0,),[]),((0,),(),[]),((0,),(0,),[(0,0)])]:
            t,p=self.check(a,b,e)
            self.assertEqual(p.cost,0)

    def test_uniform_multirow_terminal(self):
        left=tuple(range(7));right=tuple(range(4));holes=[(4,1),(6,2)]
        t,p=self.check(left,right,holes)
        self.assertTrue(any(not v.children and v.hi-v.lo>1 for v in t.nodes))

    def test_json_list_frontier(self):
        self.check((0,1),(0,1),[[0,0],[1,1]])

    def test_supplied_uniform_nonempty_holes(self):
        tree=Hierarchy((0,1),(TreeNode(0,2,()),),0)
        holes=[(0,1),(1,1)]
        p=compile_transfer((0,1),(0,1,2),holes,hierarchy=tree)
        verify_transfer((0,1),(0,1,2),holes,p,hierarchy=tree)
        self.assertEqual(p.cost,4)

    def test_nonuniform_leaf_rejected(self):
        tree=Hierarchy((0,1),(TreeNode(0,2,()),),0)
        with self.assertRaises(ValueError):
            compile_transfer((0,1),(0,1),[(0,0)],hierarchy=tree)

    def test_invalid_weights_and_frontier(self):
        for kw in [{'header':-1},{'left_weights':{0:0}},{'right_weights':{0:-2}},
                   {'left_weights':{1:2}},{'header':0.5}]:
            with self.assertRaises(ValueError):compile_transfer((0,),(0,),[],**kw)
        for holes in [[(0,0),(0,0)],[(1,0)],[(0,1)]]:
            with self.assertRaises(ValueError):compile_transfer((0,),(0,),holes)

    def test_big_integers_exact(self):
        self.check((0,1),(0,1),[(0,0)],header=2**90,
                   left_weights={0:2**100,1:2**101},right_weights={0:2**95,1:2**96})

    def test_packet_cannot_choose_trusted_dictionary(self):
        a=tuple(range(4));b=(0,1);e=[]
        tree=build_hierarchy(a,e)
        p=compile_transfer(a,b,e,hierarchy=tree)
        other=build_hierarchy(a,e,singleton_leaves=True)
        with self.assertRaises(ValueError):verify_transfer(a,b,e,p,hierarchy=other)

    def test_rejection_preserves_source_regions(self):
        e=RegionEngine();sink=Counter()
        e.insert_epoch([TupleRecord(i,0,0) for i in range(2)],
                       [TupleRecord(i,0,0) for i in range(2)],4)
        before=copy.deepcopy(e.regions)
        real=compile_transfer
        def corrupt(*a,**kw):
            p=real(*a,**kw);p.cost+=1;return p
        with patch('provenance.laminar.compile_transfer',side_effect=corrupt):
            with self.assertRaises(ValueError):e.migrate('laminar')
        self.assertEqual(e.regions,before);e.check(sink)

    def test_repeated_switch_then_new_match(self):
        e=RegionEngine();sink=Counter()
        e.insert_epoch([TupleRecord(0,0,5)],[],1)
        for mode in ['laminar','column','row','laminar']:e.migrate(mode);e.check(sink)
        e.insert_epoch([],[TupleRecord(0,0,5)],1)
        sink[e.emit((0,0))]+=1;e.migrate('laminar');e.check(sink)
        self.assertEqual(sink,e.reference())

    def test_deep_supplied_tree_without_recursion(self):
        m=1101;nodes=[TreeNode(0,1,())];root=0
        for i in range(1,m):
            leaf=len(nodes);nodes.append(TreeNode(i,i+1,()))
            nodes.append(TreeNode(0,i+1,(root,leaf)));root=len(nodes)-1
        tree=Hierarchy(tuple(range(m)),tuple(nodes),root)
        p=compile_transfer(tree.order,(0,),[],hierarchy=tree)
        verify_transfer(tree.order,(0,),[],p,hierarchy=tree)
        self.assertEqual(p.cost,m+1)
        self.assertEqual(p.metrics['height'],m-1)

    def test_plain_integer_validation(self):
        for kw in [
            {'header':True},
            {'left_weights':{0:True}},
            {'right_weights':{0:True}},
        ]:
            with self.assertRaises(ValueError):
                compile_transfer((0,),(0,),[],**kw)
        tree=build_hierarchy((0,),[])
        packet=compile_transfer((0,),(0,),[],hierarchy=tree)
        with self.assertRaises(ValueError):
            verify_transfer((0,),(0,),[],packet,hierarchy=tree,header=True)

    def test_canonical_right_order_is_certified(self):
        left=(10,20);right=(9,1,7,3);holes={(10,1)}
        tree=build_hierarchy(left,holes)
        packet=compile_transfer(left,right,holes,hierarchy=tree)
        rank={v:k for k,v in enumerate(right)}
        for block in packet.blocks:
            self.assertEqual(list(map(rank.__getitem__,block.right)),
                             sorted(map(rank.__getitem__,block.right)))
        mutant=copy.deepcopy(packet)
        b=mutant.blocks[0]
        mutant.blocks[0]=type(b)(b.left,tuple(reversed(b.right)))
        with self.assertRaises(ValueError):
            verify_transfer(left,right,holes,mutant,hierarchy=tree)


    def test_zero_frontier_preserves_trusted_right_order(self):
        left=(20,10);right=(9,1,7,3);holes=()
        tree=build_hierarchy(left,holes)
        packet=compile_transfer(left,right,holes,hierarchy=tree)
        stats=verify_transfer(left,right,holes,packet,hierarchy=tree)
        self.assertEqual(packet.blocks,[Block(left,right)])
        self.assertEqual(packet.cost,len(left)+len(right))
        self.assertEqual(stats,{'cost':6,'states':1,'blocks':1,
                                'checked':True,'height':0})

    def test_all_acknowledged_is_empty_packet(self):
        left=(0,1);right=(7,3);holes={(i,j) for i in left for j in right}
        tree=build_hierarchy(left,holes)
        packet=compile_transfer(left,right,holes,hierarchy=tree)
        stats=verify_transfer(left,right,holes,packet,hierarchy=tree)
        self.assertEqual(packet.blocks,[])
        self.assertEqual(packet.cost,0)
        self.assertTrue(stats['checked'])
        self.assertEqual(stats['blocks'],0)
        self.assertEqual(polynomial(packet.blocks),Counter())

    def test_two_by_three_canonical_seven_optimum_six(self):
        left=(0,1);right=(0,1,2);holes={(0,1),(1,2)}
        tree=build_hierarchy(left,holes,singleton_leaves=True)
        packet=compile_transfer(left,right,holes,hierarchy=tree)
        stats=verify_transfer(left,right,holes,packet,hierarchy=tree)
        self.assertEqual(packet.blocks,[Block((0,),(0,2)),Block((1,),(0,1))])
        self.assertEqual(packet.cost,6)
        self.assertEqual(stats['cost'],6)
        canonical=greedy(left,right,holes,tree)
        self.assertEqual(weighted_cost(canonical,dict.fromkeys(left,1),
                                       dict.fromkeys(right,1),0),7)
        mutant=copy.deepcopy(packet)
        first=mutant.blocks[0]
        mutant.blocks[0]=Block(first.left,first.right+(first.right[-1],))
        with self.assertRaises(ValueError):
            verify_transfer(left,right,holes,mutant,hierarchy=tree)

    def test_malformed_certificate_schema_rejected_cleanly(self):
        left=(0,1);right=(0,1);holes={(0,0)}
        tree=build_hierarchy(left,holes)
        original=compile_transfer(left,right,holes,hierarchy=tree)
        mutants=[]
        p=copy.deepcopy(original);del p.states[0]['take'];mutants.append(p)
        p=copy.deepcopy(original);p.states[0]['cost']=True;mutants.append(p)
        p=copy.deepcopy(original);p.states[0]['node']=True;mutants.append(p)
        p=copy.deepcopy(original);p.decisions={True:False};mutants.append(p)
        for packet in mutants:
            with self.subTest(packet=packet):
                with self.assertRaises(ValueError):
                    verify_transfer(left,right,holes,packet,hierarchy=tree)

if __name__=='__main__':unittest.main()
