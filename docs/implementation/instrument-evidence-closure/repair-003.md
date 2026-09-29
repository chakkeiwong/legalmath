# Development repair: missing issuer-law inventory

The preferred-share integration exposed a UBS-specific assumption in the joined
investigation: every request had to supply at least one issuer-law source.
Leaving the Swiss source attached to a US issuer would be wrong. The joined
engine now accepts an explicitly empty issuer-law list, records it as missing,
and keeps the authority calculation and overall decision qualified. Prospectus
identifiers remain required. This repairs the missing-data path without
asserting that there is no applicable law. The retained third development run
shows the rejected request; focused integration and the final affected suite
verify the repair.
