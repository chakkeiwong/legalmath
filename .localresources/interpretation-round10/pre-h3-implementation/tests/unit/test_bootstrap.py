import subprocess
import sys


def test_isolated_cli():
    import legalmath
    assert legalmath.__version__ == "0.1.0"
    assert sys.prefix != sys.base_prefix
    assert subprocess.check_output([sys.executable, "-m", "legalmath.cli", "--version"], text=True).strip() == "0.1.0"
