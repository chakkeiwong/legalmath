# Failed result disposition

The authority correctly retained007 as REJECT because result.json says FAIL:
`Worker result failed or belongs to another task`. Its output hashes remain
valid. The first252 proposal preflight assumed a RECORD event and therefore
stopped before writing a route/proposal or consuming an admission. This is a
proposal-script assumption error, not another execution or source failure.

Keep the preflight and freeze unchanged. The separately bound revise-rejected.py
checks byte equality to the frozen generator and changes exactly its required
event from RECORD to REJECT. All substantive controls, costs, inputs, method
freezes, budget history, build contract and review fields remain unchanged.
No production/runner/test repair or validation rerun occurs in this preflight.

Skeptical audit: PASS. A valid failed output is evidence for reviewed repair;
REJECT must not be mistaken for missing/corrupt evidence. The original output
manifest and event hash are still checked before proposing continuation.
