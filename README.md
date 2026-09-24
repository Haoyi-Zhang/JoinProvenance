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
- `tests/` — 31 standard-library unit tests.
- `results/` — retained raw outputs for every campaign job.
- `analysis/` — claim-linked summaries regenerated from `results/`.
- `reproduction/` — final clean-extraction ledger, comparison, summary, and 97
  captured job logs.
- `reproduce.py` — serial, resumable campaign driver and discrete comparator.
- `summarize.py` — rebuilds aggregate analysis from raw result files.
- `claim_evidence_ledger.csv` — material claims mapped to proofs, tests, raw
  results, manuscript locations, and limitations.
- `external_resources.csv` — complete scholarly, official, template, and runtime
  inventory. It covers all 38 bibliography identifiers plus the publisher assets,
  venue/policy pages, and Python runtime; no scholarly PDF is redistributed.
- `example.py` — one compact end-to-end transfer and certificate example.

The implementation uses only the Python standard library. All data are
locally generated, deterministic under the recorded parameters, and contain no
private, production, device, service, or human-subject records.

## Immediate checks

Run from the repository root:

```bash
python -m unittest discover -s tests -v
python example.py
python summarize.py --results results --analysis analysis \
  --ledger reproduction/run-ledger.csv
```

Expected outcomes:

- 31 unit tests pass;
- the example constructs, checks, and installs a valid packet;
- `summarize.py` exits zero, reports 380,928 exact-oracle cases and zero
  claim-critical mismatch, and rebuilds `analysis/summary.json` and
  `analysis/benchmark-summary.csv`.

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

A successful comparison checks 222 generated files in both directions and reports
no discrete mismatch, no unexpected generated file, and no retained claim-bearing
file that failed to regenerate. CPU/wall/RSS values are descriptive and are
excluded from deterministic equality comparison.

The delivered `reproduction/` directory records a fresh-extraction run that
completed all 97 jobs with exit code zero, compared all 222 files with zero
discrete mismatch, and observed 204.929699 child CPU seconds, 205.348004 summed
serial wall seconds, and 855,868 KiB (835.8 MiB) peak cumulative child RSS. Internal clean
reproduction is not independent external review.

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
paths, and implementation errors. Benchmark time includes Python, observer, and
certificate work. It establishes neither a production speedup nor a claim that
payload size equals peak memory or network traffic.

The optimizer's exactness holds only for the supplied laminar hierarchy and the
stated additive positive-entry cost. It does not choose a hierarchy, optimize
all biclique covers, or optimize arbitrary shared positive circuits.

## License and attribution

Original code, proof text, tests, and generated outputs are available under the
MIT License in `LICENSE`. The supplied ACM class and bibliography style retain
their publisher license in the separate paper package and are not part of this
standalone repository. Scholarly and official resources are inventoried in
`external_resources.csv`; none is required at runtime and none has been modified
or redistributed here.
