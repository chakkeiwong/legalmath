# Restore the local authoring runtime

Question: can the retained INCEpTION 38 JAR, Java 17, Chromium and Playwright
profile operate after restoration to a new path without the historical absolute
runtime paths? Comparator: the byte identities from the retained toolchain and
current installed distribution files. This is a same-host binary restoration
test, not a claim of a fresh internet install or production identity service.

Copy the complete Java/browser files and the Playwright, pyee, greenlet and
typing-extensions distributions to a configurable project-local profile with
per-file hashes and a manifest. Validate the JAR and Java binary against the
historical toolchain before snapshotting. Restore to a temporary location,
create an isolated interpreter for the Python distributions, run pip check,
start a fresh localhost-only server with random temporary administrator
credentials and guest access disabled, and log in through the restored browser.
Create and export one synthetic project through the authenticated local API.
Stop the server, delete only this run's temporary restored copy, restore again
and repeat. Reuse the historical server utility only with its output and runtime
paths redirected to the new attempt; do not execute any historical master job.

Primary criterion: both restored invocations boot, authenticate in the real
browser and export the created project, with all expected bytes verified and
server shutdown recorded. Failures in source hashes, file coverage, dependency
resolution, login or export veto this restoration claim. Credentials never enter
retained command output or evidence. The browser allows only loopback requests;
telemetry and GPU are disabled. No person is contacted and no real reading is
created. Missing resources require restoration, not an old success receipt.

Budget: 10 minutes, 2 GB persistent profile, 2 GB temporary profile plus 2 GB
server heap. CPU only. Command:
`python3 -m scripts.prospectus_closure_authoring_restore`.
Results go to the closure `authoring-restoration/attempt-NNN/` namespace.

Skeptical audit: PASS for restoration. Authentication uses ordinary password
login; synthetic accounts do not establish real identity or independence.
Project export demonstrates the live server consumer; it does not repeat the
historical authoring study or validate the new cross-document review UI.
Record system-library dependence explicitly. A loopback sandbox restriction
is an execution-environment issue, requiring the same bounded trusted command,
and is not evidence that INCEpTION or Chromium is defective.
