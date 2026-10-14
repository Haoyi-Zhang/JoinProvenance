# Certified hierarchical provenance transfer artifact

This standalone repository accompanies the anonymous internal research paper
*Certified Hierarchical Transfer of Partially Emitted Join Provenance*. It
implements and checks the paper's **restricted** contract:

- an occurrence-identified equality join;
- exact positive polynomial provenance;
- a supplied binary hierarchy on left occurrences;
- arbitrary explicit right subsets;
- positive integer occurrence weights and nonnegative integer block headers;
- a sequential quiescent migration barrier with atomic installation;
- insertions and acknowledgments only, with retained base identities.

It does **not** claim a production database implementation, global
representation or hierarchy optimality, arbitrary SQL, deletion/concurrency/
crash semantics, a shared-circuit optimizer, or performance on external
workloads.

## Repository map

- `provenance/` — packet optimizer, independent certificate checker, exact
  finite oracles, sequential interpreter, and campaign generators.
- `proofs/transfer.md` — complete hand proof, assumptions, and trust boundary.
- `tests/` — standard-library unit and regression tests.
- `results/` — retained raw outputs for every campaign job.
- `analysis/` — claim-linked summaries regenerated from `results/`.
- `reproduction/` — final clean-extraction ledger, comparison, summary, and 97
  captured job logs.
- `reproduce.py` — serial, resumable campaign driver and discrete comparator.
- `summarize.py` — rebuilds aggregate analysis from raw result files.
- `claim_evidence_ledger.csv` — material claims mapped to proofs, tests, raw
  results, manuscript locations, and limitations.
- `external_resources.csv` — historical scholarly, official, template, and runtime
  inventory; `paper/reference-audit.csv` in the companion paper covers its 51
  cited identifiers. Historical full-text labels do not attest to a new full-text
  audit. No scholarly PDF is redistributed.
- `provenance/direct.py` — separately coded full-column-bitset receiver.
- `receiver_costs.py` — same-input complete-path comparison against that receiver
  and trusted sparse recompilation, without a new workload matrix.
- `results/receiver-costs/` — measured protocol rows, exact inputs, local
  environment, campaign receipts, and source bindings for that comparison.
- `example.py` — one compact end-to-end transfer and certificate example.

The implementation uses only the Python standard library. All data are
locally generated, deterministic under the recorded parameters, and contain no
private, production, device, service, or human-subject records.

## Runtime prerequisites and preflight

The worker wrapper supports Linux/POSIX and native Windows. POSIX retains
`resource.RLIMIT_AS` (3 GiB), `resource.RLIMIT_CPU` (40/45 seconds), and one
available CPU. Windows uses a real Job Object: 3 GiB committed process memory,
40 seconds process user CPU time, one active process, kill-on-close, and one
logical CPU affinity. These are different OS accounting definitions, not
interchangeable limits. `reproduce.py` imposes a 44-second parent wall deadline.
No resource placeholder, extra runtime installation, service, or external
solver is used by the native Windows path.

Run this low-cost preflight before reproduction to record the local interpreter
and required facilities without executing a scientific job:

```bash
python - <<'PY'
import os, platform, sys
print("python", sys.version.replace("\n", " "))
print("implementation", platform.python_implementation())
print("platform", sys.platform, platform.platform())
print("affinity", hasattr(os, "sched_getaffinity"), hasattr(os, "sched_setaffinity"))
if os.name != 'nt':
    import resource
    print("RLIMIT_AS", hasattr(resource, "RLIMIT_AS"))
    print("RLIMIT_CPU", hasattr(resource, "RLIMIT_CPU"))
PY
```

The historical campaign used CPython 3.13.5 on Linux. The native Windows
measurement uses CPython 3.12.14, Windows 11 build 28000 and an Intel
Core i7-12700KF, with one logical CPU assigned per worker. No remote CPU model
is inferred. Timing and peak RSS remain descriptive; discrete outputs are the
reproducibility target. Windows peaks are measured PeakWorkingSetSize, not
per-method allocation or the Job's committed-memory limit.

## Immediate checks

Run from the repository root:

```bash
python -m unittest discover -s tests -v
python example.py
python summarize.py --results results --analysis analysis \
  --ledger reproduction/run-ledger.csv
```

Expected outcomes:

- 54 discovered unit and regression methods pass in normal and optimized modes;
- the example constructs and checks a valid packet and reports its blocks;
- `summarize.py` exits zero, reports 380,928 exact-oracle cases and zero
  claim-critical mismatch, and rebuilds `analysis/summary.json` and
  `analysis/benchmark-summary.csv`.

The separate untimed compiler regression is available with
`python -B tests/subtotal_regression.py`, or by its absolute path from any
working directory. It checks the node-local reuse of the active child subtotal
against a test-local literal arbitrary-column-subset partition oracle, exact
coefficients, complete ancestry-state keys, ties, malformed certificates and
sequential continuation. The checker independently reuses each node's active-child
subtotal after its first positive state's inactive checks, while retaining the
original read path for dict-subclass rows; the additional untimed regression is
`python -B tests/checker_subtotal_regression.py`. All semantic state
rows are retained and both branch values are still computed; no smaller state
space or measured runtime gain is claimed. This explicit standalone check is
additional to the discovered inventory, not a rewrite of the historical 97-job results
or older logs.

## Full clean reproduction

The complete campaign comprises 97 serial jobs. The driver pins each scientific
child to one available CPU, starts no child workers, limits address space to
3 GiB, and applies a 40-second CPU / 44-second wall admission limit per child.
It is resumable from its CSV ledger:

```bash
python reproduce.py --list
python reproduce.py --next 97 --out reproduction-results
python reproduce.py --out reproduction-results --compare
python summarize.py --results reproduction-results --analysis reproduction-analysis \
  --ledger reproduction-results/run-ledger.csv
```

The comparator checks 222 generated files in both directions. With the repaired
same-hierarchy pilot it intentionally reports one discrete difference:
`laminar_pilot.json` has 2,700 first-safe improvement observations, not the
historical 3,332; the other discrete fields and all 9,348 pilot oracle instances
are unchanged. The previous pilot compared different trees. Do not suppress
this difference or overwrite `results/laminar_pilot.json`. The current normal
and `-O` runs agree on all 222 discrete outputs; 221 agree with historical data.
There are no new/missing scientific filenames. CPU/wall/RSS fields are excluded
from deterministic equality comparison. A historical `--compare` exit of one
is therefore expected ONLY with exactly that reported pilot difference.

The delivered `reproduction/` directory records the retained fresh-extraction
run that completed all 97 jobs with exit code zero, compared all 222 files with
zero discrete mismatch, and observed 204.929699 child CPU seconds, 205.348004
summed serial wall seconds, and 855,868 KiB (835.8 MiB) peak cumulative child
RSS. The earlier focused TODS repair did not rerun those 97 jobs or either scale job: it
reran the current 35-test suite and the 15 certificate-corruption fixtures, then
regenerated aggregate tables from the unchanged retained raw rows. Accordingly,
`reproduction/logs/unit-tests.txt` truthfully remains the older 31-test log from
the retained 97-job run; the four added regression tests belong to the focused
recheck recorded in `analysis/focused-corrective-recheck.json`. Internal clean
reproduction is not independent external review.

The current oracle distinguishes unreachable supports from every admitted finite
integer total; its per-candidate cost gate remains unchanged. The driver compares
JSONL event files as bytes and retains captured output on timeout. The
2026-10-06 Windows checks called deterministic functions directly, with an
import-only POSIX-resource placeholder that raises on any resource API call and
separate Windows process limits. They passed 39 tests, 29,184 weighted oracle
instances, 8,192 boundary cases, 15 corruption fixtures, 16 sharp-height cases,
and 96 traces with 9,551 transition checks plus replay. These are local checks,
not a rerun of the full Linux manifest or the retained timing/scale measurements.
The later native Windows normal and `-O` checks execute all 97 entries,
including both scale jobs, the full 380,928-instance weighted oracle (also
checking the direct receiver), 8,192 boundary cases, 15 certificate fixtures,
96 traces/9,551 transitions and replay. `-O` repeats those same domains; it
does not double independent evidence. All 45 scientific `assert` statements
have been replaced by explicit checks. Controlled wrong-oracle, boundary,
formula and missing-detection regressions now fail closed under both modes.

The compiler also accepts any valid node numbering while retaining the trusted
dictionary. A proper root-first tree formerly failed honest completeness; an
explicit postorder traversal repairs that rejection. Tests include all 120
numberings of one five-node tree, not 120 distinct workloads. This change does
not optimize a hierarchy or change the recurrence's mathematical objective.

The `scientific-checks.yml` workflow is configured for the flat repository root
on Ubuntu 24.04, including pushes to `main`. It runs the 97-job manifest,
bidirectional discrete comparison, and summary mismatch gates within a
600-second whole-run deadline. Existing child limits remain 3 GiB and
40 CPU / 44 wall seconds; raw outputs are uploaded even after a failed gate.
The workflow has been prepared, not executed or published by these local checks.
Its historical comparison step now needs the independently reviewed pilot
reference transition above; local success is not a claim that public CI passes.

## Same-information receiver costs

Both packet-only receivers establish exact coefficients and the deterministic
fixed-tree payload/block optimum. They do not validate a producer table omitted
from their protocol. The full-column-bitset implementation calls neither the
compiler nor checker, but shares the theorem and research process. Sparse
recompilation shares the producer implementation and is the simpler trusted
baseline. All protocols use the same source, hierarchy, weights, and producer;
even a packet-only protocol pays for the current producer's table construction.

The study reuses the 36 existing benchmark supports in two regimes: 72 weighted
inputs, three order-rotated repeats, 216 paired triples and 648 method rows per
mode. Nonrandom seed aliases are collapsed, not counted as extra supports.
Timing includes compilation, actual compact-JSON encoding/decoding, receiver
verification and local tuple installation. Wire and common context JSON bytes
are measured separately. These are authored serialization choices, not measured
database wire bytes, transport latency, or total retained-base storage.
Source generation, hierarchy construction and common context assembly are
outside these given-context protocol timers. Consequently the measured path
is not a full database-executor barrier or physical-design cost. The same
supplied context and producer are used by every receiver.

```bash
python -B -m provenance.resources -- receiver_costs.py --n 512 --out OUT
# At n=2048 use all first indices 0..17, each with --count 1:
python -B -m provenance.resources -- receiver_costs.py --n 2048 --first 0 --count 1 --out OUT
```

Use an outer 44-second timeout per command as well as the worker limits. The
unchunked n=2048 measurement was terminated by the native Job limit and has no
success record; one-input chunks cover exactly the same 18 existing inputs.
The artifact retains ties and losses: all three receivers install the same
packet, giving zero payload-selection gain, while certificate wire size and
runtime must be assessed against both direct receivers. The aggregate and all
raw timings in `results/receiver-costs/` are descriptive local measurements.
The source inventory retains the measurement-time campaign in
`measured-sources/`; its original path is recorded in the provenance record.
The current maximal-safe-node baseline traverses the supplied dictionary
iteratively, so valid node renumberings and tall trees use the same policy.
Existing timings remain bound to their measured sources, not to this traversal
implementation. Receiver-cost measurements call neither traversal baseline.
The sparse method timing series uses all 28 source-bound benchmark chunks in
`results/measurements/`: 504 rows on the same 36 supports and 72 weighted
inputs. `source-bindings.json` identifies the measured Python sources, input
files and command outputs. The analysis table and paper runtime series derive
from these records; the large-scale timings and receiver costs retain their
separately stated measurement origins.

## Claim-critical commands

The full driver is the preferred route. The following focused commands expose
the major gates (replace `OUT` with a writable directory):

```bash
python -m provenance.hierarchy_campaign exact 4 4 0 8192 0 --out OUT
python -m provenance.hierarchy_campaign boundary --out OUT
python -m provenance.hierarchy_campaign mutations --out OUT
python -m provenance.hierarchy_campaign stream --out OUT
python -m provenance.campaign mutations --out OUT
python -m provenance.campaign dag --out OUT
```

They respectively check an exhaustive weighted 4×4 chunk against the independent
arbitrary-subset oracle; the three-row laminarity boundary; fifteen certificate
corruptions; 96 insertion/migration traces; coefficient versus weaker observers;
and the explicit-packet/shared-circuit boundary.

## Evidence interpretation

The executable exhaustive checks are finite checks, not machine-checked proofs
of unbounded theorems. General statements are supported by the hand argument in
`proofs/transfer.md`; code checks attack small counterexamples, integration
paths, and implementation errors. The benchmark method columns are `time.perf_counter` elapsed intervals. The
scale-summary wall intervals additionally include the independent bitset observer
and surrounding campaign-body work, but exclude imports/resource setup and result
serialization. Their peak RSS is the process-wide maximum, not a method-only
measurement. The retained 97-job ledgers instead time complete child invocations;
their child-CPU totals exclude the parent runner, and their summed command wall
time excludes parent work between commands. These are different measurement
scopes, not alternative counts of scientific instances. The evidence establishes
neither a production speedup nor a claim that
payload size equals peak memory or network traffic.

The optimizer's exactness holds only for the supplied laminar hierarchy and the
stated additive positive-entry cost. The compiler and checker each sort every
serialized right factor in trusted dictionary order, so their honest time bound
includes `sigma(Pi) = sum |V| log(|V|+1)` in addition to output size. The checker
returns an ordinary statistics dictionary with `checked=True`; it is not an
immutable checked-packet capability. Sequential installation reads
`packet.blocks` after a successful check and therefore assumes a benign
same-thread caller. Dense pair/bitset coefficient expansion is performed only by
the independent observer. The method does not choose a hierarchy, optimize all
biclique covers, or optimize arbitrary shared positive circuits.

## License and attribution

Original code, proof text, tests, and generated outputs are available under the
MIT License in `LICENSE`. The supplied ACM class and bibliography style retain
their publisher license in the separate paper package and are not part of this
standalone repository. Scholarly and official resources are inventoried in
`external_resources.csv`; none is required at runtime and none has been modified
or redistributed here.
