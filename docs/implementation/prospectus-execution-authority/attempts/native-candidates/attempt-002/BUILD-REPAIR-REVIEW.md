# One bounded repair of the isolated build configuration

The first compiled module linked successfully but the actual writer returned
"No OCR support in this build" before any recognition. config.h lines 308--310
defines OCR_DISABLED unless HAVE_LEPTONICA and HAVE_TESSERACT are both supplied.
The installed runtime already exported and executed these capabilities in the
retained direct trace. The failure is our trial's compile-configuration error.
Preserve unpatched.c, unpatched.so, its build manifest, wrapper.c, original
scripts and the failed page directory. No successful native run is overwritten.

The repaired build adds these two flags and retains -z defs, so missing installed
native dependencies still fail instead of being fabricated. The source audit
also found that the option string skew=none is parsed by this release as a
numeric zero-angle deskew request. The repaired wrapper omits the skew option,
selecting the actual no-deskew default used by the original comparator. This
removes a known baseline mismatch before recognition; no claim is made that the
failed module produced comparable pixels.

Use separate v2 scripts, wrapper-v2.c, unpatched-enabled.c/.so and page directories.
Their new manifests bind the actual methods and configurations. Require exact
266-word/box reproduction and 21099 Tz before the planned patch. This is the
single diagnosed bounded implementation repair allowed for arm A; a further
compile/link/ABI/baseline failure stops that arm and is retained. Continue the
independent fresh-callback arm. It needs no compiler-configuration repair.

Audit PASS: the config condition and parser behavior are inspected in exact
source; the repair changes build usage and default selection, not the original
native comparator or required evidence. Installed files remain unchanged.
