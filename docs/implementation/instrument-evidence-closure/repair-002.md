# Development repair: literal anchor and Lean environment

The second focused test run passed 25 checks but rejected two dossier uses:
one purported quotation said “shares” where the retained sentence says
“series”. Corrected the literal anchor after re-reading page 16; no source or
expected financial result was changed.

Lean checked four propositions and rejected the fifth because `by_contra` is
not supplied by this project's `Std`-only environment. Replaced that tactic
with constructive case splits and integer arithmetic. The acceptance checker
must reject `sorryAx`; a printed theorem name is not enough. The initial
failure is preserved by this note and the development diagnostic output.
