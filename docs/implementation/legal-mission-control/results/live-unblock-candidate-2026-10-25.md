# Concurrent repair result

25 October 2026. The reviewed local repair is implemented, tested and packaged while the existing live worker continues. It is **not deployed**, and P14/corpus acceptance remain open. The governing [plan](../../../plans/legal-live-unblock-candidate-2026-10-25.md) and [remaining-prerequisite analysis](live-unblock-prerequisites-2026-10-25.md) keep those distinctions explicit.

## Implemented repair

The optional `exact-context-answer-and-needs.v1` transport replaces model-retyped answer quotations with selection of an exact answer field. The decoder binds that field to the original request and reconstructs the precise text. A STILL_REQUIRED disposition preserves its exact original typed need, including query, reason, source IDs and locators. Distinct needs sharing a source remain distinct. Additional needs remain explicit.

The wire schema offers valid source IDs (including their exact existing aliases), known document hashes and route-appropriate dispositions. Missing facts/authority cannot be supplied by selecting source text. The normal validators still reject false quotations, stale bindings, foreign sources, failed-delivery waivers, unsupported numbered propositions and invalid verdicts. The default path is unchanged; the new profile is opt-in and recorded in product identity.

The patch and exact candidate files are retained at `artifacts/legal-mission-control/2026-10-25/offline-unblock/`. `candidate-manifest.json` records original and candidate hashes; `candidate.patch` passes `git apply --check` against the current worktree. Neither that check nor packaging applied the patch.

## Executed evidence

- **98 focused and adjacent regression tests pass.** The retained-failure fixture was copied exactly into the isolated tree after an initial packaging failure. Earlier outcomes and the rejected prototype remain recorded.
- **217 complete retained failed context-disposition calls** were replayed with reconstructed, hash-verified source/input records and both actual legal indexes. No citation stub, all-P14 scope assumption or suppressed delivery failure was used. Every unchanged raw response still fails.
- **194 simulated exact-reference responses validate; 23 remain rejected.** The 194 retain their original decisions: 161 UNRESOLVED, 7 REJECT and 26 already-ACCEPT proposals. These are repeated review assignments, not 194 independent legal issues or newly accepted answers. Historical results were not changed.
- **All 217 measured requests fit existing limits.** The largest final request is 108,047 bytes and 27,845 locally counted tokens, below the selected 250,000-byte/70,000-token policy. The real `BoundDispatch.measure` is used; CLI/service framing remains unmeasured.
- **Both saved P14 source indexes pass citation controls:** valid exact quotations pass; wrong paragraph attribution and fabricated quotations fail. This is narrower than complete judgment/Handbook source-use or legal-entailment qualification.
- **Zero new provider calls** were made by this repair. Existing worker progress can increase the shared ledger independently. No running source, grant, binding, result or attempt limit was edited.

The full strict replay is in `replay-all-failed-context.json`; regression is in `tests-final-compatible.xml`; capacity is in `capacity-measurements.json`; source controls are in `source-attribution-controls.json`.

## Review and limitations

The first prototype was rejected because it ignored optional invented quotations, conflated needs by shared anchors, used a personal executable fallback and replayed with citation validation disabled. Its purported 187 passing cases are not fix evidence. The replacement preserves integrity checks. A later compatibility correction keeps both exact full source IDs and their valid source-only aliases; dependency aliases remain excluded. A whole-chunk citation diagnostic was corrected to use actual indexed paragraph ranges. These intermediate failures are retained rather than erased.

The final simulation changes the response protocol: it uses a saved answer path to select exact text and retains original necessary needs deterministically. It does **not** show that a fresh model will select the right field or give a supported rationale. It also does not resolve genuine legal uncertainty. The 23 failures retain source/type/schema or assertion-binding defects. A fresh bounded live control and source-grounded review are still required before promotion.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|---|
| Accept local candidate for controlled qualification | Strict transport, replay and adverse checks pass | No weakening of legacy quotation/need validation; 23 malformed responses stay rejected | Fresh model choice and substantive support | Qualify the optional protocol after safe rebind | Live P14 recovery |
| Keep corpus BLOCKED | Current handler lacks completed applicability/source-use inputs | Missing evidence is a real promotion veto | Dated legal scope and later treatment | Complete independent evidence duties and implement their consumer | Extraction fidelity equals legal qualification |
| Keep current live worker active | Process identity and bound files unchanged | Changing live code/bindings would invalidate continuation | Gatecoin and remaining owner outcomes | Existing dispatcher drains authorized independent work | That a RUNNING reservation proves concurrency |

These are deterministic engineering controls and descriptive protocol simulations. No statistically supported model ranking, legal-accuracy estimate or default-policy promotion is claimed. The strongest alternative explanation is that deterministic field reconstruction fixes only copying, while semantic review remains wrong. A live positive/adverse qualification on the actual protocol must address that distinction.

## Continuation

The exact mission `admit` and subsequent `refresh` both completed with `ADMITTED_MASTER_WORK`; refresh reports `OPEN` and `WORK_REMAINS`. Earlier interrupted check/status attempts are not reported as passes. Independent acquisitions and tool owners remain in the ready set and belong to the existing dispatcher. Do not start a duplicate worker.

At the next verified safe worker checkpoint, require the tested candidate hashes, a reviewed same-master registration, refreshed bindings and a bounded live control before selection of this profile. P14 has used 7/7 attempts and corpus 6/6; no retry is silently added. Preserve the 8,100-call ceiling, recorded service reserve, deadline and other questions' protected allocations. Until those prerequisites hold, the repair is staged, and no claim that the live branch is unblocked is justified.
