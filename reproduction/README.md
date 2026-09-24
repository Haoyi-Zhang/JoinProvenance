# Clean reproduction evidence

This directory records the final serial reproduction executed on 2026-09-16
from a fresh extraction of the standalone repository archive candidate.

- `run-ledger.csv`: one row for each of the 97 jobs, including exit code,
  descriptive wall/CPU measurements, cumulative child peak RSS, and worker count.
- `comparison.json`: bidirectional comparison of all generated top-level result
  files with the retained `results/` corpus after excluding explicitly named
  timing/resource fields from equality.
- `summary.json`: claim-linked aggregate summary rebuilt from the clean outputs.
- `logs/`: captured standard output/error for every job.

The run completed 97/97 jobs with exit code zero. The comparator examined 222
files, found no discrete mismatch, no generated file without a retained
counterpart, and no retained claim-bearing file that failed to regenerate. It
intentionally did not compare timings for equality. The summed serial child CPU
time was 204.929699 seconds; summed serial wall time was 205.348004 seconds; the
largest cumulative child peak RSS was 855,868 KiB (835.8 MiB). These are
measurements of this run, not deterministic correctness targets.

To repeat from the repository root:

```bash
python reproduce.py --next 97 --out reproduction-results
python reproduce.py --out reproduction-results --compare
python summarize.py --results reproduction-results --analysis reproduction-analysis \
  --ledger reproduction-results/run-ledger.csv
```
