# Additional grant operator commands

Run from `/home/chakwong/python/legalmath` with the project environment:

```sh
.venv/bin/python scripts/run_assurance_new_grant.py status
.venv/bin/python scripts/run_assurance_new_grant.py phase F0
.venv/bin/python scripts/run_assurance_new_grant.py phase F1-checks
.venv/bin/python scripts/run_assurance_new_grant.py phase F1-pilot
.venv/bin/python scripts/run_assurance_new_grant.py phase F1-breadth
.venv/bin/python scripts/run_assurance_new_grant.py phase F2-tables
.venv/bin/python scripts/run_assurance_new_grant.py phase F2-sources
.venv/bin/python scripts/run_assurance_new_grant.py phase F2-table-repair
.venv/bin/python scripts/run_assurance_new_grant.py phase F2-table-identity
.venv/bin/python scripts/run_assurance_new_grant.py phase F2-source-repair
.venv/bin/python scripts/run_assurance_new_grant.py phase F3
.venv/bin/python scripts/run_assurance_new_grant.py phase F4
.venv/bin/python scripts/run_assurance_new_grant.py freeze-future
```

The exact prefix `.venv/bin/python scripts/run_assurance_new_grant.py` was
approved for trusted execution in this session. Live phases need trusted
network access. Each model request also needs a reservation from the separate
500-call grant. The command approval does not change the grant or issue limits.

The controller records phase attempts before work, retains failures, and writes
`next-phase-plan.json` on terminal completion. At most three engineering attempts
are available per phase. A retry requires a causal repair note referencing its
prior receipt and an actually executed passing focused check. Original model
requests are never refunded. Do not delete journals or raise a counter to make
a phase pass. Resume completed phases by reading their immutable receipts.

Long phases import a copied source tree so implementation of later phases
cannot alter a running investigation. The final verification additionally
copies the complete required repository inputs and checks the delivered source
against that copy. Never overwrite another workstream's shared source or PDF.

`freeze-future` issues no model requests. It runs the observer from the exact
tested snapshot, records a 30-day future publication window and one 120-call
pilot allocation within this same grant, and reports zero observations until
eligible new sources actually arrive. Preserve that snapshot: its absolute
tool and extraction paths are part of the frozen method. A rebuilt installation
needs a new method/window; copying a checksum cannot attest the old environment.
The configuration and excluded development-source bytes are retained beside
the window. Publication metadata, inventory completeness and remote model
version remain qualified.

After the final PDF pages have been inspected and their hashes recorded in
`artifacts/assurance-new-grant/2026-09-29/rendered-review.json`, deliver the local
PDFs and consolidated receipts with:

```sh
.venv/bin/python scripts/run_assurance_new_grant.py finalize
```

Finalization checks phase outputs, the inspected PDF identities, unchanged
historical allowances, all original UCITS pairs, the protected manuscript
baseline, and manuscript changes since the tested snapshot. It writes the
execution result and refreshed successor plan. It records any unrelated
workspace changes separately from the exact verified source archive.
