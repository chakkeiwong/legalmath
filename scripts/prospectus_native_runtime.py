"""Explicit optional sealed-file worker; never changes extraction defaults."""
import argparse
from contextlib import nullcontext
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT)]
from legalmath.prospectus.successor.sealed_runtime import digest, run, verify_receipt
from legalmath.prospectus.successor.process_ledger import observe


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--stdin-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--process-ledger")
    parser.add_argument("argv", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    folder = Path(args.snapshot)
    manifest = json.loads((folder / "manifest.json").read_text())
    if digest(manifest) != args.manifest_sha256:
        raise ValueError("Runtime manifest identity mismatch")
    target = Path(args.output)
    target.mkdir(parents=True, exist_ok=False)
    argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
    stdin = Path(args.stdin_file).read_bytes()
    with observe(args.process_ledger) if args.process_ledger else nullcontext():
        result = run(folder, manifest, argv, stdin)
    verify_receipt(result['receipt'], manifest, argv, stdin, result['stdout'], result['stderr'])
    for stream in ("stdout", "stderr"):
        (target / stream).write_bytes(result.pop(stream))
    (target / "receipt.json").write_text(json.dumps(result['receipt'], indent=2) + "\n")
    print(json.dumps({'returncode': result['returncode'], 'receipt_sha256': result['receipt']['receipt_sha256'],
                      'manifest_sha256': result['receipt']['manifest_sha256']}))
    return result["returncode"]


if __name__ == "__main__":
    raise SystemExit(main())
