# Preparing actual independent readings

The imported-packet trial demonstrates exchange and browser label edits. The
later [integration trial](../prospectus-integration-repair/authoring-011/result.json)
also demonstrates creation, deletion, boundary replacement, discontinuous groups
and semantic relations from initially empty evidence, using ordinary password
accounts with guest entry disabled. Both use development examples and synthetic
accounts. None of their records are independent first readings or accepted legal
conclusions.

Before assigning work, freeze the named instruments, dated questions, source
editions, complete terms and incorporated documents. Resolve or expressly bound
unresolved source intervals. Preserve the family/template/exposure register and
exclude development documents and overlapping families from any claimed unseen
cohort. Keep the questions and scoring denominator fixed before answers arrive.

Create separate authenticated accounts for two actual readers. Disable guest
invitations: the synthetic trial's invitation accepts a display name, which is
unsuitable for establishing ownership of a reading. Give each reader only the
ANNOTATOR role; managers and curators can inspect other people's work and must
not act as blind readers. Restrict remote API credentials to the coordinator.
Record actual assignments and prior exposure; do not infer independence from
different usernames or low agreement.

Import source identity and the exact text reviewed for each document. For
first readings, do not import the trial's provisional labels, suggested answers,
model predictions or another reader's annotations. Keep all recommenders absent
and integrated curation's automatic merge disabled. Before real use, repeat the
access checks with the actual account authentication method and confirm there
are no suggestions or access to another reader's work.

Use the separate draft schema in `annotation_authoring.layers()`: immutable
`LegalSource`, `DraftEvidence` with `groupId`/`label`, and `DraftRelation` with
`relationId`/`kind`. The older imported-evidence schema remains available for its
strict exchange workflow. Mixing imported and draft evidence is rejected.

The coordinator prepares a JSON envelope containing `text` and `source` with
`document`, `source_sha256` (the original document bytes) and `text_sha256` (the
exact UTF-8 text). Keep the original document and extraction provenance with
that envelope; do not substitute a hash of invented text for an original source.
From this worktree, the installed Cassis worker produces identity-only XMI and
the type system, and later admits a raw reader export without any expected labels:

```text
/tmp/prospectus-adoption-tools/bin/python -m scripts.prospectus_integration_codec empty /tmp/reading-source.json /tmp/reading-empty.xmi /tmp/reading-types.xml
/tmp/prospectus-adoption-tools/bin/python -m scripts.prospectus_integration_codec admit /tmp/reading-source.json /tmp/reader-export.xmi /tmp/reader-admitted.json
```

Configure the draft layers in the coordinator's project and import the empty
source into each separate reader record. Select text and enter its group ID and
label. For discontinuous evidence, give all pieces the same group ID and label,
then draw `same_evidence_group` links from the earliest piece to every later
piece. Semantic relations connect the earliest pieces of the respective groups;
every relation needs a unique ID. Boundary replacement was tested by deletion
and reselection; direct handle resizing has not been tested. The decoder derives
quotations and offsets from actual selected text and verifies source identity,
links and group consistency. Readers do not type provenance fields.

After feature editing, allow the editor's queued saves to complete and reload
before export. The browser driver checks the actual Wicket channel queue;
network inactivity alone previously raced a second change handler. The trial's
`decode` codec action additionally compares against predefined experiment
answers; actual first readings use `admit`, which has no such answers.

Hidden or visible feature controls are not a provenance security boundary.
Export validation rejects inconsistent source evidence; it cannot authenticate
a person or establish why an annotation is absent. Preserve raw exports before
transformation, retain the transformation receipt, and explicitly review changes.
Do not reconstruct missing evidence from an earlier packet. Local review forms
remain a fallback where the tested interface does not fit a reader's needs.

Freeze each reader's first export before either can inspect the other's work.
Retain its bytes, source hashes, assignment, submission time and authenticated
reader identity separately. A distinct adjudicator then reviews disagreements,
exact quotations, source scope, legal interpretation and unsupported premises.
Agreement alone is insufficient; include supported positive and negative cases
and record all failures and exclusions in the frozen denominator.

Use the existing A6 review admission only when those genuine records exist:

```text
python3 -m scripts.prospectus_delivery --program adoption repair --record /tmp/reviewed-record.json
python3 -m scripts.prospectus_delivery --program adoption run
python3 -m scripts.verify_prospectus_adoption
```

The admission requires obligation, phase, filename, prior hash, content and
reason as documented in `../prospectus-adoption/NEXT-PROGRAM.md`. It records an
input for assessment; it does not turn a declaration into evidence of legal
acceptance. Actual-event questions additionally require the dated legal,
regulator, issuer and client facts appropriate to the question.
