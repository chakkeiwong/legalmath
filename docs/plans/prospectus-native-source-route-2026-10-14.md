# Route all three source workers through an explicit sealed runtime

Native-binding004 closes receipt and supervised-process accounting defects. The
remaining reproduced integration gap is that source_graph.pdf_units executes
pdftotext directly and extraction.verify_hybrid_images rerenders on the host.
The sealed OCR currently reaches the product through retained output. Test an
explicit optional source-product API that selects sealed execution for all three
workers: pdftotext, fresh OCR and retained-image verification. Use a ContextVar
selection, not a global subprocess monkeypatch or an environment-only switch.
Unselected execution must keep its existing semantics. No cache reuse/default
promotion is part of this work.

Baseline: exact native-binding004 Portuguese2010 request/source/model, original
36,176 source units,29,595 clause nodes, complete questions and own-parent seals.
Use both a fresh-OCR request and the existing retained hybrid request. The
original287-file snapshot is the runtime baseline; its library/input bytes stay
bound. Extend it only with files observed by one traced native-text extraction.
Trace enumeration nominates an inventory; closed execution plus exact native
text/source/answer comparisons decide whether that inventory supports this case.
Retain original and normalized paths; refuse symlink-sensitive normalization.
No broad host-directory mounts or automatic unconfined fallback are allowed.

Primary criteria: native bbox XML/source units exact; fresh OCR source/images/
words exact; retained image verification exact; complete questions and semantic
assembly/clause fields equal across both routes; every changed parent digest
equal to its own actual product; every native child counted as sealed execution,
and the actual per-command receipt reaching the source product. An actual
changed or missing declared source/model/worker must refuse before launch.
Unit tests cover unselected behavior, unknown executable, incomplete declaration,
source/hash drift, nested selection and context restoration after failure.
All-stage current-method binding must remain fixed after implementation.

Research intent: remove unconfined optional native calls from this source path.
Counts/runtime are explanatory. The original source is exposed development data;
equal output does not establish correct reading, source authority, independent
legal truth or portability. Kernel, CPU, Bubblewrap setup and private proc/dev
remain explicit trusted inputs. Source construction still uses ordinary trusted
Python code; this is a native-worker boundary, not a hostile-code sandbox or
immutable full Python environment. Retained OCR output is hash-bound input, not
a new OCR run. Frozen assessment consumes fresh P1–P5 products.

Skeptical audit PASS: this removes real bypass sites rather than merely improving
metadata. Testing fresh and retained source paths prevents declaring integration
from one injected worker. No parent-hash equality is required across different
provenance. Old failed003 and all four admissions remain. A prototype cannot
complete native-binding without a reviewed task-specific acceptance rule and
explicit supported-source/runtime scope. No completion flags may become true.

The two intended live edits are extraction.py and source_graph.py. Keep their
exact pre-edit bytes in a baseline directory and bind those snapshots, not live
editable methods, in this admission. Preserve every other input. Freeze all
new/current methods in the attempt before execution, and retain final snapshots.
Other historical acceptance bindings may become stale; report them honestly and
perform only justified subsequent revalidation, never modify old evidence.

Default audit: source/model/version/300dpi come from the accepted comparison;
no tuning claim. Locale/thread/hash policy follows snapshot003, whose complete
English/Portuguese OCR comparisons passed. Trace library paths are a candidate,
not universal dependency closure. The smallest check is sealed pdftotext equality
before full products. Unknown file/path or incomplete inventory vetoes that
candidate and permits one diagnosed inventory/implementation repair, never a
host-mount fallback. A lost source word, changed complete answer, receipt failure,
unaccounted supervised native launch, corruption or stale admitted input stops
dependent work until the named issue is resolved within that one repair.

New supervised Popen allowance12, historical visible lower bound27. Planned
starts: one strace wrapper (its pdftotext descendant explicitly recorded, outside
Popen tally), one focused pytest wrapper (tests are in-process), two sealed native
calls in fresh source, two in retained source; at most two changed repair
launches and one final focused-test wrapper if implementation changes. Every
driver starts under the shared ledger. Record all wrapper commands separately
and retain the explicit internal descendant, so the lower-bound total includes
it even though the ledger cannot enforce tool-internal forks. No unchanged
repeat just to fill the allowance. Native children60seconds, stages120seconds,
one-second yields; snapshot512MiB/2048files, streams20MiB, trace10MiB.

Order: reviewed native-binding admission4→5; prepare the ledger, baseline and
one actual native trace; implement optional route and run focused checks; build
the explicit extended snapshot; run fresh source/construct/answer; run retained
source/construct/answer; compare full products, seals, refusal evidence and
process reservations; seal, record, refresh and inspect ready work. Result note
includes command/git/environment/CPU/seeds, actual time, source/method IDs,
decision table, strongest alternative explanation and remaining deployment scope.
No install, network call, GPU, external message or host-policy change.
