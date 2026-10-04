# Running the prospectus evidence closure

Use this checkout and its existing environment:

`/home/chakwong/python/legalmath/.worktrees/bond-gap-closure`

Branch: `feature/prospectus-evidence-master`.

## Exact command forms

```text
.venv/bin/python scripts/run_prospectus_evidence_master.py close run
.venv/bin/python scripts/run_prospectus_evidence_master.py close status
.venv/bin/python scripts/run_prospectus_evidence_master.py close verify
.venv/bin/python scripts/run_prospectus_evidence_master.py close rules
.venv/bin/python scripts/run_prospectus_evidence_master.py close check
.venv/bin/python scripts/run_prospectus_evidence_master.py close phase S2
.venv/bin/python scripts/run_prospectus_evidence_master.py close inspect hkma-ic1 1
.venv/bin/python scripts/run_prospectus_evidence_master.py close render deutsche-at1-2025 53,54
.venv/bin/python scripts/edit_workspace_files.py /tmp/prospectus-edits.json
```

Run each as a direct command with the checkout supplied as the tool's working
directory. Do not add a shell wrapper, an absolute interpreter path, an inline
environment assignment, a pipeline or output redirection. The runner sets CPU
mode and its working directory and launches bounded child commands with fixed
argument lists. Command forms are checked by the installed `codex execpolicy
check`; the saved rule already permits the literal runner prefix and editing
helper. The project policy `allowlist.json` defines the successor's finite
operations, hosts and budgets. `allow.rules` supplies a portable narrower rule;
the installed broader script-specific rule already covers it, so no additional
global rule is required.

The local editor accepts guarded JSON replacements or whole-file writes with a
prior hash. It restricts targets to this checkout, /tmp and TMPDIR, rejects
protected metadata and escaping symlinks, and validates the whole batch before
writing. Ordinary local edits retain the user's standing authorization.

The host sandbox currently fails at startup with an unsupported
`/mnt/wslg/distro` mount. Saved approvals cover the direct command forms used
here. A project rule cannot repair that host mount or grant access to protected
paths. Do not promise that arbitrary future commands can never prompt.

## What happens between phases

The controller verifies protected history and prior receipts before execution.
Each attempt records method/input hashes, command, environment, CPU mode,
elapsed time, outputs, actual repairs and remaining requirements. Failed
attempts remain immutable. Evidence bytes referenced by input JSON and retained
HTTP responses are bound as well as the JSON itself. A source, method, factual
input or review change reopens its consumers. The next-phase plan is refreshed
after each attempt; a second run with unchanged inputs performs no new phases
and makes no new HTTP requests.

An evidence wait permits independent phases to continue. It does not mean the
underlying gap has closed. A failed method needs a causal code repair and checks;
a disputed interpretation needs source work and a counterexample before a
reader repair. There is no arbitrary shell-command or self-approval field.

## Supplying evidence

Inputs live under `docs/prospectus/evidence-closure/`:

| File | Consumed by | Effect |
| --- | --- | --- |
| assessment.json | S1/S3 and dependants | Separate requested effective and known timestamps. Neither invents an observation date. |
| source-inputs.json | S1 | New document IDs and reviewed changes to existing issue selections. New originals/extractions require hashes; changed selections require current admissions. |
| admissions.json / decisions.json | S1 | Exact page, edition, language, precedence, amendment and per-reference reviews. Missing or changed bindings keep references open. |
| public-queue.json | S2 | Exact reviewed HTTPS requests with key, URL, gap and review reason. Redirects are separate reviewed queue entries. |
| source-work-reviews.json | S2 | Source-bound closure judgment for every affected issue in a named work order. A download cannot supply this judgment. |
| facts.json | S3 | Retained source bytes, hash, media_type, origin, observation/effective/freshness times, and issue-specific typed assertions/context/route/policy. |
| clause-reviews.json | S4 | Exact issue/evidence binding and expected disposition. Disagreement produces a repair requirement; it never changes the reader by itself. |
| scenarios.json / mechanism-reviews.json | S5 | Explicit hypothetical or source-dependent inputs for named issue/edition profiles and source-bound formula reviews. |
| challenge.json | S6 | Complete selection, exposure, adjudication, rubric and budget protocol, frozen before source exposure. |
| challenge-evidence.json / challenge-adjudication.json | S6 | Every selected case, including unavailable cases, and independent source judgments; changed frozen methods reject reuse as fresh validation. |
| human-review.json | S7 | Scoped qualified-human decision bound to the exact review packet, with matching retained attestation. It cannot clear another phase's evidence gaps. |

The schemas and counterexamples are in `closure_sources.py`,
`closure_reviews.py` and `tests/prospectus/test_closure_intake.py`.
Unknown issue IDs, stale reviews and evidence mismatches are rejected. A new
source observed after the selected known timestamp cannot support that earlier
assessment. Change the assessment deliberately when investigating a later date.

## Remaining execution boundaries

The user authorised 100 additional public requests on 2026-10-04. The cumulative
continuation-plus-closure ceiling is 112. All 12 earlier requests remain charged,
including failures and redirects. The former 24-request proposal is superseded.
A separate fresh-case challenge allocation remains zero pending its protocol.
S2 inspects retained response bytes and records unreviewed PDF candidates or
HTML navigation links; neither downloads nor extraction constitute admission.

The three new profiles provide bounded conditional arithmetic. Full price
adjustments, legal time-counting, actual settlement and additional issuer
profiles remain incomplete. All 36 existing cases are exposed development
evidence. Danske Bank cannot be used as a fresh issuer family. Fresh-case
validation needs exact eligible cases, an independent adjudicator and an
approved allocation. Actual private facts and qualified human acceptance must
be supplied by their real sources. No external messages or transactions are
sent by this program.
