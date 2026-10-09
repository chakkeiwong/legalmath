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
/tmp/prospectus-adoption-tools/bin/python -m scripts.prospectus_integration_codec admit /tmp/reading-source.json /tmp/reader-export.xmi /tmp/reader-admitted.json --types /tmp/reading-types.xml
/tmp/prospectus-adoption-tools/bin/python -m scripts.prospectus_integration_codec admit /tmp/reading-source.json /tmp/reader-export.zip /tmp/reader-admitted.json
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

The current closure workflow uses `review_records.py` to validate administrator-
signed assignments, normalized exports, first readings, adjudication and family
exposure. The signing key must be supplied by the actual trusted administrator;
the development key used in tests cannot authenticate a real reviewer. Bind the
normalized export to exact raw text maps; corrected spans use the admitted
correction map and cannot borrow a source quotation for inserted or uncertain
text. `prediction_execution.py` executes the frozen requests and the scorer
recomputes them before accepted scoring. Caller-typed predictions or integrity-
only receipts cannot satisfy release.

For a cross-document condition or exception, preserve separate source exports
and add a reviewed `reviewed-annotation-meaning.v2` relation binding both packet
hashes and group endpoints. This is an application-level reviewed link, not a
claim that a single CAS natively spans documents. Live reader use of this new
link workflow still needs validation. A standalone-XMI export requires its
matching type system; ZIP must include it. The codec exercise tests both forms.

Use the isolated closure namespace for current engineering checks:

```text
python3 -m scripts.prospectus_delivery --program closure status
python3 -m scripts.prospectus_delivery --program closure refresh
```

Do not rerun historical adoption or repair programs to manufacture current
evidence. The executable review interfaces and mutation examples are in
`tests/prospectus_successor/test_closure_reviews.py`; a production administrator
export/identity integration and actual assignments remain pending. Reading
records alone do not establish legal acceptance. Actual-event questions also
require the dated legal, regulator, issuer and client facts appropriate to the
question. Compass Group PLC's EMTN family is development-exposed by the current
financial exercise and must be excluded from an unseen evaluation cohort.
