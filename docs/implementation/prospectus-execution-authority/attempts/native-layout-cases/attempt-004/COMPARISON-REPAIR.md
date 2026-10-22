# Preserve the failed comparison and inspect nested outcomes

The first comparison removed only the outer unresolved list before checking
Q2. Q2 also contains subquestions, each with its own occurrence-bound unresolved
list. Their clause identifiers legitimately change when new selected native
lines alter the clause enumeration. The original comparison method and failure
remain in invocations/compare; no products or extraction were rerun.

The reviewed comparison recursively compares all question fields for Q1, Q2
and Q3. It permits differences only in lists named unresolved, retaining every
one of those lists and its exact path in complete-answer-differences.json.
Statuses, values, witnesses, qualifiers and subquestion structure must remain
equal; Q4 through Q6 remain completely equal. Full answers and graph/assembly
differences remain retained. This fixes an incomplete comparison, not the
product or an unfavorable candidate result, and consumes the one allowed local
repair. No further repair or native start is authorized by this package.
