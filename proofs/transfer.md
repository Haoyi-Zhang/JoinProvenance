# Certified hierarchical transfer: mathematical argument

This file is a complete pen-and-paper argument for the implemented fragment.
The executable checks are finite checks, not a proof-assistant formalization.
The algebraic semantics follow provenance semirings (Green, Karvounarakis and
Tannen, PODS 2007). Rectangle partitions, canonical tree decompositions and
shared arithmetic circuits are established representations, not inventions of
this artifact. The claims below distinguish their precise restrictions.

## 1. Model and observational contract

A finite equality join has left occurrences identified by distinct symbols x_i
and right occurrences identified by distinct symbols y_j. Different occurrences
retain different symbols even when every data value is equal. Symbols on the two
sides are disjoint. For one equality-key bucket let A and B be the finite sets of
identities. Every currently matching pair belongs to exactly one pending region
or to the acknowledged sink. A pending region consists of a rectangle A × B and
an exception set E of acknowledged pairs in that rectangle. It denotes

    P(A,B,E) = sum_{(i,j) in (A × B) \ E} x_i y_j  in N[X,Y].

No negative coefficient, subtraction, repeated factor member, or hidden
exception predicate is permitted in a target block. A block (U,V) denotes
(sum_{i in U} x_i)(sum_{j in V} y_j); both sets are nonempty. A target packet is
a sum of such blocks. Membership lists, rather than shared sum nodes or interval
endpoints, are the costed target representation.

For multiple buckets and regions, the polynomial is their sum. The source
base relation retains each identity and equality key separately from the packet.
There are only sequential insertion, acknowledgment and migration steps. An
insertion epoch admits at most Delta new occurrences in total. No deletion,
outer join, negation, concurrent insertion, crash, distributed acknowledgment or
external exactly-once guarantee is in this model. Delta may be zero and need
not enter the migration-cost bounds.

**Proposition 1 (coefficient contract).** A target packet preserves this region
under every assignment of its occurrence symbols into every commutative semiring
if and only if its rectangles partition (A × B) \ E.

**Proof.** The coefficient of x_i y_j in the packet is exactly the number of
blocks containing that pair: distributivity creates one term for each such
block, and positive coefficients cannot cancel. Polynomial equality is
therefore equivalent to coefficient one for every pending pair and coefficient
zero for every other pair. This is exactly a partition. Equality implies all
semiring interpretations agree, because evaluation of polynomials preserves
addition and multiplication. Conversely choose the semiring N[X,Y] itself and
assign each symbol to itself. Universal equality then implies polynomial
equality. This does not claim necessity of a partition for one fixed idempotent
semiring, where duplicates may disappear. QED.

## 2. Target hierarchy and cost

A trusted proper binary tree T partitions A. Every node v has a nonempty row
cluster A_v. The root cluster is A; two child clusters are disjoint and have
union A_v. Leaves partition A. Singleton leaves always suffice. A leaf containing
more than one row is admissible only if all its rows have the same exception
columns. This condition is checked against the frozen source frontier.

A target row factor must equal A_v for a node v. Its column factor may be any
nonempty subset of B. In particular, it is not required to be a node of a
second hierarchy. T is selected before optimization and supplied independently
to the checker; changing T changes the optimization problem.

Assign positive integer entry weights a_i and b_j, and a nonnegative integer
block-header weight h. The cost of a block (A_v,V) is

    h + sum_{i in A_v} a_i + sum_{j in V} b_j.

The packet cost is the sum of block costs. The primary objective is this cost;
the secondary, lexicographic objective is the number of nonempty blocks.
This is the factor-payload cost only. It excludes the certificate, source base
relations, transient simultaneous source and target storage, allocator overhead,
and framing not explicitly represented by these weights.

## 3. Normal form

**Lemma 2 (one block per cluster).** There is an optimum with at most one block
at every node. Every positive-cost optimum already has this property after
identical-node blocks are combined.

**Proof.** In a positive exact packet, two blocks with the same nonempty row
cluster have disjoint column sets; otherwise they duplicate at least one pair.
Replace them by one block containing the union of the column sets. Column cost
is unchanged, and a positive row cost plus one nonnegative header is saved.
The block count decreases. Repeating proves the assertion. QED.

At a node v, call a column available if it is pending in every row of A_v and
has not been assigned to an active ancestor. An active node has a nonempty block.

**Lemma 3 (all-or-none exchange).** After merging identical-node blocks, every
minimum-cost exact packet has this property: if v is active, its block contains
every available column at v.

**Proof.** Suppose v is active but omits an available column j. Since no ancestor
owns j on A_v, the pairs (i,j), i in A_v, must be partitioned by strict descendant
clusters whose blocks contain j. No cluster partly crosses A_v because tree
clusters are laminar. A strict descendant cannot cover all of A_v, so at least
two such descendant blocks are required. Remove j from every one of those
blocks and add j to the existing block at v. Delete any block that becomes
empty. No pair is lost or duplicated: exactly the same column slice A_v × {j}
is moved to v. The active block at v incurs no additional row or header cost.
At least two b_j charges are replaced by one b_j charge, and all other removed
charges are nonnegative. Since b_j > 0, the cost strictly decreases, contrary
to optimality. A leaf cannot omit an available column while being the only
remaining owner of its row cluster. QED.

This lemma depends on node-wide row factors, arbitrary column subsets, positive
column weights, additive costs, and the absence of sharing or cross-block
compression. It is not valid merely because a representation is called
factorized. Zero column weights still permit a non-increasing normalization,
but that extension is not needed by the admitted implementation.

## 4. Sparse information and recurrence

Let Bad(v) be the set of columns with at least one exception in A_v. Define

    Q_root = B \ Bad(root),
    Q_c    = Bad(parent(c)) \ Bad(c) for a nonroot node c,
    q_v    = sum_{j in Q_v} b_j,
    alpha_v = h + sum_{i in A_v} a_i.

The Q sets on one root-to-leaf path are pairwise disjoint: Bad sets only shrink
along a path, and a column leaves them at most once. Q_v is exactly the set of
columns that become fully pending for the first time at v. A column that still
belongs to Bad at a leaf is not pending on that uniform leaf.

Suppose the available columns at v have total weight k. Their identities do not
otherwise affect any decision below v: all of them are pending on every row
below v, their costs are additive with node-independent b_j, and none is a member
of any Q set below v. Descendant partially pending columns are described by the
fixed Q sets. Let F_v(k) be the optimum lexicographic pair (payload cost, block
count) for this suffix problem. Its value is the same for any available set of
weight k. Arithmetic below is on pairs; adding an activated block adds its cost
and one to its count.

At a leaf,

    F_v(0) = (0,0),
    F_v(k) = (alpha_v + k, 1)  for k > 0.

At an internal node, put

    N_v(k) = sum_{c child of v} F_c(k + q_c).

Then

    F_v(0) = N_v(0),
    F_v(k) = min_lex { N_v(k),
                      (alpha_v + k,1) + sum_c F_c(q_c) } for k > 0.

The root answer is F_root(q_root). Empty inputs have the unique empty packet
with zero cost and no certificate tree in the packet.

**Theorem 4 (exactness).** This recurrence returns the minimum payload cost and,
among minimum-cost packets, the minimum block count in the supplied hierarchy.

**Proof.** Induct on the subtree height. At a uniform leaf, either no column is
available and no block is needed, or its only row cluster must carry all
available columns. This gives the base case. At an internal node, Lemma 3
restricts an optimum to two possibilities. An inactive node passes every
available column to both children. Child c also receives Q_c; the two sets are
disjoint, and their total weight is k+q_c. An active node takes every available
column and passes none of them downward; each child receives only Q_c. Child
row sets are disjoint. Consequently their suffix subproblems have no pair
ownership interaction, and their costs add. Every candidate produced by either
choice is a valid exact packet after the inductive child solutions are attached.
Thus both an optimum is represented among the choices and each chosen value is
attainable. The lexicographic tie-break is preserved by addition and minimization.
This proves the result at every node and hence at the root. QED.

No subset enumeration is used by the optimizer. The exhaustive oracle deliberately
does enumerate all column subsets and solves a different shortest-path dynamic
program over support masks, so the finite comparison does not assume Lemma 3.

## 5. Ancestry-state bound and sparse complexity

Let H be the maximum root-to-leaf edge depth and t the number of nodes. During
top-down recurrence evaluation, k at a node v is the sum of q values on a suffix
of the root-to-v path: the suffix starts immediately below the most recent
active ancestor, or at the root if none is active.

**Lemma 5 (state compression).** At most depth(v)+1 distinct k values are needed
at v, and therefore at most sum_v(depth(v)+1) <= t(H+1) states are needed overall.

**Proof.** The root has only k=q_root. A transition from parent p to child v
passes either k_p+q_v (inactive parent) or q_v (active parent). The former extends
the existing suffix and the latter starts a new suffix. There are depth(v)+1
possible suffix starts. Equal numeric sums can merge states, but cannot create
additional states. Memoization therefore evaluates at most the asserted number.
The bound counts states, not all possible integer values up to the total weight.
It does not depend on the magnitude of the weights. QED.

Let e=|E| and d be the number of rows incident to an exception. The sparse builder
puts all unaffected rows in one uniform leaf, balances the d affected singleton
rows, and, when both groups are nonempty, puts their roots below a new root.
For d>=1 this gives t<=2(d+1)-1 and H<=1+ceil(log2 d). Also d<=e. For d=0 there
is a single uniform root. Selection of this hierarchy is not claimed optimal.

**Theorem 6 (output-sensitive construction).** For that sparse hierarchy, an
honest optimum packet and its certificate can be constructed and checked in
expected O(m+n+e log(e+1)+W) word operations and space, where m=|A|, n=|B| and W
is the total number of row and column memberships in the emitted packet. The
case e=0 takes O(m+n+W). This word-operation bound assumes identities and exact
arithmetic fit the stated word model; otherwise integer-operation bit costs
must also be counted.

**Proof.** Input validation and the row dictionary take O(m+n+e). A leaf's Bad
set is its exception-column set. At an internal node it is the union of its
children's Bad sets. Charge one occurrence in Bad(v) to an exception in v's
subtree with that column. Summing over all nodes charges each exception at most
H+1 times, so total stored Bad memberships are at most e(H+1). Each Q difference
can be computed by scanning a parent's Bad set, except the root complement,
which scans B. Binary branching contributes only a constant factor. Thus all
Q sets, their weights, and the Bad sets cost O(n+e(H+1)) expected hash-table work
and space. A prefix sum over the row order gives alpha_v in constant arithmetic
operations per node. Lemma 5 bounds the constant-branching recurrence work by
O(t(H+1)).

For reconstruction, follow each available column occurrence from its birth node
until it is emitted. Deferral sends it into both children; activation ends the
branch. Every leaf of this propagation forest corresponds to a column membership
in an emitted block. No branch can terminate without emitting the column, because
a fully pending column remains pending on every descendant leaf. A proper binary
tree with L leaves has 2L-1 nodes. Therefore total column-propagation work is at
most twice the number of output column memberships, plus their birth accounting.
Copying the row intervals into output lists costs exactly the output row
memberships. No sort is required: factor-member order is semantically irrelevant,
and the checker compares column sets after validating uniqueness.

The checker independently recomputes Bad, Q and alpha, verifies each closed table
row in child-first order, verifies precisely the root-reachable state closure,
and reconstructs the same certified choices. Each operation has the same bound;
the supplied physical dictionary is compared with the trusted one. Substituting
t<=2d+1, d<=e and H=O(log(e+1)) proves the claim. Honest-packet space includes the
retained source exception sets, the tables, the packet and traversal state. QED.

If input weights use at most L bits, the values are bounded by the cost of the
singleton-leaf packet. Their bit lengths are O(L+log(mn+1)), with a corresponding
factor for exact addition and comparison. The implementation includes a test
regime above 64 bits; that is a correctness test, not a constant-word timing
claim. Python objects add substantial constants. RSS measurements report these
constants and include the independent coefficient observer when it is used.

## 6. Certificate soundness and trusted context

The trusted context is (A,B,E,T,a,b,h) at a stopped migration barrier. A certificate
contains a target packet, node dictionary, reachable recurrence table, chosen
traversal decisions and claimed payload cost. T in the packet must equal trusted
T; merely validating that an attacker-supplied tree is a tree would establish
optimality for the wrong physical format.

**Theorem 7 (certificate soundness).** An accepted packet is an exact positive
partition of the trusted remaining region and has the optimal lexicographic
cost for trusted T, under the model above.

**Proof.** Tree checks establish nonempty clusters, a disjoint full root
partition, uniform leaves and exact equality with trusted T. Source checks
establish unique occurrence identities, legal distinct exceptions and positive
weight domains. The checker computes Bad and Q from this source, not from the
producer's claims. It requires all and only the recurrence states reachable
from the root by evaluating both choices. Child-first verification establishes
by induction that every table value equals the recurrence value; leaves are
checked against a closed formula. Missing, duplicated or extraneous table
states are rejected.

During reconstruction the checker maintains the available column set. A newly
born set is disjoint from its inherited set. The recorded decision either emits
that full set at the node or passes it to both children. The producer's blocks
must match the reconstruction; duplicate column members are rejected before
set comparison. Each pending pair therefore follows its column from its unique
birth node down the unique branch containing its row until exactly one block
owns it. No exception ever becomes available at a leaf containing that exception.
Thus the reconstructed blocks are a partition. The independently recomputed
cost and block count must match both the packet and the checked root value.
Theorem 4 makes that value optimal. QED.

This is a proof-carrying optimization certificate, not a cryptographic attestation,
a proof-assistant theorem, or an independently developed/reviewed system. The
checker is separate source code written in the same research process. Correctness
still relies on the mathematical argument and on ordinary implementation trust.
A corrupt source snapshot, source key catalog or acknowledgment record is outside
its trust boundary. A resource-admission policy must also bound input/certificate
sizes before accepting arbitrary external data; this artifact uses only owned,
bounded generated tests and has no external service endpoint.

## 7. Why laminarity matters

Let F be any finite family of nonempty row sets containing every singleton row.
Allowed blocks are U×V with U in F and arbitrary nonempty column subsets. For a
binary support matrix, a Boolean cover may cover a positive cell repeatedly,
whereas a positive exact partition may not.

**Theorem 8 (universal overlap boundary).** The following are equivalent:
(a) F is laminar; (b) for every finite column set, every binary support relation,
every positive entry-weight assignment and every nonnegative header cost, the
minimum Boolean-cover payload equals the minimum positive-partition payload.

**Proof of (a) => (b).** Start with any Boolean cover. Merge blocks with equal row
sets by taking their column-set union; this cannot increase cost. For each column
j, retain j only in the inclusion-maximal active row sets containing it, and
remove it from the other blocks. Distinct retained maximal sets are disjoint
because F is laminar. Every covered pair remains covered: any removed row set
is contained in a retained one. No new pair is introduced. The retained blocks
therefore partition the original support. Removing memberships or empty blocks
cannot increase cost. Since positive partitions are already Boolean covers,
the two optimum costs are equal. In fact positive column weights imply a
minimum-cost Boolean cover cannot retain an avoidable nested duplicate.

**Proof of (b) => (a).** Suppose F contains crossing sets A and B. Choose row
representatives a in A\B, b in A∩B and c in B\A, and columns p,q,r. Let the support
be A×{p,q} union B×{q,r}, with no other positive cells. A Boolean cover with two
blocks has unit-membership cost C=|A|+|B|+4, plus two headers. On rows a,b,c and
columns p,q,r the support matrix is

    [1 1 0]
    [1 1 1]
    [0 1 1].

Its determinant is -1, so its rational rank is three. An exact rectangle
partition into k blocks expresses this submatrix as a sum of k rank-at-most-one
matrices over Q, hence k>=3. This remains true even if F contains additional row
sets. Choose integer header h>C and unit entry weights. Every positive partition
costs at least 3h, whereas the two-block Boolean cover costs 2h+C<3h. Singletons
make a positive partition feasible, so this is a strict finite gap, contradicting
(b). QED.

The necessity statement quantifies over header costs. It does not assert a gap
for every crossing family under every one fixed header. The tree optimizer is
not solving a separation between the two optimal costs within its own laminar
format: there is no such separation there. It instead certifies coefficients
and optimizes that restricted format efficiently from the complement input.

## 8. A sharp baseline comparison

The canonical first-safe algorithm emits a block at v for every column that
first becomes fully pending at v. Equivalently, it always takes available
columns at their highest valid tree nodes. It is correct and requires no
optimization table, but can pay avoidable repeated row costs.

**Theorem 9 (sharp height factor).** For a hierarchy of height H and the additive
payload costs above, canonical first-safe cost is at most (H+1) times optimum.
For every H there are admitted positive integer weights and a support relation
for which the ratio approaches H+1 arbitrarily closely.

**Upper-bound proof.** For any column j, its canonical nodes are the maximal
clusters on which j is fully pending. Every feasible packet must cover every
one of those clusters with at least one block containing j. It cannot use an
ancestor crossing an exception. Therefore the canonical packet has no more
column memberships, separately for each j, than any feasible packet. Its total
weighted column charge is consequently at most optimum's column charge.

A participating row occurs in at most H+1 canonical blocks, one per ancestor,
whereas it must occur in at least one block of any exact packet. Thus canonical
weighted row cost is at most (H+1) times optimum's weighted row cost. Finally,
for each active canonical node v choose one of its newly safe columns j and
one row i in A_v. In an optimum, the block owning (i,j) must be at v or a
descendant: an ancestor cannot be fully pending for j by maximality of v.
Charge v's header to this optimum block. An optimum block can receive charges
only from its ancestor nodes, at most H+1 of them. This bounds canonical header
cost by (H+1) times optimum's header cost. Add the three inequalities. QED.

**Matching-family proof.** Use a perfect binary tree of height H with m=2^H
singleton leaves. Introduce one column j_v for every tree node v; column j_v is
pending exactly on A_v. Thus n=2m-1 and each row has H+1 pending columns. Give
every row weight M, every column weight one, and let h=0. Canonical first-safe
has one block at every node and cost

    C_can = M m(H+1) + 2m - 1.

A leaf's own column is pending only at that leaf, so every feasible packet must
activate every leaf. If an internal block contains k columns then k<=H, since
only that node's ancestor columns can be full on its row cluster. Move those
columns to the already-active leaf blocks below it. Extra column charge is at
most k(|A_v|-1), while row charge M|A_v| is removed. For M>H this strictly reduces
cost. Therefore the leaf-only packet is optimal, with cost

    C_opt = m(M+H+1).

The ratio tends to H+1 as M increases. This support family has a dense exception
set; it demonstrates a tight approximation boundary, not sparse-input performance
or an observed production encoding. QED.

For unit weights, the 2×3 support {(0,0),(0,2),(1,0),(1,1)} is already a strict
example: taking the common column at the root costs 7 memberships, while the
two leaf blocks cost 6. The optimum is not determined merely by input cardinality.

## 9. Composition under drift and atomic installation

Let I=(L,R) be retained base occurrences, S the acknowledged sink polynomial,
and P the pending polynomial. The state invariant is

    S + P = Q(I),

with each matching occurrence pair having exactly one coefficient-one owner.
On inserting disjoint new identities L+ and R+, create delta regions for
L_old × R+ and L+ × (R_old union R+), restricted to equality-key buckets. They
are disjoint and their union is exactly the newly matching pairs. In particular
new-new pairs occur only in the second term.

**Theorem 10 (sequential continuation).** Suppose the initial state satisfies the
invariant, every epoch respects its declared insertion bound and unique IDs,
every acknowledgment moves one currently pending pair to the sink, every
migration uses accepted region certificates (or another exact partition), and
retained base occurrences/keys are unchanged by migration. Then any finite
sequence of such operations preserves the complete result polynomial under all
commutative-semiring interpretations. If processing eventually drains all
pending pairs after the last insertion, the sink equals the final join.

**Proof.** Induct on transitions. Insertion adds exactly the disjoint delta
polynomial just described to P and changes Q(I) by the same amount. Acknowledgment
adds a pair to S and removes the same pair from P, changing neither their sum
nor ownership multiplicity. Migration preserves every region polynomial by
Theorem 7 and leaves S and I fixed. Thus it preserves their sum. The final
statement follows by P=0. The proof does not impose a completion-time bound,
fairness guarantee, or a bound on intermediate output size. QED.

Preparation constructs and checks all target regions while the source remains
installed and frozen. Only after all checks succeed does a single sequential
assignment replace the installed region list. An exception during construction
or checking leaves the installed source list unchanged. This is the implemented
installation contract. It is not a process-crash recovery protocol.

Retaining current output counts or input lineage alone is insufficient. A
Boolean-cover packet can have exactly the intended support but duplicate some
coefficients. Two different matching-pair sets can have the same cardinality
and the same set of participating identities. Moreover, equality of current
pending polynomials alone does not imply future equivalence when base state
can be lost: one retained left occurrence with no right occurrence and an empty
left relation both have current result zero, but differ after a matching right
insertion. The continuation theorem explicitly retains the needed base context.

## 10. Representation boundaries

For the crown support {(i,j): i != j} on n>=2 rows and columns, the rational rank
of J-I is n. Consequently any explicit positive rectangle partition has at least
n blocks. Boolean covers can be smaller, a classical biclique-cover phenomenon.
However a shared positive arithmetic circuit can compute the same polynomial
with 5n-7 binary addition/multiplication gates using prefix and suffix sums of
y variables, multiplying the sum excluding y_i by x_i, and adding all rows.
No subtraction is needed. The artifact constructs and checks this circuit.
Thus bounds about explicit unshared membership packets are not bounds about
all provenance circuits, all semiring implementations, or all state encodings.

For a balanced power-of-two crown, canonical explicit factor memberships equal
2n log2 n. The optimum within a supplied hierarchy may have the same payload
cost but fewer blocks. Neither observation establishes a runtime speedup over
an existing database engine. Those boundaries apply equally when cardinality
drift is zero.
