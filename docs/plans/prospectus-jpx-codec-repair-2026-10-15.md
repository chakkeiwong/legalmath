# Repair the reproduced Japanese native runtime dependency

Baseline native-layout005 failed inside the trusted sealed runtime:
PyMuPDF page.get_text() called Python's raw_unicode_escape decoder,whose
module was absent from the declared snapshot. Both exact JPX PDFs are retained.
This is an implementation/dependency defect on our side,not an OCR or source
quality finding. Retain the original failing receipt and immutable snapshot.

The repair adds only the installed interpreter's
lib/python3.11/encodings/raw_unicode_escape.py to a new snapshot. Its source
imports codecs and uses the built-in raw_unicode_escape implementation;the
existing interpreter already contains codecs. The helper and two original
PDFs remain byte-identical. No switch to an unrestricted native runtime and no
missing-dependency suppression is allowed. This is the smallest discriminating
repair;it does not establish that every Python codec or source family is covered.

Question and primary criterion: does the same real two-source inspection now
complete,and do both exact PDFs reach P1–P5 and the ordinary full answer with
all worker words preserved? The explicit negative comparator is the sealed005
missing-codec failure. Positive evidence requires original image/page inventory,
identity checks,actual downstream consumption,repeated full answer and adverse
product controls. No synthetic ASCII-only smoke can close this repair.

Assumption audit: exact host-installed codec bytes are a reviewed dependency,
not a change of Python/PyMuPDF version. Early diagnostic is the same helper
over the same PDFs. Any other dependency failure remains a separate finding,
not an excuse for an unrestricted fallback. Native line order and extracted
words are observations,not independent Japanese readings. Vertical writing
is established only by inspected original images;zero wmode1 alone is weaker.
All authority/publication/meaning limits from the source-pair plan continue.

Skeptical audit: PASS. The named blocker is reproduced in retained stderr,the
change is a single necessary codec file,and successful execution must answer
the original source task. No retry uses the unchanged snapshot,no old evidence
is rewritten,and no additional download occurs. A missing/corrupt input or
stream,second implementation failure,or exhausted bound ends the package.
Promotion of language/meaning quality remains separate from repairing startup.

Bounds: one reviewed cumulative native-layout admission5-to6,retaining all five
attempts and failed native start. Historical native lower bound70;new maximum
three reservations:one same helper,two Poppler calls. No native retry. HTTP
starts0;historical source-acquisition lower bound8. Native60seconds,stage120,
64MiB stream,evidence350MiB,one local implementation repair. No network,install,
OCR,GPU,model/API or external messages. Under the already approved wrapper,
use `.venv/bin/python -m scripts.prospectus_jpx_sources codec-<stage>` for
prepare,native-prepare,inspect,source,construct,compare. One-second yields and
retained sessions continue. Seal native-layout006,record,refresh,and continue
the substantive programme/correction question if the repaired source supports it.
