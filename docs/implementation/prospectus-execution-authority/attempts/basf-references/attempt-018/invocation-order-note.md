# Refused premature validation invocation

After consumer-closure had yielded a still-running session, the supervisor
invoked validate prematurely. The runner refused before creating a validate
stage, because consumer-closure/result.json did not yet exist. No trial stage
ran or was retried by that invocation, and frozen methods remained unchanged.
The original consumer-closure session then returned PASS. Validation was
subsequently invoked after that prerequisite receipt existed.

This is an invocation-order error, not evidence against the source mapping.
Await completion and inspect the receipt before dispatching each dependent
stage; a yielded session is not a completion receipt.
