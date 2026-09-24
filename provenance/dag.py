"""A shared-DAG boundary control, not an implementation of general sparse circuits.

The prefix/suffix construction for a missing diagonal is classical; see
Kulikov, Mikhailin, Mokhov, and Podolskii, Complexity of Linear Operators,
Theory of Computing 21(9), 2025, pp. 2--3 and Lemma 3.3.
This module is an original implementation of that elementary special case.
"""
from __future__ import annotations
from dataclasses import dataclass
from collections import Counter

@dataclass(frozen=True)
class Node:
    op: str
    args: tuple[int, ...] = ()
    variable: str = ''

@dataclass
class Circuit:
    nodes: list[Node]
    output: int

    @property
    def gates(self):
        return sum(n.op in {'add', 'mul'} for n in self.nodes)

    @property
    def wires(self):
        return sum(len(n.args) for n in self.nodes)

    def check_topology(self):
        for i, n in enumerate(self.nodes):
            if n.op not in {'input', 'zero', 'add', 'mul'}:
                raise ValueError('unknown gate')
            if any(j < 0 or j >= i for j in n.args):
                raise ValueError('not a topologically ordered DAG')
            if len(n.args) != (2 if n.op in {'add', 'mul'} else 0):
                raise ValueError('incorrect arity')
        if not 0 <= self.output < len(self.nodes):
            raise ValueError('invalid output')

    def expand(self):
        # Small-instance observer only; do not expand a large circuit.
        self.check_topology()
        values = []
        for n in self.nodes:
            if n.op == 'zero': values.append(Counter())
            elif n.op == 'input': values.append(Counter({(n.variable,): 1}))
            elif n.op == 'add': values.append(values[n.args[0]] + values[n.args[1]])
            else:
                out = Counter()
                for a, ca in values[n.args[0]].items():
                    for b, cb in values[n.args[1]].items():
                        out[tuple(sorted(a+b))] += ca*cb
                values.append(out)
        return values[self.output]


def crown_circuit(n: int) -> Circuit:
    """For n>=2, use exactly 5*n-7 binary gates and 2*n input nodes.

    Prefixes exclude the final input and suffixes exclude the first input.
    Each internal row combines two disjoint ranges. No subtraction or
    idempotence is used. The final circuit computes sum(i!=j) x_i*y_j.
    """
    if n < 1:
        raise ValueError('n must be positive')
    nodes = [Node('input', variable=f'x{i}') for i in range(n)]
    nodes += [Node('input', variable=f'y{i}') for i in range(n)]
    def gate(op, a, b):
        nodes.append(Node(op, (a,b)))
        return len(nodes)-1
    if n == 1:
        nodes.append(Node('zero'))
        return Circuit(nodes, len(nodes)-1)
    prefix = [n]
    for i in range(1,n-1): prefix.append(gate('add', prefix[-1], n+i))
    suffix = {n-1: 2*n-1}
    for i in range(n-2,0,-1): suffix[i] = gate('add', n+i, suffix[i+1])
    rows=[]
    for i in range(n):
        if i == 0: subtotal = suffix[1]
        elif i == n-1: subtotal = prefix[n-2]
        else: subtotal = gate('add', prefix[i-1], suffix[i+1])
        rows.append(gate('mul', i, subtotal))
    output = rows[0]
    for r in rows[1:]: output = gate('add', output, r)
    result = Circuit(nodes, output)
    result.check_topology()
    return result
