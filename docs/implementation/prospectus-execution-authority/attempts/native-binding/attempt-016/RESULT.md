# Current native implementation

The live driver, exact explicit-grant checks and separate current validator are implemented. All95 focused tests passed in1.56s; runner wall1.6514s. The exact future registry candidate was loaded in an isolated namespace and dispatched the real validator, which refused a missing live grant. Registration is not yet applied and no native calls were made.

The next live revision must bind the reviewed registry and rerun current tests. Both historical runtime snapshots remain immutable. New owned snapshots permit complete source, receipt and answer equality without dropping provenance fields.

| Decision | Primary criterion | Veto status | Main uncertainty | Next action | Limit |
| --- | --- | --- | --- | --- | --- |
| Retain implementation |95 tests and actual candidate dispatch pass | No focused failure | Fresh execution still untested | Reviewed grant, current tests and canary | No task acceptance |

The strongest alternative explanation is shared parser/interpretation error on exposed examples. Only actual fresh routes and independent reviews can address their respective remaining gaps.
