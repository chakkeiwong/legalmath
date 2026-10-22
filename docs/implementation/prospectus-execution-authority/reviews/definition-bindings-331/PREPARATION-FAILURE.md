# Preparation failure retained

The first proposal preparation ran before METHOD-REVIEW.md and the stage
runner had been written. It exited with FileNotFoundError while constructing
the binding manifest, after retaining profile.json, profiles.json and the
candidate copies. No candidate evaluation, authority revision or admission
occurred. The partial files are retained and are not success evidence.

The next preparation must use a distinct method and output directory or
explicitly validate these retained partial files before completing the
proposal. It must not overwrite them or rerun the same exclusive writes.
The elapsed preparation time was not recorded; charge a conservative90seconds
within the cumulative account rather than report it as measured or zero.
