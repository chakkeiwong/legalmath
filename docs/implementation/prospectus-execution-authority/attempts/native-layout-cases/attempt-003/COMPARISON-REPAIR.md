# One local comparison repair

The original comparison attempted to parse retained Poppler XML directly. It
failed at a control character which the actual source importer already removes
and records explicitly. This was a mismatch in our diagnostic, not a new native
extraction failure. The failed invocation retains its method and result.

The reviewed comparison applies the exact same limited XML-control filter and
requires the complete removed-offset/codepoint list to equal the actual P1
record. The untouched original native stream stays retained. No native call is
repeated. This consumes the package's one local implementation repair. A
further comparison failure is retained without another repair in this package.
