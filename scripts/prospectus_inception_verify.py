"""Offline validation of immutable INCEpTION server evidence, without restarting it."""
import io
import json
from pathlib import Path
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
import zipfile


def validate(folder, *, current=True):
    from scripts.prospectus_inception import ROOT, check_configuration, file_sha, packets, project_json, runtime_identity, sha

    manifest = json.loads((folder / "manifest.json").read_text())
    result = json.loads((folder / "result.json").read_text())
    if manifest["status"] != "SERVER_EXCHANGE_PASS" or result["status"] != manifest["status"]:
        raise ValueError("No completed server exchange")
    if result["ui"]["status"] != "TWO_BROWSER_EDITS_PERSISTED":
        raise ValueError("Browser edits were not exercised")
    if result["ui"]["curation"] != "TWO_EMPTY_CURATION_EXPORTS_AFTER_OPENING":
        raise ValueError("Runtime curation was not checked")
    if not manifest.get("outputs"):
        raise ValueError("Unsealed historical diagnostic cannot establish current acceptance")
    for name, expected in manifest["outputs"].items():
        if Path(name).name != name or file_sha(folder / name) != expected:
            raise ValueError("Evidence changed: " + name)
    if sha(json.dumps(manifest["method"], sort_keys=True).encode()) != manifest["method_fingerprint"]:
        raise ValueError("Method fingerprint mismatch")
    if current:
        if manifest["runtime_identity"] != runtime_identity():
            raise ValueError("Runtime/sidecar bytes changed")
        for name, expected in manifest["method"].items():
            if not (ROOT / name).resolve().is_relative_to(ROOT) or file_sha(ROOT / name) != expected:
                raise ValueError("Trial no longer represents current method/input: " + name)
    stopped = json.loads((folder / "server-stop.json").read_text())
    if not stopped["stopped"] or stopped["exit_code"] is None:
        raise ValueError("Owned server shutdown was not recorded")
    settings = json.loads((folder / "server-settings.json").read_text())
    if settings["server.address"] != "127.0.0.1":
        raise ValueError("Server was not isolated on localhost")
    accounts = json.loads((folder / "accounts.json").read_text())
    access = json.loads((folder / "access-checks.json").read_text())
    if result["ui"]["access"] != "FOUR_CROSS_ACCOUNT_REQUESTS_DENIED" or len(access["checks"]) != 4:
        raise ValueError("Runtime account authorization checks missing")
    if {(r["reader"], r["requested_owner"]) for r in access["checks"]} != {
        (user, target) for user in accounts["readers"] for target in ["trial-admin", *[u for u in accounts["readers"] if u != user]]}:
        raise ValueError("Wrong cross-account authorization cases")
    if any(r["denial"] != "Requested document does not exist or you have no permissions to access it." for r in access["checks"]):
        raise ValueError("Expected explicit access denial")
    permissions = json.loads((folder / "permissions.json").read_text())["body"]
    for user in accounts["readers"]:
        if {p["role"] for p in permissions if p["user"] == user} != {"ANNOTATOR"}:
            raise ValueError("Synthetic reader has wrong permissions")
    for name in ("project-before.zip", "project-final.zip"):
        _, _, project = project_json((folder / name).read_bytes())
        check_configuration(project)
    http = json.loads((folder / "http.json").read_text())
    for response in http:
        if file_sha(folder / response["file"]) != response["sha256"]:
            raise ValueError("Raw server response was changed")
    ids = json.loads((folder / "project-ids.json").read_text())
    checks = []
    with tempfile.TemporaryDirectory(prefix="legalmath-inception-verify-") as temporary:
        temporary = Path(temporary)
        packets(temporary)
        for name in ("unicode", "basf"):
            for suffix in ("original", "expected-edit"):
                if (temporary / f"{name}-{suffix}.json").read_bytes() != (folder / f"{name}-{suffix}.json").read_bytes():
                    raise ValueError("Frozen packet differs from reviewed input or intended edit")
            for stage in ("original", "after"):
                for index, user in enumerate(["trial-admin", *accounts["readers"]]):
                    exported = f"{name}-{stage}-reader-{index}.zip"
                    path = f"/api/aero/v1/projects/{ids['project']}/documents/{ids['documents'][name]}/annotations/{user}?format=xmi"
                    if not any(r["method"] == "GET" and r["path"] == path and r["file"] == exported and r["status"] == 200 for r in http):
                        raise ValueError("Export lacks the expected server response provenance")
                    suffix = "expected-edit" if stage == "after" and index == 0 else "original"
                    command = ["/tmp/prospectus-adoption-tools/bin/python", "-m", "scripts.prospectus_inception_xmi", "decode",
                               "--packet", str(folder / f"{name}-{suffix}.json"), "--xmi", str(folder / exported),
                               "--output", str(temporary / (exported + ".json")), "--expect-equal"]
                    run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
                    if run.returncode:
                        raise ValueError(exported + ": " + run.stderr)
                    checks.append(exported)
            with zipfile.ZipFile(io.BytesIO((folder / f"{name}-curation.zip").read_bytes())) as archive:
                tree = ET.fromstring(archive.read(next(n for n in archive.namelist() if n.endswith(".xmi"))))
            packet = json.loads((folder / f"{name}-original.json").read_text())
            if any(n.tag.endswith(("LegalEvidence", "LegalRelation")) for n in tree):
                raise ValueError("Automatic curation merge was not prevented")
            if next(n for n in tree if n.tag.endswith("}Sofa")).get("sofaString") != packet["text"]:
                raise ValueError("Empty curation has wrong source text")
    return {"status": "OFFLINE_EVIDENCE_PASS", "trial": str(folder.relative_to(ROOT)),
            "trial_manifest_sha256": file_sha(folder / "manifest.json"), "exact_packet_checks": checks,
            "independence": "NOT_ESTABLISHED", "legal_acceptance": "PENDING"}


def verify():
    from scripts.prospectus_inception import OUT, ROOT, save
    candidates = [p.parent for p in sorted(OUT.glob("run-*/manifest.json"))
                  if json.loads(p.read_text()).get("status") == "SERVER_EXCHANGE_PASS"]
    if not candidates:
        raise ValueError("No passing server trial; continue the reviewed repair sequence")
    started = time.monotonic()
    result = validate(candidates[-1])
    base = OUT / "verification"
    index = 1
    while (base / f"attempt-{index:03d}.json").exists():
        index += 1
    result["wall_seconds"] = time.monotonic() - started
    result["command"] = "python3 -m scripts.prospectus_inception verify"
    save(base / f"attempt-{index:03d}.json", result)
    print(json.dumps(result, indent=2))
