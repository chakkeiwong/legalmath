# Evidence branch: final four-group capacity diagnostic

This read-only diagnostic is independent of live P10. It makes no model call,
does not consume an owner attempt, and does not change bound code or the master.

Question: why did the evidence branch stop after four successful reduction
levels? The exact comparator is its saved `reduction-evidence-3.json`: four
groups, 265156 bytes in the retained decoded JSON representation. Every one of
the 86 original accounts validates; reduction populations were 107, 19, 7, 4.
The returned failure is `Synthesis cannot contract without losing support`.

The diagnostic reconstructs the actual request builder, source selection, exact
downstream encoding and provider input measurement for each singleton and every
pair of the four retained groups. It compares their fit against the registered
32768-token downstream limit and 200000-byte limit. These are transport capacity
diagnostics, not legal acceptance or evidence that a proposed compression is
semantically safe. No token or byte limit is changed.

Skeptical audit: PASS for debugging only. Aggregate decoded group size alone
cannot identify the binding limit because production request encoding and full
source attachment matter. Every pair must be measured through that exact code
path. A pair fitting would refute the simple all-pairs-over-capacity explanation
and require checking greedy packing/order. If no pair fits, retained wire sizes
identify the immediate bound; they do not prove inherent impossibility or
justify discarding citations. Source/recovery fidelity and unchanged live ledger
are mandatory checks. The JSON report preserves measurements and this note.
