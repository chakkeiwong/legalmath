# Entitlement consumer result

The admitted entitlement task ran through the real P1-to-P5 consumer path. Two retained Shell cases stayed `CONDITIONAL` with the pre-change amounts (`31215847/5` for the global hypothetical and `1249` for the definitive hypothetical), the same dates, events, source evidence, and other question results. The new explanation retains every declared holding and lists excluded accounts.

Ten controls passed: all accounts unentitled, two accounts for one holder, distinct holders, record/ex-coupon inputs with both entitlement flags, missing and unknown flags, duplicate accounts, negative principal, a missing required record event, and payment-before-determination chronology. Invalid premises are returned as typed `UNSUPPORTED`; no legal entitlement, clearing transfer, note form, or settlement is inferred.

The first two bounded attempts exposed harness assumptions about exact rational formatting and refusal wording. `partial-failure.json` preserves those failures and the repairs. `validate_entitlement.py` is the task-specific validator.

This task remains partial under the authority acceptance rule. Independent legal/form review and actual client entitlement, clearing, and settlement records remain open. The evidence supports a reporting repair and conditional accounting behavior; it does not establish a real holder's legal right to payment.
