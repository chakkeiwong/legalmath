# Keep the admitted finite evaluator's limit explicit

Pre-execution code review found that predicates.dispatch returns UNKNOWN with
DOMAIN_LIMIT above12 distinct facts. P4 applies this limit both within bases and
to the aggregate basis statuses. Fifteen independent bases would therefore not
answer the proposed question under the inherited finite default. No run was
started on that mistaken design.

Use exactly12 necessary-condition families, each with at most11 named facts:
scope/regime, contractual authorization, permitted subject, equal treatment,
statutory majority, contractual majority, eligible votes, first-meeting quorum,
meeting procedure, publication, execution permission, and deed implementation.
Meeting procedure lists11 separate hypotheses; it is not one valid_resolution
bit. Because that family spans several provisions, its authority anchor spans
the exact contiguous statutory sections9–16 and its descriptor names the
individual provision for every hypothesis. Scope uses the full retained statute
as its anchor because sections1,19 and24 are noncontiguous; exact supporting
sections remain in the descriptor. That broad source anchor does not prove the
executor's interpretation. The original text is retained in full.

Statutory and contractual majorities remain separate bases. The deliberately
adverse measure9 scenario supplies nonessential=True and subject1to8=False,
simple_majority=True, qualified_majority=False. The contractual formula alone
allows that combination; the statutory subject1to9 rule rejects it. This tests
the conjunction under supplied source classifications, not whether such a
measure can legally be nonessential or what law applied in2022.

Review PASS after this correction: no new engine/default, concealed domain-limit
failure, composite validity assumption, or claim of complete legal efficacy.
