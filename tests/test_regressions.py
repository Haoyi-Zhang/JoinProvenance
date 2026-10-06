"""Finite integer and retained-output regressions; no child jobs or services."""
import json
import math
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from provenance.oracle import minimum_costs
import reproduce


class OracleIntegerTests(unittest.TestCase):
    def test_partition_total_exceeds_old_finite_sentinel(self):
        left=tuple(range(12));weight=9*10**98
        cost=weight+1
        self.assertLess(cost,10**99)  # The existing per-candidate gate admits it.
        expected=(12*cost,12)
        self.assertGreater(expected[0],10**100)
        positive,boolean=minimum_costs(left,(0,),[(i,) for i in left],
                                       dict.fromkeys(left,weight),{0:1},0)
        self.assertEqual(positive[-1],expected)
        self.assertEqual(boolean[-1],expected)
        self.assertIs(type(positive[-1][0]),int)

    def test_unreachable_support_remains_distinct_from_finite_cost(self):
        positive,boolean=minimum_costs((0,1),(0,),[(0,1)],
                                       {0:1,1:1},{0:1},0)
        self.assertEqual(positive[0],(0,0))
        self.assertEqual(positive[3],(3,1))
        self.assertEqual(boolean[3],(3,1))
        self.assertTrue(math.isinf(positive[1][0]))
        self.assertTrue(math.isinf(boolean[2][0]))


class RetainedOutputTests(unittest.TestCase):
    def test_event_stream_comparison_is_byte_exact(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'results').mkdir();out=root/'fresh';out.mkdir()
            expected=root/'results'/'events.jsonl';actual=out/'events.jsonl'
            expected.write_bytes(b'{"event":1}\n')
            actual.write_bytes(b'{"event":1}\r\n')
            with patch.object(reproduce,'ROOT',root),redirect_stdout(StringIO()):
                self.assertFalse(reproduce.compare(out))
            report=json.loads((out/'comparison.json').read_text())
            self.assertEqual(report['discrete_mismatches'],['events.jsonl'])
            actual.write_bytes(expected.read_bytes())
            with patch.object(reproduce,'ROOT',root),redirect_stdout(StringIO()):
                self.assertTrue(reproduce.compare(out))

    def test_timeout_preserves_captured_stdout_and_stderr(self):
        # Construct the exception directly; this test starts no subprocess.
        for stdout,stderr in [(b'partial stdout\n',b'partial stderr\n'),
                              ('partial stdout\n','partial stderr\n')]:
            exc=subprocess.TimeoutExpired(['owned-fixture'],44,
                                           output=stdout,stderr=stderr)
            self.assertEqual(reproduce.timeout_log(exc),
                             'partial stdout\npartial stderr\n\n'
                             'Wall timeout after 44 seconds.\n')


if __name__=='__main__':unittest.main()
