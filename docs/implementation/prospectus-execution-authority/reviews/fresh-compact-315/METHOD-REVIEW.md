# Serialization correction audit

PASS:complete freshly extractedP1equals baseline;only indented bytes exceeded
the cap. Candidate changes product serialization to compactUTF-8JSONwith
flush/fsync/replace. Original recipe,semantic content,hashes and128MiBcap remain.
Regression makes compact JSON fit while pretty JSON would fail. Preserve all
failed055bytes,costs and methods;no unchanged retry. Finish actual installed
P1-P5and full answer equality. Counts do not prove legal completeness.
