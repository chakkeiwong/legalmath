# Main integration

The Catala implementation (`09a81a31`) and retained evidence (`64889253`) were
fast-forwarded into main on 28 September 2026. All 88 previously modified tracked
files retained their exact bytes at the merge, and the existing index diff was
unchanged. No dirty file overlapped the integrated changes.

Twenty focused tests passed from main in 53.54 seconds with no failures or skips:
shared/native CLI execution, resource rejection, the combined helper/collection/
partial-evidence/exception/rounding case, and native trace/compiler comparisons.
The complete 807-test run remains identified with the clean `09a81a31` checkpoint;
the focused main checks do not claim to revalidate all concurrent unrelated work.

The local manuscript incorporates the engineering follow-up. Its TeX/PDF review
is recorded under `docs/monograph/review/catala-engineering-closure/`. It remains
part of the existing uncommitted manuscript revision, alongside other active
work, and is not included in this engineering integration commit.

The closing synchronization uses a normal push of main and a fast-forward of the
Catala branch to main. Remote ancestry and branch equality are checked afterward.
The [integration manifest](integration.json) preserves the exact test command,
IDs and hashes. No historical evidence was rewritten.
