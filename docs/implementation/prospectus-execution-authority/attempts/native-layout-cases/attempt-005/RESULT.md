# Japanese originals retained; sealed-runtime inspection failed

Both exact official JPX links returned PDFs:programme1,882,811bytes SHA256
a85164ea1ef41a307e7738a96884802671b03d272e2cd82ffab9e6b747d0febb;
correction72,709bytes SHA256
c67822ee5fcbdebba0e099bf5cde415e09da121c6e32e8b5c5ce0e22c6495ce9.
Original bodies,headers,commands and exits are retained. No redirects were
followed. Two of three permitted HTTP starts were consumed;earlier six remain
consumed,for a visible source-acquisition lower bound of eight.

The first sealed native inspection failed before producing its JSON report.
The retained stderr ends `LookupError: unknown encoding: raw_unicode_escape`
in PyMuPDF's PyUnicode_DecodeRawUnicodeEscape called from page.get_text().
The parent snapshot includes only encodings/__init__.py,aliases.py,utf_8.py and
their cached versions. The current installed Python environment contains
encodings/raw_unicode_escape.py;its implementation imports codecs and exposes
the built-in raw_unicode_escape decoder. This is a missing declared runtime
dependency on our side. The PDFs' layout,reading order and linguistic accuracy
have not yet been evaluated. No package inadequacy follows from this failure.

| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Unsupported conclusion |
|---|---|---|---|---|---|
| Preserve original source acquisition | Both exact PDFs retained with HTTP evidence | No acquisition identity/size failure | Source authority and meaning unreviewed | Reuse exact bytes in a repaired runtime | Historical publication or legal precedence |
| Reject current native package execution | Required inventory and actual consumers absent | Missing declared codec stops inspection | Further unexercised dependencies | Reviewed new snapshot with the required codec;actual same-source inspection and consumers | No Japanese text or fundamental PyMuPDF failure |

One of three native reservations was consumed;the historical visible native
lower bound is70. No OCR,install,GPU or model call occurred. No local repair was
executed in this attempt. The package did not deliver its required downstream
comparison. Preserve this failed attempt and do not relabel it accepted.
The next reviewed package must retain the failure and exact originals,change
the missing-codec declaration,and keep the earlier call history. No further
network acquisition is needed for that repair.
