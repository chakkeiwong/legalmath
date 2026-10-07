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


def adoption_snapshots(command):
    """Retain reconstruction for ignored snapshots, including old source bytes."""
    manifest_path = ROOT / REL / "snapshot-manifest.json"
    if command == "snapshot-inventory":
        if manifest_path.exists():
            raise ValueError("Snapshot manifest already exists; preserve it")
        candidates = {}
        for manifest in (ROOT / REL / "phases").glob("*/attempt-*/read-context.json"):
            for row in json.loads(manifest.read_text())["records"]:
                if row["kind"] in {"file", "external-file"} and row["sha256"]:
                    candidates.setdefault(row["sha256"], set()).add(row["name"])
        models = json.loads((ROOT / REL / "tool-setup/layout-model/receipt.json").read_text())
        model_by_hash = {row["sha256"]: row for row in models["files"]}
        records = []
        archive = ROOT / REL / "snapshot-archive"
        for path in sorted((ROOT / REL / "snapshots").iterdir()):
            if path.name.startswith("."):
                continue
            identity = sha(path)
            if identity != path.name:
                raise ValueError("Snapshot is corrupt: " + str(path))
            sources = sorted(candidates.get(identity, []))
            usable = [name for name in sources if not Path(name).is_absolute()
                      and (ROOT / name).is_file() and sha(ROOT / name) == identity]
            row = {"snapshot": str(path.relative_to(ROOT)), "sha256": identity,
                   "bytes": path.stat().st_size, "observed_sources": sources}
            if usable:
                row.update(kind="retained-file", source=usable[0])
            elif identity in model_by_hash:
                model = model_by_hash[identity]
                row.update(kind="external-model", source=model["file"], url=model["url"],
                           revision=models["revision"])
            else:
                archive.mkdir(parents=True, exist_ok=True)
                packed = archive / (identity + ".gz")
                with path.open("rb") as src, packed.open("wb") as dst:
                    with gzip.GzipFile(filename="", fileobj=dst, mode="wb", mtime=0) as enc:
                        shutil.copyfileobj(src, enc, 1024 * 1024)
                with gzip.open(packed, "rb") as decoded:
                    if sha_stream(decoded) != identity:
                        raise ValueError("Snapshot archive mismatch")
                row.update(kind="archived", archive=str(packed.relative_to(ROOT)), archive_sha256=sha(packed))
            records.append(row)
        manifest_path.write_text(json.dumps({"version": "adoption-snapshots.v1", "files": records,
            "prerequisites": ["Restore retained historical repair checkpoints first when their source files are absent",
                              "Download pinned model files from the recorded URLs only if external-model inputs are absent",
                              "Tool environment recreation is separate; exact distribution bytes are checked in phase receipts"],
            "restore_command": "python3 -m scripts.archive_prospectus_successor_checkpoint restore-snapshots --campaign adoption"}, indent=2) + "\n")
    else:
        for row in json.loads(manifest_path.read_text())["files"]:
            destination = contained(row["snapshot"])
            if destination.exists():
                if sha(destination) != row["sha256"]:
                    raise ValueError("Existing snapshot differs; refusing overwrite")
                continue
            if command == "verify-snapshots":
                raise ValueError("Snapshot absent; run restore-snapshots")
            source = Path(row.get("source", ""))
            if row["kind"] == "retained-file":
                source = (ROOT / source).resolve()
                if not source.is_relative_to(ROOT):
                    raise ValueError("Snapshot source escapes checkout")
            elif row["kind"] == "external-model":
                if not source.resolve().is_relative_to(Path("/tmp/prospectus-adoption-models")):
                    raise ValueError("Snapshot model escapes declared directory")
            else:
                source = contained(row["archive"])
                if sha(source) != row["archive_sha256"]:
                    raise ValueError("Snapshot archive changed")
            destination.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(dir=destination.parent, prefix=".restore-")
            try:
                opener = gzip.open if row["kind"] == "archived" else open
                with opener(source, "rb") as src, os.fdopen(fd, "wb") as dst:
                    shutil.copyfileobj(src, dst, 1024 * 1024)
                if sha(Path(temporary)) != row["sha256"]:
                    raise ValueError("Snapshot source differs from recorded hash")
                os.replace(temporary, destination)
            finally:
                if Path(temporary).exists():
                    Path(temporary).unlink()
    print(json.dumps({"command": command, "manifest": str(manifest_path.relative_to(ROOT)), "status": "PASS"}))


def main():
    global REL, OUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["inventory", "pack", "verify", "restore", "snapshot-inventory", "restore-snapshots", "verify-snapshots"])
    parser.add_argument("--campaign", choices=["successor", "repair", "adoption"], default="successor")
    args = parser.parse_args()
    REL = Path("docs/implementation/prospectus-" + args.campaign + ("" if args.campaign == "adoption" else "-2026-10-06"))
    OUT = ROOT / REL / "checkpoint"
    if "snapshot" in args.command:
        if args.campaign != "adoption":
            raise ValueError("Snapshot reconstruction applies to adoption only")
        adoption_snapshots(args.command)
        return
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
