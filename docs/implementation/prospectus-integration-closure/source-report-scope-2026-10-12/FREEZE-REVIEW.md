# Source review correction before implementation

`freeze-001` retains four matched readings and exact quotations. Review found a
semantic ambiguity in the field label: the 2009 statutory report calls itself
a free translation but does not say which version prevails. That quotation
cannot establish translation priority. Preserve this freeze and create
`freeze-002` with separate translation-status and translation-priority fields;
the latter is UNKNOWN for the statutory opinion. The English sustainability
report expressly states Portuguese priority and supports both fields. No such
statement is invented in the Portuguese original.

Also clarify the incomplete-review control: omitting a required field is an
invalid contract; explicitly marking it UNKNOWN is valid incomplete evidence.
The consumer must withhold a complete scope finding when essential subject,
conclusion or assurance/reliance qualifications are unknown. This avoids
forcing invented facts to make an admission pass. A syntactically consistent
but substantively false reviewer classification is not automatically detected
by source hashes; the frozen matched cases test our classification, while
independent adjudication remains outstanding.

Revised command: `.venv/bin/python -m scripts.prospectus_report_scope freeze --freeze-id freeze-002`.
The first freeze is not an independent baseline, and is not overwritten.
