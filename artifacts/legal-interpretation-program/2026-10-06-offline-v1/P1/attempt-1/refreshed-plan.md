# P1 refreshed from P0

Use packet.json, baseline.json and overlay.json from artifacts/legal-interpretation-program/2026-10-06-offline-v1/P0/attempt-1. There are 54 retained source units, 35 reading identities in two roles and 46 open obligations.

Packet is historical units-only data, not the strict Packet schema. Add a lossless legacy envelope; do not pretend it already contains edition/actor/speaker metadata. Keep supplied source qualifications and raw circular identity. Distinguish source integrity, proposed meaning, applicability, factual support and formal results. Use strict immutable records with tuples, forbid truth coercion of four-state evidence, preserve partial dates without year imputation, and bind semantic branch assumptions/settings independently of a legacy Reading.

Audit passed: no source truth inferred from verified quotes; unknown actor/time/role remain unresolved. Tests: approved phase-tests P1 and regression contracts. Stop on lossy roundtrip or source identity mismatch; unsupported meaning permits conditional development.
