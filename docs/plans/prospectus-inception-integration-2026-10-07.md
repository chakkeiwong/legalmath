# INCEpTION integration: reviewed execution plan

Baseline: `bada667759a7d9f87ffc01235ff3a012601f5b75` on
`feature/prospectus-evidence-master`. This continuation implements the unfinished
annotation-tool integration identified after A0–A6. Source interpretation, actual
coupon premises and authentic independent legal acceptance remain separate work
in `docs/implementation/prospectus-adoption/NEXT-PROGRAM.md`.

## Question and evidence contract

Can the pinned INCEpTION 38.0 server accept our evidence schema and annotations,
retain a deliberate edit, and export data that our engine recovers without
changing source editions, quotations, Unicode offsets, discontinuous groups or
semantic relations? Can its actual project configuration support separate first
readings with recommendations and automatic pre-merge disabled?

Comparator: the exact A3/attempt-004 packet and Cassis 0.10.1 XMI result, plus a
retained BASF development excerpt with explicitly provisional annotation labels.
The primary pass criterion is exact equality of the expected edited packet and
the packet reconstructed from the actual server export. HTTP success, a browser
screenshot, annotation counts and the prior Cassis round trip are insufficient.
Each reader export must remain separately recoverable; a changed source hash,
text, quote, group member, offset or relation must be detected. An administrator
and synthetic test accounts do not establish authentic reader independence.

Hard promotion vetoes: source/annotation loss, wrong edit, invented provenance,
unverified project settings, shared predictions in a claimed blind workflow, or
an untested claimed interface. These trigger adapter/configuration repair.
Continuation vetoes: corrupt source or release bytes, an incompatible runtime,
unexpected paid/model execution, exposure beyond localhost, or the resource
bounds below. Repairable candidate failure does not stop unrelated checks.
Timing and counts are explanatory only. No legal correctness, population
accuracy, independent adjudication or production deployment is concluded.

Evidence goes to `docs/implementation/prospectus-inception/`: source/release
receipts, exact commands and environment, immutable numbered trial attempts,
original and edited packets, individual server exports, configuration, tests,
result/decision table and refreshed next-work note. Do not rewrite A3 history.

## Skeptical review before implementation

The previous plan needs these corrections before execution:

1. A Cassis serialization test is the wrong baseline for claiming a running
   annotation platform. Require server imports/exports and an explicit edit.
2. `blind_protocol` in our JSON is only a declaration. Inspect actual project
   settings, recommendations, curation strategy and account permissions.
3. The system Java is 11; the pinned release uses Spring Boot 3.5.5 and Wicket
   10.6. Use the existing Temurin 17.0.20.1 toolchain, inspect the release and
   startup result, and bind the executable bytes. The older guide's Java claim
   is not authority for this release's runtime.
4. A real server may normalize/drop unknown types or offsets. Validate its
   exported type system and all semantic fields, including group links and
   source hashes, before accepting any packet. Never silently reconstruct lost
   evidence from the original input and call it preserved.
5. Distinguish a REST annotation upload/edit from a browser editor action.
   Record which was actually exercised. Attempt a browser edit with the retained
   Playwright/browser tools; browser failure cannot be relabelled a UI pass.
6. Existing development packets cannot establish an unexposed evaluation cohort.
   Test accounts are labelled synthetic. Prepare the real-reader protocol and
   ingestion checks without manufacturing readings or contacting anyone.
7. Trial execution uses an isolated local repository/database and localhost-only
   port. Preserve the trial project and exports; stop only the server process
   created by this program. No shared INCEpTION installation is modified.

Audit verdict: PASS for this bounded integration sequence with those corrections.
The finite preservation assertions answer the engineering question; they cannot
answer the legal acceptance question.

## Defaults and assumptions

| Choice | Provenance / status | Failure mode and earliest diagnostic |
|---|---|---|
| INCEpTION 38.0 | Release matched to retained guide/source; reviewed version | Release/runtime mismatch: official asset digest, class version and startup check |
| Standalone JAR | Official GitHub release, 352,903,149 bytes; convenience packaging | Wrong/downloaded bytes: require SHA256 `6c0b54c262a36d6ccaaa2e37796bc728c656fdf8ea0ae40c7854cb54bdb9c876` |
| Temurin 17.0.20.1 | Existing local toolchain; compatibility hypothesis | Newer Java required: inspect/start before creating a project |
| Cassis 0.10.1 | A3 baseline; explicit optional dependency | New server schema: compare exported type definitions and exact packet |
| Character-level spans and explicit group links | Exact quotation requirement; reviewed design | UI token snapping, missing group links: Unicode/multiline boundary cases |
| Recommendations absent and no automatic merge | Original independent-reading design | Metadata flags differ from server: inspect exported project configuration and runtime |
| Synthetic account separation | Harness convenience only | Mistaken independence claim: mark all output as implementer test evidence |
| Two development packets | Smallest discriminating test, not coverage sample | Overfitting: preserve limits; no statistical ranking or family generalization |

## Execution and repair sequence

1. **Prepare.** Retain official release metadata and relevant source/API/config
   definitions. Download/hash the standalone JAR in a git-ignored local resource
   directory. Reuse Java 17, Cassis and the existing browser tooling.
2. **Adapt.** Implement strict XMI exchange and project configuration using the
   inspected server API. Separate exported source identity from an external
   expectation; reject a packet that only appears correct after filling gaps.
   Add focused regressions for source/quote drift, UTF-16 boundaries, group links,
   relation endpoints and changed labels.
3. **Run the actual server.** Create the isolated project, inspect settings, import
   both development packets and retain an unedited export. Make a deliberate edit,
   re-export and compare to a predeclared expected packet. Exercise separate
   synthetic reader records and preservation of original exports. Record browser
   and REST coverage separately. Repair failures within the bounds below.
4. **Verify and hand off.** Run focused tests and the relevant existing regression
   suite. Add the actual server result to the tool-status documentation and
   refreshed next-work plan. Prepare blind first-reading and separate adjudication
   instructions. Real readings remain pending until supplied by actual people.

Intended exact entry points (the implementation will retain actual commands):

```text
python3 -m scripts.prospectus_inception prepare
python3 -m scripts.prospectus_inception run
python3 -m scripts.prospectus_inception verify
```

Preparation downloads at most 800 MB of new runtime/source bytes and uses at most
30 external HTTP fetch attempts. Local data/storage is capped at 2 GB for this
integration. Each server attempt has at most 300 seconds startup and 900 seconds
workflow time, with a 2 GB Java heap and two active processors. At most three
attempts per unchanged method/input; a repair must explain the changed input or
method before further attempts. No GPU, model download, external annotation
service, messages to readers or paid API is needed. The local server is stopped
after each attempt. Do not retry a successful trial without a new defect/change.

## Pre-mortem and continuation decision

### Reviewed continuation after run-004

The proposed REST overwrite is wrong for the available timestamp evidence.
The real XMI exports contain no CASMetadata. `RAnnotation.formatTimestamp`
reports only seconds, whereas `FileSystemCasStorageDriver` compares the CAS
timestamp with filesystem milliseconds. Re-encoding with `-1` consequently
fails on an existing record. We will not fabricate a timestamp, relax the
storage check, or delete/recreate the record. Use the supported browser editor
for the deliberate label changes on both packets, then compare REST exports
against the frozen expected edits. Preserve and recheck both separate synthetic
reader originals. REST replacement remains unsupported by this adapter.

Skeptical audit: PASS for this revised mechanism. The comparator remains exact
packet preservation, not HTTP success. Browser inspection alone is diagnostic
and cannot pass the edit criterion. Account roles and curation behavior require
separate assertions; administrative browser access proves no reader isolation.
The finite engineering test has no stochastic ranking or legal-acceptance claim.

The final access check uses a localhost-only, synthetic guest invitation to open
each project-bound test account in a separate browser session. Each session must
display its own original packet and receive an explicit denial when requesting
the other reader's or administrator's annotations. This tests authorization
within an established session. The invitation allows entry by display name and
does not authenticate a human identity; real independent readings must use
separate authenticated accounts, with guest invitations disabled. Passing this
test cannot establish account ownership or independent readers. Audit PASS for
this stated boundary, with raw denial snapshots retained.

A plausible false pass would upload XMI and compare an untouched local copy,
ignore stripped features, reconstruct deleted links, or mistake synthetic account
names for independent people. Preserve raw server responses and compare all
required fields; mutate fields to show the checker detects loss. A plausible
false failure would use Java 11, the wrong API format identifier or token-aligned
layers. Resolve those environment/schema issues before rejecting the platform.

If the server exchange fails, identify whether the problem is input, configuration,
adapter or platform behavior and execute the corresponding bounded repair. If it
passes, the next evidence is an authentic independent review of source-complete
contracts; no amount of replay can generate that evidence. Keep the existing
source/interpretation/coupon program open while closing this tool-integration gap.
