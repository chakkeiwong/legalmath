# Recovery record

This continuation extends the adoption catalogue from ten to thirteen large
products and from 252 to 253 snapshots. Both previous catalogues are copied here;
their original rows and all original product bytes are preserved. No previously
retained snapshot source needed rebinding. Recovery sources themselves, including
compressed contents and retained/model files, were checked against recorded hashes.

The BASF run-002 and run-003 products are byte-identical to adoption A1 attempt-007.
`product-aliases.json` binds both to the same lossless archive, avoiding duplicate
11 MB files in Git. The original local files remain present and unchanged.

Recovery and checks:

```text
python3 -m scripts.archive_prospectus_successor_checkpoint restore --campaign adoption
python3 -m scripts.archive_prospectus_successor_checkpoint restore-snapshots --campaign adoption
python3 docs/implementation/prospectus-basf-scope-repair/evidence-preservation/restore-products.py
python3 -m scripts.archive_prospectus_successor_checkpoint verify --campaign adoption
python3 -m scripts.archive_prospectus_successor_checkpoint verify-snapshots --campaign adoption
```

Both standard verification commands and the alias restoration check passed.
The helper refuses to overwrite differing products. `preserve.py` is the exact
one-time extension script; it refuses to overwrite its before-copies and should
not be rerun unchanged. Later extensions need their own evidence directory.
