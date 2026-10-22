# Native input observation result

The actual OCR worker and source consumer now retain mapped native file hashes
and a named set of hashed environment values. On the retained two-page synthetic
scan, all page images, text, word geometry, source units and downstream question
results equal the protected baseline. The source graph includes 39 mapped files.
The trace run returns identical page output and records 281 regular file inputs
and 438 absent paths. All absent paths remained absent at the post-run check.

Six controls detect changed content, deletion, same-content symlink retargeting,
a formerly absent path becoming present, environment changes and restoration.
The focused 15-test run passed before a final defensive check was added for
incomplete mapping observations; its separate check is retained. That addition
does not change extraction or the recorded earlier method snapshot.

| Decision | Primary criterion | Veto status | Uncertainty | Next action | Limit |
| --- | --- | --- | --- | --- | --- |
| Retain observation repair | Exact extraction and question equality passed | No changed source or lost output | Late mappings and a finite trace omit some inputs | Extend real multilingual/correction recovery | No legal or reuse acceptance |
| Keep native reuse veto | Mutable, incomplete native boundary persists | Complete closure is absent | 86 unclassified trace lines and 46 nonregular/dynamic paths | Review an immutable supported runtime before confinement integration | Trace counts do not prove dependency closure |

The strongest alternative explanation is that the selected scan simply does
not exercise optional libraries or failure paths. A new input family can expose
additional dependencies. This package is therefore partial and host-specific;
native isolation, immutable mounts, race freedom and second-host portability
remain open. Existing historical manifests were not rewritten. The trace is
retained in full so parser omissions remain inspectable.
