# Review of restoring the CDM exchange dependency

The revision183 source-only preparation is recorded and its immutable output
manifest is verified. It reports `task_complete: false`, no CDM import or official
round trip, and no receiver compatibility. The original CDM profile remains
external and waiting.

Restore `cdm-roundtrip.depends_on` to `["cdm-profile"]`, remove the transient
source-only selector, and return the actual-exchange dossier and reason. Keep
all preparation evidence in the same task's input bindings. Preserve the original
two-admission budget: the first source-preparation admission is consumed and only
one remains. Do not create a separate task or use source preparation as a package
acceptance result.

Skeptical audit: PASS. This is necessary to reinstate the original dependency
before handoff. It changes no obligation, acceptance criterion, task stream or
budget. The true receiver, version/profile, runtime and native functions remain
unknown, so actual CDM work remains blocked on that input.
