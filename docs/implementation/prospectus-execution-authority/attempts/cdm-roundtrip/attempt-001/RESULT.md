# CDM bond fixture preparation

The pinned FINOS function-input example now has a complete JSON field inventory,
five resolved local references, a source-bound semantic map and fifteen actual
fixture-integrity controls. The controls include changing clean and accrued
components while preserving the dirty total. These are checks of our retained
fixture comparison, not observations from a CDM runtime or receiving system.

The arithmetic is exact: GBP20,000,000 nominal times1.022 gives GBP20,440,000;
the1.02 clean component gives GBP20,400,000 and the0.002 accrued component gives
GBP40,000. The input's payout is Party1/Mega Bank to Party2/Global Bank, with
2020-09-24 settlement. The description names Global Bank as seller and Mega Bank
Inc as buyer. Whether the generating function produces the expected cash and
opposite security legs remains untested.

The prose names Euroclear, a Treasury issuer and issuer LEI; those identities are
absent from this JSON. Its centre fields name generic roles. Its bond quantity
uses GBP rather than an instrument-unit field. The same-commit SettlementBase
definition requires settlementType, but the function-input fixture omits it.
These are concrete mapping and validation questions. Do not silently insert
defaults or conclude that the model is defective: the actual generating function,
official output, receiver profile and runtime conditions have not been exercised.
The party identifiers use the explicitly dummy identifier scheme.

The source POM enforces build JDK21 and separately declares parent compiler target11,
with an override comment. This is not proof of the user's runtime compatibility.
The Python README requires3.11+, explicit model/condition validation, and native
replacements for any required Java stubs such as LoadCodeList. No runtime was
installed or invoked. All441 production files remain identical.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Limit |
|---|---|---|---|---|---|
| Retain source preparation | Pinned source identities, exact amounts and15 controls pass | No corrupt source, lost field or production drift | Fixture assumptions and source/prose differences | Use the retained field map when the receiver is identified | No CDM conformance or package verdict |
| Keep actual exchange gated | No receiver exchange exists | Named profile/runtime/native functions absent | Actual generated legs, conditions and receiver behavior | Restore cdm-profile dependency, then review genuine supplied profile | Task and program remain incomplete |

Post-run review: an intended function may supply omitted values or interpret GBP
as bond nominal, and the prose may lag the fixture model. Exact matching official
function/output code and receiver validation would distinguish those explanations.
The weakest evidence is the absent real runtime result. This packet consumes the
first original CDM admission and leaves the second under the original allowance;
it does not reset public-source calls or permit an unchanged rerun.
