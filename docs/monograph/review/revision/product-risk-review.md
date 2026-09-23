# Product design and legal-use assessment

**Not ready for autonomous legal/compliance decisions or bank production.**
The reviewed baseline is the accepted E01–E09 scripted increment. Later
concurrent search work is separately identified and is not promoted by this
audit. The code supports useful local invariants but does not establish source
completeness, legal accuracy, employee authority or a production operating model.

| Gap / severity | Inspected evidence | Consequence | Repair and acceptance evidence |
|---|---|---|---|
| Legal authority and source completeness / critical | Real 23EC46 candidate retains five legal issues and two Code/FAQ dependencies; E01–E09 reports | Compilable output may omit a controlling rule | Independently approved source perimeter and interpretation; unresolved material units block release |
| No measured legal interpretation performance / critical | Scripted provider and supplied repair in retained acceptance | 205 tests do not estimate legal error rate | Blind, adjudicated unseen packets; severity-specific errors, disagreement and uncertainty; no default promotion from a pilot |
| Institution and activity scope / critical | Applicability record in `review/lifecycle.py:91`; reviewed SFC/HKMA circular scopes | A valid requirement can be applied to the wrong entity/use | Named entity, activity, product, clients, jurisdiction and effective time; legal-owner approval |
| Identity and revocation / critical | `review/lifecycle.py:14` stores local role/token hashes; changed registration is rejected | Local caller strings do not establish current delegated employee authority | Enterprise identity, MFA as required, role lifecycle/revocation and separation of duties; test departed/revoked reviewers |
| Case/entity confidentiality / critical | `api/app.py` authenticates callers; generic reads are not a tenant authorization model | A valid user can lack authority over a particular client's material | Case/entity-level authorization throughout linked reads, exports and retrieval; negative cross-entity tests |
| Privileged history rewriting / high | `storage/database.py:64` chains hashes within the same locally administered store | Rewriting both records and expected chain can evade internal consistency checks | Independently controlled checkpoints/retention, key custody and recovery; privileged-rewrite exercise |
| Host concurrency and stale releases / critical | `review/releases.py:114` selects historical/current releases; synthetic host tests | Offline packages may continue after retirement; concurrent trades can breach cumulative limits | Production atomic exposure reservation and release check, defined revocation delivery/cache age, concurrency/failure tests |
| Unresolved-case operating model / high | Bounded controller can halt; no demonstrated bank queue ownership/SLA | Abstention may become ignored work rather than a safe decision | Owner, evidence request, interim restriction, deadline, escalation and expiring override; queue-failure drill |
| Client data and provider boundary / critical | Public-source scripted increment; no bank provider/data integration acceptance | Sensitive information or source instructions could acquire unintended access | Approved data flows, retention/deletion/privilege, provider contracts, parser isolation and restricted model capabilities; malicious-source tests |
| Incident response and amendment effect / high | Hash/version history and local replay are useful but incomplete operational evidence | Wrong decisions may persist after an error is found | Suspension authority, affected-decision reconstruction, client remediation and legal notification assessment; rehearsed missing-exception/stale-release scenarios |

The focused security, release-binding and host-transaction test execution passed
18 cases. That supports only those tested paths. It is neither penetration
testing nor independent validation of a bank system. Regulatory penalties cannot
be estimated from these test results; actual duties and breach facts would govern.

| Decision | Primary criterion status | Veto diagnostic status | Main uncertainty | Next justified action | Not concluded |
|---|---|---|---|---|---|
| Retain as a bounded research/engineering workbench | Local scripted invariants have test evidence | Production and legal reliance blocked by the gaps above | Independent interpretation accuracy and operating controls | Legal-owner review, production threat model, identity/host integration and adjudicated shadow study | No regulatory approval, production safety, or quantified legal error rate |

The strongest alternative explanation for the apparent assurance is that exact
hashes preserve an exactly wrong interpretation. A material legally adjudicated
counterexample would refute that interpretation even if every generated program
agreed. The weakest current evidence is the link from public-source scripted
cases to an institution's real decisions. These are product promotion vetoes;
they do not invalidate the document work or justify abandoning the proposed
repairs.
