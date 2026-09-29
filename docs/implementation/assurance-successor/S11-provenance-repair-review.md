# Retained UCITS dossier and current implementation

28 September 2026, diagnosed while S11 attempt one is running its full
regression. The retained 25EC66 dossier binds 203 implementation files. Relative
to it, the current tree has seven added qualification Python files and changes
to the shared translation CLI and RuleIR lowering. S8 attempt nine's hashed
implementation archive matches every original file exactly. The 26EC55 dossier
already binds the current 210-file inventory.

The existing finalizer calls the active-version verifier on both old and new
dossiers. Its rejection of an old version is correct, but the finalizer lacks
the intended historical/current distinction. This is a finalization harness
defect; it is not evidence that the retained UCITS reading or Java result changed.
Do not edit any bound dossier, refund a call, overwrite an archive or replace
working source with historical source to make the check pass.

The bounded repair reuses the existing independently tested historical-snapshot
verifier against the exact S8 archive. It then rebuilds and actually executes
the same retained replay input under current code in a new directory. The old
and new target, candidate/encoding coverage, bundles, finite cases and projected
results must agree. The record distinguishes historical evidence from current
finite conformance and includes the changed/added code inventory. Formal
certificates continue through their separate kernel and actual Java checker.

Skeptical audit: hashes alone are insufficient; a new runtime replay is required.
The identical source, question, unchanged readings and original finite cases
are the comparator. Changed semantics, dropped cases, a corrupt archive, changed
non-code evidence or a failed backend veto acceptance. Runtime agreement remains
finite and conditional and supplies no fresh legal judgment. No model request
is needed. Stage the helper and negative tests outside the working source while
the current regression runs; after its terminal result, record the failure,
merge the checked repair, run focused tests and a new full current-tree check.

Execution: attempt one's current-source regression passed 1,295 tests with zero
failures, errors or skips in 1,263.89 seconds. The subsequent active-version
dossier check failed with E_HASH_MISMATCH, exactly at the diagnosed old-code
boundary. The separate historical check passed against S8 attempt nine's
unchanged archive and explicitly reports current-implementation conformance as
false. Fourteen staged focused checks passed. The merged helper is now invoked
by the finalizer; it does not alter the product verifier or any old receipt.

Final execution: S11 attempt two passed after the current-tree regression of
1,303 tests in 1,252.95 seconds, with zero failures, errors or skips. The source
hashes stayed unchanged. Its actual current replay repeated 192 Java and 192
Catala cases, preserving target, bundles, cases and projected answers. Five
supported certificates were independently replayed. The phase completed its
journal, inherited scoped-result and PDF reconstructions. The final status is
ENGINEERING_VERIFIED_STUDY_INCOMPLETE; S8 and all legal/source uncertainties
remain as recorded. No extra model call was used for this repair.
