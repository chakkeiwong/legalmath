"""Lossless Git checkpoint for oversized generated prospectus evidence."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REL = Path("docs/implementation/prospectus-successor-2026-10-06")
OUT = ROOT / REL / "checkpoint"
LIMIT = 8 * 1024 * 1024


def sha_stream(stream):
    h = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        h.update(block)
    return h.hexdigest()


def sha(path):
    with path.open("rb") as stream:
        return sha_stream(stream)


def untracked():
    raw = subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=ROOT)
    return [ROOT / p for p in raw.decode().split("\0") if p]


def contained(relative):
    path = (ROOT / relative).resolve()
    if not path.is_relative_to((ROOT / REL).resolve()):
        raise ValueError("Archive path outside evidence directory")
    return path


def main():
    global REL, OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["inventory", "pack", "verify", "restore"])
    parser.add_argument("--campaign", choices=["successor", "repair"], default="successor")
    args = parser.parse_args()
    REL = Path("docs/implementation/prospectus-" + args.campaign + "-2026-10-06")
    OUT = ROOT / REL / "checkpoint"
    if args.command in {"inventory", "pack"}:
        files = [(p.stat().st_size, p) for p in untracked() if p.is_relative_to(ROOT / REL)]
        large = sorted(((n, p) for n, p in files if n >= LIMIT), reverse=True)
        if args.command == "inventory":
            print(json.dumps({"total_untracked_bytes": sum(n for n, _ in files),
                "oversized": [{"bytes": n, "path": str(p.relative_to(ROOT))} for n, p in large]}, indent=2))
            return
        OUT.mkdir(parents=True, exist_ok=True)
        if (OUT / "manifest.json").exists():
            raise ValueError("Checkpoint already exists; use verify or restore")
        records = []
        for size, path in large:
            before = sha(path)
            packed = OUT / (before + ".gz")
            if not packed.exists():
                with path.open("rb") as src, packed.open("wb") as dst:
                    with gzip.GzipFile(filename="", fileobj=dst, mode="wb", mtime=0, compresslevel=6) as enc:
                        shutil.copyfileobj(src, enc, 1024 * 1024)
            with gzip.open(packed, "rb") as decoded:
                if sha_stream(decoded) != before or sha(path) != before:
                    raise ValueError("Archive round-trip mismatch")
            records.append({"path": str(path.relative_to(ROOT)), "sha256": before, "bytes": size,
                "archive": str(packed.relative_to(ROOT)), "archive_sha256": sha(packed),
                "archive_bytes": packed.stat().st_size})
        manifest = {"format": "gzip-by-sha256.v1", "threshold_bytes": LIMIT, "files": records,
            "restore_command": "python3 -m scripts.archive_prospectus_successor_checkpoint restore --campaign " + args.campaign}
        (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        ignore = ROOT / ".gitignore"
        old = ignore.read_text()
        marker = "# Oversized " + args.campaign + " evidence: exact bytes in checkpoint/manifest.json."
        if marker in old:
            raise ValueError("Archive ignore block already exists")
        ignore.write_text(old.rstrip() + "\n\n" + marker + "\n" +
                          "".join("/" + row["path"] + "\n" for row in records))
        print(json.dumps({"archived_files": len(records),
            "original_bytes": sum(r["bytes"] for r in records),
            "packed_unique_bytes": sum(p.stat().st_size for p in OUT.glob("*.gz")),
            "round_trip_sha256": "PASS", "original_files": "PRESERVED"}))
        return
    manifest = json.loads((OUT / "manifest.json").read_text())
    for row in manifest["files"]:
        packed = contained(row["archive"])
        target = contained(row["path"])
        if sha(packed) != row["archive_sha256"]:
            raise ValueError("Compressed checkpoint changed")
        with gzip.open(packed, "rb") as stream:
            if sha_stream(stream) != row["sha256"]:
                raise ValueError("Checkpoint decoded hash mismatch")
        if target.exists():
            if sha(target) != row["sha256"]:
                raise ValueError("Existing file differs; refusing overwrite")
        elif args.command == "restore":
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(dir=target.parent, prefix=".restore-")
            try:
                with os.fdopen(fd, "wb") as dst, gzip.open(packed, "rb") as src:
                    shutil.copyfileobj(src, dst, 1024 * 1024)
                if sha(Path(temporary)) != row["sha256"]:
                    raise ValueError("Restored hash mismatch")
                os.replace(temporary, target)
            finally:
                if Path(temporary).exists():
                    Path(temporary).unlink()
        else:
            raise ValueError("Unpacked file absent; run restore")
    print(json.dumps({"status": "PASS", "files": len(manifest["files"]), "command": args.command}))


if __name__ == "__main__":
    main()
