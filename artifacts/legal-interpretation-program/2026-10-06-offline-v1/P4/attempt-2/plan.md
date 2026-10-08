# P4: Interpret precedents and justify their transfer

Status: PLANNED_NOT_EXECUTED. The [master program](../legal-interpretation-master-program.md)
controls evidence, default assumptions, resource limits and source-fidelity claims.
Dependencies: P1, P2, P3.

## Question and inputs

What exactly does a cited judgment contribute to a proposed reading, and why is it relevant to this question?

P2 disputes and P3 argument profiles; retained official source collection; HYPO/CATO/AGATHA and CLERC/eyecite findings. First identify actual candidate judgments and jurisdictional rules; do not invent a precedent or select by desired outcome.

## Implementation

1. Build a source manifest for each acquired judgment: official origin, hash, edition, court, jurisdiction, date, procedural context and opinion boundaries. Keep any unverified field explicitly unknown. Check acquisition terms independently from software licences.

2. Implement semantics/precedent.py with proposed issue/holding/factual-finding/reasoning/dictum/submission records. Each proposition has source passages and an inference warrant. A classifier output nominates a role but cannot prove that a passage is the ratio.

3. Record binding or persuasive authority only under source-backed jurisdiction and hierarchy premises, including temporal applicability and subsequent treatment. An empty search result does not establish that a case remains good law.

4. Construct source-linked factors and analogy/distinction/counterexample moves. Explain which fact difference matters under which legal proposition. Foreign cases remain conditional comparative material unless the relevance premise is supported.

5. Use eyecite only after a syntax/coverage diagnostic; support an explicit unresolved citation path for Hong Kong forms it cannot parse. Borrow CLERC retrieval concepts without merging opinions or treating original citations as exhaustive relevant authority.

6. Exercise one actual acquired judgment through the full representation if available, with no hidden legal quality labels. If suitable authority cannot be acquired, retain the failed search and missing premise; validate mechanics on explicitly synthetic legal specifications and leave the real precedent demonstration pending.

## Files and validation commands

Proposed semantics/precedent.py; official-case manifest, opinion/proposition/factor records, authority-premise map and a retained worked comparison.

The following test files are planned deliverables, not existing executed tests.
After implementing them, run these exact forms from the repository root:

```text
.venv/bin/python -m pytest tests/interpretation/semantics/test_precedent.py -q
.venv/bin/python -m pytest tests/interpretation/semantics/test_case_citations.py -q
```

Add the relevant existing regression paths discovered from actual touched imports.
Record those exact paths in the phase revision before executing; do not invent a
successful regression result or invoke a broad suite unrelated to the change.

## Discriminating challenges

Dissent used as majority; a quoted party argument becomes a finding; similar outcome masks a material distinction; an overruled or later case is used at an earlier date; no case found is reported as no contrary authority.

## Acceptance and failure decisions

The representation and argument moves preserve speaker, scope, role uncertainty and source warrants. Complete a real-case mechanical walkthrough if sources are available. A missing real authority remains a named open obligation; engineering completion cannot claim precedent-supported legal resolution.

Unclear reuse permission blocks code/data copying, not literature-based design. Missing authority permits conditional P5/P6 work with the dependency visible. Misattributed opinion roles or assumed binding force veto promotion of the affected case argument.

## Result and next-phase refresh

P5 receives the verified source identities, proposed factors/warrants, authority gaps, actual coverage limits and pending real-case demonstration. Revise any classification that relied on a missing precedent.

Save the executed plan version, input/output hashes, commands, results,
uncertainties, decision and refreshed successor plan under the immutable attempt
directory specified by the master. A planned test command is not run evidence.

Resource boundary: Prefer retained sources. Any new acquisition lists exact official URLs, maximum bytes, timeout and output directory before execution; no broad crawl, login or provider spending is implied.
