# Failed verifier controls retained

The actual ordinary CLI passed the seven frozen source readings and preserved the
complete prior answer. The 128 targeted tests passed. Controls then crashed when
`drop-scope` set a span to `None`; the oracle dereferenced it without a shape
assertion. This is our verifier defect. It does not demonstrate package failure.
The remaining controls and installed CLI were not completed.

|Decision|Primary criterion|Veto|Uncertainty|Next action|Not concluded|
|---|---|---|---|---|---|
|Reject this attempt|Ordinary source check passed; adverse and installed checks incomplete|Unexpected TypeError|Full refusal behavior and installed equality|Explicit shape guard repair under a new reviewed admission|Candidate rejection, general recall, legal truth, build closure|

The failed harness does not invalidate the retained ordinary execution. Any
changed source or production digest would invalidate its reuse. No frozen method
or original expectation has been modified; no unchanged stage retry is allowed.
