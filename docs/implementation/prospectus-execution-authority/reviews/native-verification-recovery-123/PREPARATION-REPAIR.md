# Correct the historical inventory path before admission

The first local inventory command stopped before writing any proposed revision
or inventory: attempt006 retains `fresh/P1.json.gz` and `retained/P1.json.gz`,
not `raw-P1.json.gz`. Attempt008 separately retains raw and rebound products.
The preparation script now records each exact path and explicitly distinguishes
the consumed rebound 2010 P1 from the raw 2009 P1. It does not rename, synthesize
or replace a historical source product. No product/native execution or task
admission occurred during this failed file lookup.
