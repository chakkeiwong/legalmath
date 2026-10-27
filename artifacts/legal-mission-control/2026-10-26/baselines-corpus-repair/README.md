# Current repair entrypoint

The current local candidate is **candidate-hardened/**, identified by
**latest-candidate.json** and **candidate-hardened-manifest.json**. It is
implemented and tested in isolation, **NOT DEPLOYED**.

- Read final-result.md and attribution-review-addendum.md for the final findings.
- Use candidate-hardened.patch only after checking all recorded live hashes and
  reaching a verified safe implementation-owner checkpoint. It is consolidated;
  do not apply any older patch first.
- candidate/ and candidate.patch are the retained first candidate. Its corpus
  attribution gap was reproduced and corrected in the hardened candidate. They
  remain evidence and must not be selected for activation.
- tests-attribution-qualified.xml records 130 passing tests.
  corpus-attribution-hardened.json records 965 real passage identity checks and
  rejected unqualified legacy rows. These do not constitute legal acceptance.
- p14-target-location-audit.json refines the preliminary semantic diagnosis:
  the network-absence statement occurs in /unresolved/2, while several warrants
  incorrectly select /conclusion. All original legal decisions remain intact.
- mission-checkpoint-hardened.json records the final same-master event.
  mission-refresh-hardened-command.json and mission-refresh-hardened.json record
  its validator outcome once that command finishes; their absence is not a pass.
- activation-prerequisites.json is a dated resource snapshot. Re-read current
  ledgers at deployment. No attempt, service reserve or deadline is reset.

The original master still governs independent execution. Do not restart or
replace a live owner based only on stale files or sandbox process invisibility.
The local candidate closes reproduced engineering defects; P14 target review,
corpus applicability/later treatment, complete source-use review and fresh live
qualification remain outstanding.
