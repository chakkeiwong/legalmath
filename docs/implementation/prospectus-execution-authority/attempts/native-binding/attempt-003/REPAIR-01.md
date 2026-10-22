# Inventory path repair before the first native launch

Preparation failed before creating a snapshot or launching a worker. The old
trace contains five successful paths with parent components: the interpreter's
bin/../lib directory and four lib-dynload/../../ library names. Passing these
trace strings directly to the strict snapshot API was our inventory-driver
error. The launcher's rejection is correct.

For each observed path, compare its actual strict resolved target with the
strict resolved target of its normalized absolute spelling. Refuse if they
differ; this avoids treating lexical normalization as valid across a
symlink-sensitive parent operation. Retain every raw/normalized/resolved alias.
When duplicate destinations occur, require identical resolved source identity.
Keep explicit library aliases needed by the dynamic loader. The namespace has
no host directory symlinks: declared destinations remain canonical, with file
bytes copied from their verified source. Do not relax the launcher path rules.

Skeptical review PASS for this bounded inventory repair. The exact OCR and
boundary comparators remain unchanged. The first failed preparation, its
method snapshots and its two case specifications remain intact. The changed
preparation reuses case files only after exact equality checks. This consumes
the first of two allowed inventory/launcher repairs; zero native launches have
occurred. Run the changed preparation once, then the actual boundary controls.
