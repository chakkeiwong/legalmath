# Recovery after table/reference repair

The adoption checkpoint catalogue now retains 16 large products and its snapshot
catalogue retains 254 inputs. A separate alias restores the focused run-002
product, bringing this extension to four new product paths and one new snapshot.
The current construction is stored once in the gzip archive and restores to the
A1 product, blob and focused result. All earlier catalogue rows remain intact;
before-catalogues and receipts are preserved here. Local originals remain.

The first preservation pass incorrectly included the focused path inside the
adoption catalogue. The restorer correctly rejected its destination as outside
the adoption directory. `repair-catalogue.py` moves that single row into the
separate scoped alias catalogue without changing archives or source products.
The failed catalogue and its original receipt remain preserved. The corrected
three-command recovery check passes in `recovery-validation.json`.

Use these existing fixed commands from the feature worktree:

```text
python3 -m scripts.archive_prospectus_successor_checkpoint restore --campaign adoption
python3 -m scripts.archive_prospectus_successor_checkpoint restore-snapshots --campaign adoption
python3 docs/implementation/prospectus-basf-reference-repair/evidence-preservation/restore-products.py
```

Restore historical repair checkpoints first if their underlying source products
are absent. Do not rerun `preserve.py` in this directory: the before-catalogues
are deliberately exclusive-create. Do not rerun `repair-catalogue.py` either.
A future extension needs a new directory and must retain separate destination
scopes for adoption and focused results.
Successful decompression/hash checks establish recovery of bytes, not legal
acceptance or new independent evidence.
