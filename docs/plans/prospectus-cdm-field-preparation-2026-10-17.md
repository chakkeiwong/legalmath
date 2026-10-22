# Prepare the pinned FINOS bond fixture for a later receiver trial

This local preparation uses the official FINOS CDM bond-execution input already
retained from commit `65996cfa8defcd1f15eb457f9d2c50295b3e9691`. The active
continuation route authorizes source-field and semantic-loss preparation before
the receiver is named. This does not select a receiver, execute CDM, validate a
round trip, or close either CDM task.

## Question and evidence contract

Can the retained fixture's security, cash amount, settlement date, party roles,
and source claims be made explicit enough to compare later against an actual
named receiver? The comparator is the pinned input JSON plus its matching
official markdown description and settlement model source. The primary criterion
is exact source integrity and internally consistent extraction of the fixture's
stated arithmetic and role references. Changed critical fields or broken party
references must fail local fixture checks.

Explanatory findings include absent fields, role mismatches, unit ambiguity, and
differences between prose and serialized input. They do not establish an error
in the CDM model or Python implementation. The later interoperability criterion
remains bidirectional identity through the user's named receiver and version,
with receiver-specific validation, functions and downstream semantics.

## Assumption audit and pre-mortem

| Choice | Provenance and purpose | Failure mode and early check | Status |
|---|---|---|---|
| Use the existing official fixture | Pinned FINOS tree receipt and matching example prose | A fixture can be mistaken for an authentic transaction; retain demonstration and dummy-party labels | Preparation baseline only |
| Treat 20,000,000 GBP as quantity and price 1.022 GBP/GBP | Exact retained JSON fields and description | Numerical multiplication may hide a unit-model mismatch; preserve units and flag actual asset/quantity interpretation for receiver review | Source-derived arithmetic, CDM interpretation unresolved |
| Map Party1/Mega Bank to buyer and Party2/Global Bank to seller | Counterparty references joined to retained names and prose | Cash and security payer directions can be conflated; record each leg direction separately and require actual transferable-product output | Source-level role mapping only |
| Treat settlement-centre values as roles | Serialized input and same-commit settlement definition | Mistaking role enum values for Euroclear; preserve that prose names Euroclear while input carries generic roles | Confirmed source difference, no chosen fix |
| Use retained README/POM for runtime prerequisites | Pinned official source receipts | Java and Python capabilities can be conflated; preserve Python and Java requirements separately and do not install | Source boundary only |

The run could appear to pass while only repeating its own hard-coded fixture
expectations; therefore every derived value is tied to hashes and JSON paths,
and no control is described as an official package execution. It could appear to
fail because the demo intentionally uses currency units for a bond quantity or
generic settlement-centre roles; these remain mapping questions until the
receiver profile and native functions are known.

## Ordered local work and limits

1. Admit the first of the existing two `cdm-roundtrip` admissions solely for this
   source preparation. During this bounded admission, `depends_on` is empty and
   `actual_exchange_depends_on` retains `cdm-profile`. The external profile task,
   original acceptance and all budgets are unchanged. The source-only worker
   has no exchange operation and requires the profile to remain unprovided.
2. Verify hashes against retained receipts for the official example input,
   example description, settlement model, Python README and source POM.
3. Extract security, price, quantity, settlement, party and identifier fields
   without changing the fixture; calculate dirty, clean and accrued amounts
   using exact decimal arithmetic.
4. Retain a source-field map, semantic-loss checklist, integrity controls and
   machine-readable result. Label every unanswered receiver-specific claim.
5. Record the partial result, refresh, and restore the normal `depends_on:
   [cdm-profile]` through the next reviewed revision. This restoration is required
   before handoff. Keep the spent preparation admission visible; it leaves one
   of the original two admissions available after the real profile is accepted.

The single preparer is bounded to 30 seconds and 5 MiB new evidence. It uses only
the local Python standard library and retained files. No network, package
installation, CDM import, Java process, native function, model, GPU, external
message or production edit is allowed. The input is not modified. The existing
public-source request cap is not extended.

Protect all441production files against the revision181 baseline. Count the new
admission and evidence against the same task; no renamed task or fresh budget is
created. The historical600second focused-command and200MB evidence upper bounds
remain. The command is `timeout 40 .venv/bin/python -m
scripts.prospectus_cdm_source_prep`, with one-second tool yield and polling to
actual exit. Stop on source/method drift, a missed required control, an unexpected
runtime/subprocess/network action or exceeded bounds. A failure needs a reviewed
repair and consumes its attempt; no unchanged rerun is authorized.

## Skeptical audit: PASS

This work answers the locally actionable source-mapping portion of the reviewed
route. It does not claim to answer integration. In particular, the prose says
Euroclear while the serialized settlement-centre fields are generic roles; the
cash payout is Party1-to-Party2 while the prose describes the transferable bond
as Party2 payer; and the security quantity is denominated in GBP. Those may be
intentional model choices, but silently treating them as interchangeable would
make a round-trip comparison meaningless. Preserve these as receiver questions.
The same-commit settlement definition requires `settlementType (1..1)`, while the
function-input fixture omits it. Preserve that discrepancy; the function output
and validation semantics are untested. The POM enforces build JDK21 while its
parent compiler target is11 and may be overridden in a child; neither determines
the user's actual runtime. The raw quantity times price arithmetic is exact, but is not by itself evidence
that an exchange understands the bond quantity, cash amount, or both DvP legs.
