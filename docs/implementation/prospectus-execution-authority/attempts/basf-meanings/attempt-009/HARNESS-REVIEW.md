# Bounded preparation-label correction

The `prepare` stage passed its structural checks but copied the attempt-008
section-12 disposition reason into newly selected page-131 procedural units.
That label was wrong; the sentence spans, selected roles, original source bytes
and five prior section-12 meanings were not changed. The original
`common.json.gz`, `prepare-started.json` and `prepare-result.json` are retained
as evidence of the mistake, not used as the accepted downstream common input.

The first `repair_labels` command failed its assertion before writing a
corrected common file. Its matching driver was reconstructed and checked
against the started runner hash in `run-repair-v1.py`. Diagnosis showed that a
global text replacement would also change 14 previously admitted section-12
unit reasons. A second call to the same action name was made in error and
failed at exclusive creation of its already existing started marker before
performing any repair; it did not run the candidate computation. That failed
call is not counted as a successful stage.

The changed `repair_labels_v2` action targets only the 27 newly promoted
page-131 units; line17 was already operative in the protected baseline. It
requires the copied wrong reason in exactly those units and changes only their
disposition/assembly descriptions plus the resulting assembly digest. It
preserves all candidate/baseline clauses, selected contract and earlier
section-12 reasons. The subsequent baseline construction rejected this first
correction: the copied `assembly.reviewed_dispositions.units` still contained
the wrong reason, although the request and assembly units had been corrected.
The first diagnosis retained `construct-difference.json`: all assembly units
and selected-contract data were equal; the nested review metadata differed.
A second bounded diagnostic identified the nested `units` field specifically.
Earlier commentary incorrectly described this as a digest-only mismatch. The
underlying mismatch was the retained nested descriptions, which changed the
digest as a consequence.

Two intervening calls did not run a construction: `baseline construct-v2`
failed because the driver did not implement that action, and a repeated
`baseline construct` failed at the existing immutable started marker. Together
with the earlier duplicate repair call, these are execution mistakes, not
production or legal failures. None is reported as a successful computation.
The attempt exceeded the original plan's one-repair bound; describing all
these actions as one episode would hide that deviation. This record preserves
the actual cumulative actions rather than retroactively claiming plan compliance.

`materialize_corrected_p2` then ran the existing production constructor, checked
the selected contract and every assembly unit, and retained the resulting full
payload as `common-corrected-v2.json.gz`. The separate
`baseline construct_v3` rebuilt that input and required full P2 equality,
including nested review metadata and hashes. It passed. Candidate and omission
construction reuse requires equality of every request field except supplied
clauses. Only this fully checked corrected input feeds downstream stages; the
original and intermediate files remain retained. No sealed earlier attempt
was edited, and no production acceptance condition was weakened.

Finalization review: no further implementation or construction repair is
authorized within this attempt. The already planned interpretation/consumer
and comparison checks may finish using the proved corrected construction.
Any failure in those checks must be retained and reviewed before another
computation. The result note must explicitly report this harness deviation,
separately from whether the eleven original-source readings pass.
