# Transfer schematics

From the artifact root, run:

```bash
python -B figures/draw_schematics.py --outdir ../paper/figures
```

The optional renderer requires Matplotlib and uses its bundled STIX font family.
It draws the protocol, four-by-five running example, observer relationships,
recurrence alternatives and checker pipeline directly as vector PDFs without
calling TeX. These are conceptual figures, not measured benchmark results.
The running example follows the ten pending pairs listed in the manuscript.
Scientific reproduction remains standard-library only.
