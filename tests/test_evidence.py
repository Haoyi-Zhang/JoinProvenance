"""Owned finite evidence gates and certificate-independent receiver conformance."""
import ast, copy, json, sys, tempfile, unittest
from collections import Counter
from itertools import product,permutations
from pathlib import Path
from unittest.mock import patch
from provenance import hierarchy_campaign as hc
from provenance import campaign as old
from provenance.direct import optimize_direct,verify_direct
from provenance.laminar import compile_transfer,build_hierarchy,Hierarchy,TreeNode
from provenance.oracle import minimum_costs
from provenance.rectangles import Block,polynomial

class EvidenceGates(unittest.TestCase):
    def test_wrong_oracle_rejected(self):
        with patch.object(hc,'minimum_costs',return_value=([(123,1)]*4,[(123,1)]*4)):
            with self.assertRaises(ValueError):hc.exact(1,1,0,2,0)
    def test_wrong_boundary_rejected(self):
        with patch.object(hc,'minimum_costs',return_value=([(0,0)]*512,[(0,0)]*512)):
            with self.assertRaises(ValueError):hc.boundary()
    def test_wrong_height_formula_rejected(self):
        with patch.object(hc,'greedy',return_value=[]):
            with self.assertRaises(ValueError):hc.gap(1,16)
    def test_missing_detection_rejected(self):
        with patch.object(hc,'verify_transfer',return_value={'checked':True}):
            with self.assertRaises(ValueError):hc.mutations()
    def test_baseline_missing_coefficient_rejected(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(old,'OUT',Path(tmp)),patch.object(old,'sparse_complement',return_value=[]):
            with self.assertRaises(ValueError):old.exact(1,1)
    def test_replay_must_drain(self):
        # A valid post-insertion invariant alone is not completed replay.
        event=dict(seed=1,drift=0,kind='insert',bound=2,
                   left=[dict(identity=0,key=0,value=0)],right=[dict(identity=0,key=0,value=0)])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'owned.jsonl';path.write_text(json.dumps(event)+'\n')
            with self.assertRaises(ValueError):hc.replay(path)
    def test_no_bare_scientific_assert(self):
        root=Path(__file__).resolve().parents[1]
        paths=list((root/'provenance').glob('*.py'))+[root/name for name in
                ('pilot.py','sparse_pilot.py','laminar_pilot.py','example.py')]
        self.assertEqual([(p.name,n.lineno) for p in paths for n in ast.walk(ast.parse(p.read_text()))
                          if isinstance(n,ast.Assert)],[])

class DirectReceiver(unittest.TestCase):
    def test_all_node_numberings_preserve_trusted_ids(self):
        a=(20,10,30);b=(9,1,7);e={(20,1),(10,7),(30,1)}
        base=build_hierarchy(a,e,singleton_leaves=True)
        original=compile_transfer(a,b,e,hierarchy=base)
        from provenance.certificate import verify_transfer
        for sequence in permutations(range(len(base.nodes))):
            index={old:new for new,old in enumerate(sequence)}
            nodes=tuple(TreeNode(base.nodes[old].lo,base.nodes[old].hi,
                        tuple(index[c] for c in base.nodes[old].children)) for old in sequence)
            tree=Hierarchy(base.order,nodes,index[base.root])
            packet=compile_transfer(a,b,e,hierarchy=tree)
            self.assertEqual((packet.order,tuple(packet.nodes),packet.root),(tree.order,tree.nodes,tree.root))
            self.assertEqual((packet.cost,packet.blocks),(original.cost,original.blocks))
            self.assertTrue(verify_transfer(a,b,e,packet,hierarchy=tree)['checked'])
            self.assertTrue(verify_direct(a,b,e,packet,hierarchy=tree)['checked'])

    def test_protocol_roundtrip_and_recompile_binding(self):
        from receiver_costs import encode,decode,verify_recompile
        a=(20,10);b=(9,1,7);e={(20,1),(10,7)};t=build_hierarchy(a,e,singleton_leaves=True)
        packet=compile_transfer(a,b,e,hierarchy=t)
        for certificate in (False,True):
            restored=decode(encode(packet,certificate))
            self.assertTrue(verify_recompile(a,b,e,restored,hierarchy=t)['checked'])
            restored.blocks.append(restored.blocks[0])
            with self.assertRaises(ValueError):verify_recompile(a,b,e,restored,hierarchy=t)

    def test_trusted_preorder_dictionary_honest_compiler_completeness(self):
        tree=Hierarchy((20,10),(TreeNode(0,2,(1,2)),TreeNode(0,1,()),TreeNode(1,2,())),0)
        a=(20,10);b=(9,1,7);e={(20,1),(10,7)}
        packet=compile_transfer(a,b,e,hierarchy=tree)
        self.assertEqual((packet.order,tuple(packet.nodes),packet.root),(tree.order,tree.nodes,tree.root))
        self.assertEqual((packet.cost,len(packet.blocks)),(6,2))
        from provenance.certificate import verify_transfer
        self.assertTrue(verify_transfer(a,b,e,packet,hierarchy=tree)['checked'])
        self.assertTrue(verify_direct(a,b,e,packet,hierarchy=tree)['checked'])

    def test_all_three_by_three_supports_two_trees_three_regimes(self):
        left=(20,10,30);right=(9,1,7);pairs=list(product(left,right))
        for tree in hc.binary_hierarchies(left)[:2]:
            for h,lw,rw in [(0,dict.fromkeys(left,1),dict.fromkeys(right,1)),
                            (7,{20:2,10:5,30:8},{9:1,1:6,7:11}),
                            (2**90,dict.fromkeys(left,2**100),dict.fromkeys(right,2**95))]:
                weights=dict(header=h,left_weights=lw,right_weights=rw)
                clusters=[tree.order[n.lo:n.hi] for n in tree.nodes]
                costs,_=minimum_costs(left,right,clusters,lw,rw,h)
                for mask in range(512):
                    holes={pair for k,pair in enumerate(pairs) if not mask>>k&1}
                    d=optimize_direct(left,right,holes,hierarchy=tree,**weights)
                    p=compile_transfer(left,right,holes,hierarchy=tree,**weights)
                    self.assertEqual((d.cost,len(d.blocks)),costs[mask])
                    self.assertEqual(list(d.blocks),p.blocks)
                    self.assertEqual(polynomial(d.blocks),Counter({pair:1 for pair in pairs if pair not in holes}))
                    self.assertTrue(verify_direct(left,right,holes,p,hierarchy=tree,**weights)['checked'])
    def test_empty_and_uniform(self):
        for left,right,holes in [((),(),[]),((),(0,),[]),((0,),(),[]),
                                  ((0,1),(9,1),[(0,1),(1,1)]),
                                  ((0,1),(9,1),list(product((0,1),(9,1))))]:
            tree=build_hierarchy(left,holes);p=compile_transfer(left,right,holes,hierarchy=tree)
            self.assertTrue(verify_direct(left,right,holes,p,hierarchy=tree)['checked'])
    def test_wrong_packet_fields_rejected(self):
        a=(0,1);b=(0,1,2);e={(0,1),(1,2)};t=build_hierarchy(a,e,singleton_leaves=True)
        original=compile_transfer(a,b,e,hierarchy=t)
        for alter in [lambda p:p.blocks.pop(),lambda p:p.blocks.append(p.blocks[0]),
                      lambda p:setattr(p,'cost',True),lambda p:setattr(p,'cost',p.cost+1),
                      lambda p:setattr(p,'order',(1,0)),lambda p:setattr(p,'root',0),
                      lambda p:p.blocks.__setitem__(0,Block((0,),(2,0))),
                      lambda p:p.blocks.__setitem__(0,Block((0,),(0,0,2)))]:
            p=copy.deepcopy(original);alter(p)
            with self.assertRaises(ValueError):verify_direct(a,b,e,p,hierarchy=t)
    def test_context_rejections(self):
        for a,b,e,kw in [((0,0),(0,),[],{}),((0,),(0,),[(1,0)],{}),
                           ((0,),(0,),[(0,0),(0,0)],{}),((0,),(0,),[],{'header':True}),
                           ((0,),(0,),[],{'left_weights':{0:0}})]:
            with self.assertRaises(ValueError):optimize_direct(a,b,e,hierarchy=build_hierarchy(tuple(set(a)),[]),**kw)
        with self.assertRaises(ValueError):optimize_direct((0,1),(0,),[(0,0)],hierarchy=Hierarchy((0,1),(TreeNode(0,2,()),),0))
    def test_certificate_rows_are_not_part_of_direct_protocol(self):
        a=b=(0,1);t=build_hierarchy(a,[]);p=compile_transfer(a,b,[],hierarchy=t)
        p.states=[];p.decisions={}
        self.assertTrue(verify_direct(a,b,[],p,hierarchy=t)['checked'])
        # This guarantees output semantics/optimum, not truth of discarded rows.

if __name__=='__main__':unittest.main()
