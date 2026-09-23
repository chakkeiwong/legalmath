"""Build the canonical book and keep the former proposal PDF identical."""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    subprocess.run([
        'latexmk', '-xelatex', '-interaction=nonstopmode', '-halt-on-error',
        '-cd', 'docs/monograph/monograph.tex',
    ], cwd=ROOT, check=True)
    shutil.copyfile(ROOT/'docs/monograph/monograph.pdf', ROOT/'docs/proposal/proposal.pdf')
    subprocess.run([sys.executable, str(ROOT/'scripts/check_proposal.py')],
                   cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
