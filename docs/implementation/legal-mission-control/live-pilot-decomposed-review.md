# Review of the existing piece-inventory continuation

10 October 2026. PASS for the one bounded attempt in
`docs/plans/legal-mission-live-pilot-decomposed.md`. This is executor review.
The existing product implementation is unchanged. Only the closed runner profile
selects five source pieces and equal remaining core effort.

Local qualification preserved all 55 source units in original order and exact
bytes. Both reader roles receive every piece and the same source qualification.
The ten initial encoded requests range from 44,522 to 68,146 bytes, compared with
the timed-out whole-packet request's 128,525 bytes. Encoding round trips are exact.
The existing full-source cross-piece checks remain mandatory and their eventual
sizes remain unmeasured until the actual inventories exist. No response has been
normalized or supplied by the executor.

The pilot and mission suites passed 65 tests in 3.69 seconds, including the new
equal-remaining-effort and actual qualified-piece controls. The earlier source
context, exact-reference and codec suites also passed; their product code has not
changed. `git diff --check` passed. These are engineering checks, not legal results.

The shared allowance is still 5/400. The new baseline and candidate each have 31
core calls; five candidate slots are withheld. All original stage ceilings and
the absolute deadline remain. The ordinary one-detour bound is unchanged, with
this reviewed enabling exception explicitly counted as the sixth detour. It is
not repeatable under another name. A failed trial returns an unavailable
comparison and its evidence; a fourth live configuration is not automatic.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Not concluded |
|---|---|---|---|---|---|
| Run one decomposed baseline and conditional matched candidate | Original complete legal answers pending | Source, grant and equal-effort controls pass locally | Per-call latency, cross-piece fidelity and downstream capacity | Freeze, dispatch and inspect actual result | Legal correctness or that smaller requests cure the timeout |

| Inference status | Evidence |
|---|---|
| Hard veto screen | Prior literal validation failures and whole-packet timeout remain retained. |
| Statistically supported ranking | None. |
| Descriptive-only differences | Smaller measured request sizes; no response-time attribution. |
| Default readiness | Not established. |
| Next evidence | Complete piece inventories, both cross-checks, generated legal readings and complete answers. |

The strongest alternative explanation remains transient service latency; a
smaller successful call would not establish a general size-performance relation.
The important legal risk is losing P10/footnote/Appendix qualifications across
pieces. The full-source cross-check and final source review, not unit counts,
must address it. No tool receives promotion from this enabling work.
