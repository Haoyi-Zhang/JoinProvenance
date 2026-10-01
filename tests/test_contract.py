"""Finite checks of the published representation and transition contracts."""
import csv
import json
import statistics
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch
from collections import Counter
from itertools import product
from provenance.rectangles import *
from provenance.engine import Engine, TupleRecord
from provenance.regions import RegionEngine

class ContractTests(unittest.TestCase):
    def test_all_small_oracle_witnesses(self):
        for m,n in [(1,1),(1,4),(2,2),(2,3),(3,3)]:
            pos,boo=all_optima(m,n)
            for mask in range(1 << (m*n)):
                for boolean,cost in [(False,pos),(True,boo)]:
                    blocks=optimal_blocks(mask,m,n,boolean=boolean)
                    self.assertEqual(len(blocks),cost[mask])
    def test_all_small_sparse_bitset(self):
        for m,n in [(1,1),(1,4),(2,3),(3,3)]:
            full=set(product(range(m),range(n)))
            for mask in range(1 << (m*n)):
                e=full-set(mask_pairs(mask,m,n))
                b=sparse_complement(tuple(range(m)),tuple(range(n)),e)
                self.assertTrue(verify_partition_bits(tuple(range(m)),tuple(range(n)),e,b))
    def test_empty_and_invalid(self):
        self.assertEqual(sparse_complement((),(2,),[]),[])
        self.assertEqual(sparse_complement((2,),(),[]),[])
        for args in [((1,1),(2,),[]),((1,),(2,),[(1,2),(1,2)]),((1,),(2,),[(0,2)]),((),(2,),[(1,2)])]:
            with self.assertRaises(ValueError): sparse_complement(*args)
        with self.assertRaises(ValueError): all_optima(5,5)
    def test_checker_detects_overlap_omission_replay(self):
        a=(0,1); b=(0,1); e={(0,0)}
        good=sparse_complement(a,b,e)
        for bad in [good+good,good[:-1],[Block(a,b)], [Block((2,),b)]]:
            with self.assertRaises(ValueError): verify_partition_bits(a,b,e,bad)
    def test_crown_separation(self):
        for n in range(2,17):
            cover=crown_cover(n)
            self.assertEqual(set(polynomial(cover)),set(crown(n)))
        n=6
        self.assertLess(crown_boolean_width(n),n)
        self.assertNotEqual(polynomial(crown_cover(n)),Counter(crown(n)))
    def test_power_two_memberships(self):
        for n in [2,4,8,16,32,64,128,256]:
            blocks=sparse_complement(tuple(range(n)),tuple(range(n)),[(i,i) for i in range(n)])
            self.assertEqual(len(blocks),2*(n-1))
            self.assertEqual(sum(x.memberships for x in blocks),2*n*(n.bit_length()-1))
    def test_partial_diagonal_width_bound(self):
        m,n=3,4; pos,_=all_optima(m,n); full=(1 << (m*n))-1
        for e in range(4):
            actual=max(pos[mask] for mask in range(1 << (m*n)) if m*n-mask.bit_count()<=e)
            self.assertEqual(actual,min(m,n,e+1))
    def test_stable_identity_and_atomic_rejection(self):
        e=RegionEngine(); s=Counter()
        e.insert_epoch([TupleRecord(0,1,9)],[TupleRecord(0,1,9)],2)
        e.check(s);before=e.pending()
        with self.assertRaises(ValueError): e.insert_epoch([TupleRecord(0,1,9)],[],1)
        with self.assertRaises(ValueError): e.insert_epoch([TupleRecord(1,1,9)],[],0)
        with self.assertRaises(ValueError): e.migrate('unsupported')
        self.assertEqual(e.pending(),before)
        s[e.emit((0,0))]+=1;e.check(s)
        with self.assertRaises(ValueError): e.emit((0,0))
        e.migrate('sparse');self.assertEqual(e.regions,[])
        e.insert_epoch([],[TupleRecord(1,1,9)],1);e.check(s)
        self.assertEqual(e.pending(),Counter({(0,1):1}))
    def test_new_new_delta_owned_once(self):
        e=RegionEngine();s=Counter()
        e.insert_epoch([TupleRecord(0,0,0)],[TupleRecord(0,0,0)],2)
        e.insert_epoch([TupleRecord(1,0,0)],[TupleRecord(1,0,0)],2)
        e.check(s);self.assertEqual(e.pending(),Counter(product(range(2),repeat=2)))
    def test_exact_install_rejects_mutants(self):
        e=Engine();e.insert_epoch([TupleRecord(i,0,0) for i in range(2)], [TupleRecord(i,0,0) for i in range(2)],4)
        expected=e.reference();good=list(e.pending)
        for mutant in [good+good, [], [Block((0,),(0,1))], [Block((8,),(0,1))]]:
            with self.assertRaises(ValueError): e.install(mutant,expected)
        self.assertEqual(polynomial(e.pending),expected)
    def test_same_cardinality_and_lineage_not_enough(self):
        first=Counter({(0,0):1,(1,1):1});second=Counter({(0,1):1,(1,0):1})
        self.assertEqual(sum(first.values()),sum(second.values()))
        self.assertEqual({i for i,j in first},{i for i,j in second})
        self.assertEqual({j for i,j in first},{j for i,j in second})
        self.assertNotEqual(first,second)

    def test_empty_positive_factors_rejected(self):
        for block in [Block((),(0,)),Block((0,),())]:
            with self.assertRaises(ValueError):
                polynomial([block])

    def test_row_baseline_validates_frontier(self):
        with self.assertRaises(ValueError):
            row_complement((0,0),(0,),[])
        with self.assertRaises(ValueError):
            row_complement((0,),(0,),[(0,0),(0,0)])
        with self.assertRaises(ValueError):
            row_complement((0,),(0,),[(1,0)])

    def test_engine_rejects_nonpositive_sink_coefficients(self):
        e=Engine();e.insert_epoch([TupleRecord(0,0,0)],[TupleRecord(0,0,0)],2)
        with self.assertRaises(AssertionError):
            e.check(Counter({(0,0):-1}))


    def test_random_encoded_paired_ratio_three_seed_fixture(self):
        import summarize
        root=Path(__file__).resolve().parents[1]
        source=root/'results'/'hierarchy_bench_128_random.csv'
        with source.open(newline='') as handle:
            rows=[row for row in csv.DictReader(handle) if row['regime']=='encoded']
        self.assertEqual(len(rows),9)
        seeds=sorted({int(row['seed']) for row in rows})
        self.assertEqual(seeds,[1701,2718,3141])
        per_seed=[]
        for seed in seeds:
            seed_rows=[row for row in rows if int(row['seed'])==seed]
            self.assertEqual(len(seed_rows),3)
            ratios={int(row['canonical_cost'])/int(row['optimized_cost'])
                    for row in seed_rows}
            self.assertEqual(len(ratios),1)
            per_seed.append(ratios.pop())
        expected=28056/20440
        self.assertEqual(statistics.median(per_seed),expected)
        self.assertAlmostEqual(expected,1.3726027397260274,15)
        with tempfile.TemporaryDirectory() as td:
            target=Path(td)/'benchmark-summary.csv'
            output=summarize.build_benchmark_summary(root/'results',target)
        item=next(row for row in output
                  if row['n']==128 and row['family']=='random'
                  and row['regime']=='encoded')
        self.assertEqual(item['payload_ratio_median'],expected)

    def test_reproduction_compare_detects_missing_output(self):
        import reproduce
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'results').mkdir();out=root/'fresh';out.mkdir()
            (root/'results'/'expected.json').write_text(json.dumps({'value':1}))
            with patch.object(reproduce,'ROOT',root), redirect_stdout(StringIO()):
                self.assertFalse(reproduce.compare(out))
            report=json.loads((out/'comparison.json').read_text())
            self.assertEqual(report['retained_files_without_reproduced_counterpart'],
                             ['expected.json'])

class SharedDagTests(unittest.TestCase):
    def test_shared_dag_coefficients_and_size(self):
        from provenance.dag import crown_circuit
        for n in range(1,17):
            circuit = crown_circuit(n)
            target = Counter({tuple(sorted((f'x{i}', f'y{j}'))): 1
                              for i in range(n) for j in range(n) if i != j})
            self.assertEqual(circuit.expand(), target)
            if n >= 2:
                self.assertEqual(circuit.gates, 5*n-7)
                self.assertEqual(circuit.wires, 2*(5*n-7))
    def test_invalid_migration_on_empty_state(self):
        with self.assertRaises(ValueError): RegionEngine().migrate('unsupported')

if __name__ == "__main__":
    unittest.main()
