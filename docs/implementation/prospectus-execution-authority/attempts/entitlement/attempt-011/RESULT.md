# Source-bound registration rounding through the financial consumers

Revision255 admitted this continuation of entitlement, retaining obligations
G14, G15, E03 and RESIDUAL-04 and every earlier attempt. The unchanged253
production repair passes the reviewed finite source/consumer checks. This is
partial conditional evidence; the original entitlement task and general build
remain incomplete.

## Actual execution and evidence

The three commands ran once, sequentially, from the prospectus worktree:

```text
.venv/bin/python scripts/prospectus_registration_baseline.py tests
.venv/bin/python scripts/prospectus_registration_baseline.py bbva
.venv/bin/python scripts/prospectus_registration_baseline.py seb
```

The test report retains432 tests, zero failures, errors or skips. Each issuer
retains nine valid registration controls,25 adverse controls and two detected
pre-repair wrong functions. All five original products reconstructed exactly;
the complete original Q5 and three other question values were preserved for
each issuer. Changed scenarios preserved the other complete question values.
Valid and adverse answers are retained losslessly as shared-answer-questions.v1;
the wrapper checked exact reconstruction before writing them.

The valid controls cover both directions of holder/registration disagreement,
input reordering, splitting an amount within a registration, exact and near
integer boundaries, a large exact amount and multiple registrations. For each
issuer the adverse controls comprise four ambiguous legacy inputs across active
and inactive conversion paths,18 malformed explicit mappings across those paths,
one genuine excluded-source product, and content/parent tampering. Refusals do
not confer transaction authority. No additional extraction or native PDF call
was made: the source campaign remains at six calls. Retained008 P1 evidence was
reused, never described as fresh extraction.

## Source rule, calculation and attribution

BBVA original PDF129 Condition6.11 and SEB original PDF43–44 Condition5A.10
condition aggregation on Delivery Notices for shares to be registered in the
same name. Their original identities and full retained excerpts remain bound
under registration-groups-253. The SEB clause separately discusses Selling Agent
aggregation; this package does not calculate that allocation.

For a supplied registration partition g, sum its exact positive amounts A_g
before rounding. At the reviewed supplied conversion price3, put all decimal
amounts over a common integer denominator d and write A_g=n/d. Independent
integer division gives n=3d*q+r, with0<=r<3d. The conditional whole shares are q
and the uncompensated fractional share is r/(3d). This independent checker uses
Decimal-to-integer ratios and quotient/remainder, without production grouping
or Fraction arithmetic. At amounts5+5, separate registrations receive1+1
shares; one registration receives3. The old holder grouping produces the wrong
answer in both directions. The retained wrong functions still demonstrate those
defects through both issuer controls.

The production defect was our input model/source interpretation: legal-holder
identity had replaced the source's registration partition. The corrected model
requires a supplied explicit partition when holder and exact registration-name
partitions do not coincide. It preserves exact names and refuses inconsistent,
mixed or incomplete groups, including on inactive primary paths. Beneficial
allocation remains NOT_ESTABLISHED.

The009 storage refusal was our preflight error, before substantive tests ran.
The010 regression failure was our source-incorrect test baseline: it demanded
separate holder rounding for ambiguous same-name input. Its failed report and
original test survive unchanged. Revision255 changed only that live test to
require legacy refusal, conditional explicit aggregation and preservation of the
valid coincident legacy case. Production and primary validators were unchanged.
These failures provide no evidence of a fundamental third-party package defect.

## Decision and limits

| Decision | Primary criterion | Veto diagnostics | Main uncertainty | Next justified action | Not concluded |
| --- | --- | --- | --- | --- | --- |
| Retain conditional registration repair | All18 source-bound P5/P6 controls equal independent arithmetic | Both issuers refuse declared adverse inputs; original complete values preserved; four wrong controls detected | Supplied partition and delivery-notice premise are not observed facts | Seal, record and refresh; review the next substantive route | Whole entitlement or general-build completion |
| Preserve scope restrictions | Conditional and actual-event limits survive the normal consumers | No beneficial allocation, settlement support or execution authority inferred | Unmodelled clauses, delivery and actual ownership | Continue source-to-answer coverage with explicit unsupported conditions | Actual shares received, payment, settlement or economic recovery |

Stage times were3.848136s for tests,41.556428s for BBVA and22.250320s for SEB.
Cumulative measured campaign time before sealing is181.610604s, including prior
retained work and255 preparation, below480s. The sealing manifest records final
measured time and storage against the reviewed160MiB cumulative allowance; the
original80MiB violation remains visible. Historical unmeasured time is UNKNOWN.
Counts and runtime explain the check, not legal completeness. This deterministic
validation establishes no stochastic ranking or package superiority.

The strongest alternative explanation is that a supplied registration partition
or notice condition does not match the actual transaction. Agreement at supplied
price3 cannot establish a different adjusted price, denomination, market-price
window, FX rate or legally effective notice. An authenticated source clause
requiring different grouping, a valid in-domain counterexample, or a consumer
that accepts one of these malformed mappings would overturn the corresponding
claim. The weakest evidence remains completeness of the interpreted source
domain, rather than the checked integer arithmetic.

Open work includes actual notices/ownership, Selling Agent allocation,
settlement/delivery, denominations, adjusted prices, supplied SEB market price
and FX, dates, broader contract/law, and native geometry/confinement. Zero
converted principal does not imply zero economic recovery. Actual holdings and
reader acceptance follow the general build; external-adviser opinions are not
its correctness prerequisite. Receiver-specific CDM and portability remain
deferred. A PASS here cannot substitute for those source and coverage duties.
