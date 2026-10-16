# Evidence master operation

Run from /home/chakwong/python/legalmath:

    .venv/bin/python scripts/assurance_evidence_master.py run

The requested environment prefix is exactly:

    [".venv/bin/python", "scripts/assurance_evidence_master.py"]

The same prefix covers status and offline preflight. There are no arbitrary path,
command or URL flags. The repository allowlist documents permitted behavior; it
does not itself grant execution permission. Trusted execution is required while
the WSL bubblewrap startup error persists.

The master freezes code before dispatch and executes that snapshot. It verifies
old result/source/grant hashes, reserves every provider attempt durably, and keeps
all failures charged. A whole-master lock prevents overlapping campaigns. A
saved complete provider response is validated and recovered without another
call. An interrupted call with no retained response remains an explicit spent
frontier. Two consecutive dependency failures stop provider breadth.

Each phase records a result receipt and refreshes JSON and real Markdown plans.
Invalid schema/citation responses get at most one causal, counted correction
under the same canonical issue identities and the 16-call repair reserve.
Source/meaning uncertainty does not trigger repeated prompting or stop unrelated
work. Model responses and downloaded documents cannot choose commands.

P0 executes locator repairs and tests. P1 acquires official sources and reviews
authority/date evidence. P2 reviews discriminating cases and the vocabulary
bridge. P3 updates all 35 reading dispositions, preserves all historical
questions, recomputes conditional checks and invokes the existing runtime
qualification. P4 reviews actual results and closures. Release eligibility stays
false. No manuscript, prospectus, publication, commit or deployment is included.

Changing frozen code or evidence stops the run. An engineering revision requires
a separately recorded causal repair and successful checks; never delete a
manifest, reservation or failed response to get a pass. Inspect next-phase-plan
and final-result for pending work and legal/evidence limits.

After a recorded engineering failure, the already approved prefix also supports:

    .venv/bin/python scripts/assurance_evidence_master.py repair

This uses the separately recorded repair-allowlist.json amendment. It creates a
new immutable snapshot, executes focused tests and actual-source packet checks,
and activates it only after both pass. The original snapshot, manifest,
reservations, phase outputs and failed attempts remain unchanged. Resume with
the original run command; completed phases are replayed from receipts.

A supervisor-recorded substantive scope defect can trigger one counted
correction against the same historical task/issue IDs. This does not grant a new
budget or reset attempts. The input and old response are retained; the correction
is reviewed before being treated as the active disposition.
