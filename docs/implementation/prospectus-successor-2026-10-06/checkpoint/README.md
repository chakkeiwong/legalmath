# Restoring the prospectus execution checkpoint

The prior execution generated repeated 128 MB JSON reports and 31 MB source
graphs. Eighteen files at least 8 MiB are stored losslessly as gzip files named
by original SHA-256 in this directory. The manifest preserves original paths,
sizes, original hashes and compressed hashes. Identical bytes share one archive.
All 18 files were decompressed and their hashes checked before committing.
Local original files were retained. Exact-path .gitignore entries prevent
oversized duplicate blobs entering Git.

After cloning, run from the worktree root:

```bash
python3 -m scripts.archive_prospectus_successor_checkpoint restore
python3 -m scripts.archive_prospectus_successor_checkpoint verify
```

Restoration refuses to overwrite different existing bytes. It creates only
manifest-listed files inside this successor evidence directory. The phase
receipts still refer to the original uncompressed bytes and hashes.

This is a storage change, not an execution or legal result. The 8 MiB threshold
is a repository convenience. Reproducing a phase still requires the retained
source PDFs, checkout dependencies and commands recorded in its manifest.
