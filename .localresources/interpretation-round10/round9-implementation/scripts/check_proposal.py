"""Compatibility check for the proposal entry point of the unified monograph.

The original v0.3 checker is frozen with the pre-unification baseline. The
proposal no longer has separate scientific content or independent acceptance.
"""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    for name in ['check_monograph.py', 'check_unified_monograph.py']:
        subprocess.run([sys.executable, str(ROOT/'scripts'/name)], cwd=ROOT, check=True)
    result = json.loads((ROOT/'docs/monograph/review/unification/preservation-check.json').read_text())
    alias = {
        'status':result['status'],
        'document':'UNIFIED_MONOGRAPH',
        'canonical_tex':'docs/monograph/monograph.tex',
        'canonical_pdf':'docs/monograph/monograph.pdf',
        'proposal_pages':result['page_comparison']['unified'],
        'proposal_sha256':result['canonical_pdf_sha256'],
        'preservation_report':'docs/monograph/review/unification/preservation-check.json',
        'independent_reader_acceptance':'PENDING',
    }
    (ROOT/'docs/proposal/validation.json').write_text(json.dumps(alias,indent=2)+'\n')


if __name__ == '__main__':
    main()
