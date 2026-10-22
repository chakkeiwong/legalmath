# Source rehearsal implementation review

The new adapter replaces only sealed_runtime.run for selected routes and
subprocess.run for the default reference. The real SourceRuntime.execute,
required-file hashes, receipt validation, source parser, graph assembly,
correction admission and downstream consumers remain active. A Popen guard
prevents unexpected execution. Returned bytes and receipts remain exactly the
historical records; all current evidence labels their delivery as rehearsal.

Current default source code requests90s for both pdftotext and retained-image
verification. Historical008 capture_default applied min(requested_timeout,60),
so its records contain60s. This was verified in the source before execution.
The adapter requires90s requested and60s recorded, retaining both in the dispatch
record. It does not falsely claim the original caller requested60s. Selected
calls already use the real60s runtime boundary and original stream capacities.

The2009 raw request comes from raw-P1 rather than the consumed correction-bound
request. The2010 source driver stored its direct source_product as P1 without
a correction rebind; its absent raw-P1 is not synthesized as historical data.
For each route current raw/consumed P1 and downstream full objects must equal
their exact available comparator. No semantic field is dropped to pass.

The source driver is confined to offline stages in this admission. Native
execution, the live boundary probe, current host dependency closure and an
acceptance registration remain separate work. Method and test snapshots will
bind the actual current source adapter;014's sealed files are unchanged.
