# Senior bank prospectuses: UK, EU and Australia

Three issue examples are preserved with their matching programme documents.
The eight applicable PDFs contain 755 pages. A ninth PDF (three pages) is
retained as a rejected ASB/CBA issuer mismatch. Original bytes, source URLs,
dates, page text and SHA-256 hashes are in [manifest.json](manifest.json) and
[sources.json](sources.json). These documents are development examples.

| Issue | Final terms | Matching documents | Assessment under the working feature definition |
| --- | --- | --- | --- |
| UK: NatWest Markets plc, Series 14, USD750m 4.789%, issued 21 March 2025, due 21 March 2028; USG6382RGD47 (Reg S), US63906YAM03 (144A) | [18 March 2025](originals/nwm-2025-final.pdf) | [17 March base prospectus](originals/nwm-2025-base.pdf); [registration document](originals/nwm-2025-registration.pdf) | **loss absorption**: Condition 7, PDF p.69 / printed p.66, expressly permits UK bail-in reductions or cancellation of principal. |
| EU/France: BPCE S.A., Series 2025-23, USD54m SOFR + 1.03%, issued 19 December 2025, due December 2030; FR0014014YQ1 | [17 December 2025](originals/bpce-2025-23-final.pdf) | [14 November base prospectus](originals/bpce-2025-base.pdf) | **loss absorption**: Condition 17, p.150, covers permanent reduction of amounts due, defined to include principal; p.167 expressly includes senior preferred debt. |
| Australia: Commonwealth Bank of Australia, Series 6700, EUR255m €STR + 0.26%, issued 15 October 2025, due October 2026; XS3206613666 | [13 October 2025](originals/cba-2025-6700-final.pdf) | [1 July programme circular](originals/cba-2025-base.pdf); [13 August CBA EMTN supplement](originals/cba-2025-emtn-supplement.pdf) | **non loss absorption**, qualified: the inspected senior terms specify cash repayment without an identified CoCo or statutory principal-loss mechanism. Ordinary creditor-approved restructuring is treated separately. |

The dedicated binary classifier now returns these same three qualified
outcomes, with generated reasons in the
[executed report](../../implementation/bond-loss-absorption-classification/results.md).
The earlier reader returned `UNDETERMINED` in its different complex-bond test. See the
[diagnostic and reasoning](../../implementation/bond-loss-absorption-classification/bank-senior-study/result.md).

The feature definition includes an explicit, issue-applicable statutory
principal write-down disclosed in the prospectus, as well as contractual CoCo
mechanisms. Seniority alone does not determine the label. This definition must
not be substituted for a regulatory product-scope or trading-eligibility test.

CBA Condition 13 (pp.137–138) permits collective creditor decisions to reduce
repayment, binding dissenting holders. The working definition records ordinary
creditor-approved restructuring separately from contractual capital triggers
and statutory bail-in. If the intended definition includes every such
principal reduction, the CBA row becomes positive too. This boundary has been
raised with the user; no confirmation is assumed. The CBA negative remains a
qualified assessment of the inspected terms, not a proof of absence throughout
all incorporated documents or subsequent amendments. The archive does not
contain every referenced financial statement, agency agreement or deed.

The file [cba-2025-supplement.pdf](originals/cba-2025-supplement.pdf) was retrieved
as a candidate supplement but its cover limits it to **ASB Bank Limited, New
Zealand**. Its original acquisition filename is retained; `sources.json`
explicitly rejects it for the CBA case. The matching date and combined USD70bn
programme limit do not establish issuer identity. The correct CBA supplement is
the separately named `cba-2025-emtn-supplement.pdf` above.

The NatWest base request initially returned HTTP 500; a second request succeeded.
Both HTTP header records are retained in `acquisition/`. No error response was
accepted as a prospectus.
