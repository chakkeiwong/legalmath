# BES legacy-audit language transfer check, 12 October 2026

The first four-page bilingual diagnostic recovered three source-language/code
spans without losing a previously matched span. Before nominating the profile
for wider product use, test it on the **other six** previously selected audit
pages. These pages and their 18-span image-reviewed oracle already existed
before the four-page language comparison. They are a separate known-case check,
not a blinded holdout or a sample of all prospectuses.

The question is whether `eng+por` and `por+eng` preserve the English baseline's
15/18 matching spans and recover any of its three accent failures on 2008 PDF
245–248 and 2009 PDF 174–175. Exact comparator: the frozen retained English
worker outputs and `hybrid-review-001/oracle-v2.json`. The primary local screen
is no loss among the 15, at least one accent gain, exact source/page/image/model
bindings, unchanged native units and successful actual `service.source_product`.
Compare raw and source-product text separately. Counts are descriptive only.

An English baseline that fails exact worker reproduction, source/image drift,
invalid native comparison or missing model is a continuation veto. Failure of a
bilingual candidate's local screen rejects only that candidate; still run the
other predeclared language order. The test cannot show whole-document coverage,
legal answer preservation, an optimal/default model, independent authenticity,
native confinement or statistical superiority. Any profile that changes old
raw units needs a new source graph and review packet before it could enter the
eleven-document consumer; do not silently replace retained OCR evidence.

Defaults are inherited as comparator settings: existing 300 dpi CPU worker,
English model SHA `7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2`,
official Portuguese fast model SHA
`c4932b937207a9514b7514d518b931a99938c02a28a5a5a553f8599ed58b7deb`,
and Unicode NFC plus whitespace folding. The `por` bytes and official retrieval
receipt are already retained in `language-profile/acquisition-001/`. Model
order is a hypothesis, not a default. Accent- or punctuation-insensitive
matching would hide precisely the failure under test, so it is prohibited.

Skeptical audit: the comparator is a real earlier product page family with a
frozen oracle, not the four pages used to nominate bilingual OCR. It is still
assisted and limited to audit reports. The command's source-product units and
image checks answer the transfer question; it cannot answer legal acceptance.
Stopping after an ineligible first candidate would confuse candidate veto with
research continuation. Audit verdict: PASS for one bounded three-arm diagnostic.

Run from the prospectus worktree with CPU hidden:

```text
timeout 600 .venv/bin/python docs/implementation/prospectus-integration-closure/bes-original-acquisition/compare_legacy_audit_profiles.py
```

Retain starts, exact command/environment, baseline commit, dirty method hashes,
source/model/oracle identities, all three worker outputs, product summaries,
per-span gains/losses, runtime, manifests, and phase-by-phase next reason in
`language-profile/legacy-audit-001/`. Do not change current product defaults.
After results, review all six pages and refresh the next programme based on
whether the bilingual profile is viable only on known cases or fails this
additional family. The result should explicitly distinguish our configuration
choice from a fundamental package defect.
