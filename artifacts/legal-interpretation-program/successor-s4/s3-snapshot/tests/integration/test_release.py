from pathlib import Path
import zipfile
import pytest
from tests.helpers import prepare_release
from legalmath.errors import LegalMathError
from legalmath.storage.archive import export_history, import_history


def test_exact_release_export_history_and_retirement(db, root, tmp_path, case):
    w = prepare_release(db, root, tmp_path, case)
    r = w["releases"].release("engineer", "release", w["state"]["bundle_hash"], w["manifest"], w["state"]["revision"], case["valid_at"])
    exported = w["releases"].export_java(r["release_hash"], tmp_path / "export")
    assert (tmp_path / "export/policy.jar").is_file() and exported["authority"] == "LOCAL_SYNTHETIC"
    with db.connect() as con:
        assert w["releases"].select(con, w["app"]["scope_key"], case["valid_at"], case["known_at"])["hash"] == r["release_hash"]
    export_history(db, tmp_path / "history.zip")
    restored = import_history(tmp_path / "history.zip", tmp_path / "restored")
    assert restored.verify()
    from legalmath.review.releases import Releases
    assert Releases(restored).export_java(r["release_hash"], tmp_path / "reexport")["jar_sha256"] == exported["jar_sha256"]
    w["releases"].retire("engineer", "retire", r["release_hash"], case["valid_at"], r["revision"])
    with db.connect() as con, pytest.raises(LegalMathError):
        w["releases"].select(con, w["app"]["scope_key"], case["valid_at"], case["known_at"])
    with db.connect() as con:
        assert db.get(con, r["release_hash"])["bundle_hash"] == w["state"]["bundle_hash"]


def test_corrupt_jar_cannot_release(db, root, tmp_path, case):
    w = prepare_release(db, root, tmp_path, case)
    db.blobs.path(w["build"]["jar_sha256"]).write_bytes(b"wrong jar")
    with pytest.raises(LegalMathError) as e:
        w["releases"].release("engineer", "bad-release", w["state"]["bundle_hash"], w["manifest"], w["state"]["revision"], case["valid_at"])
    assert e.value.code == "E_HASH_MISMATCH"
    with db.connect() as con:
        assert con.execute("SELECT count(*) FROM releases").fetchone()[0] == 0


def test_tampered_archive_rejected(db, tmp_path):
    db.mutate("test", "key", {}, lambda con: {"answer": 1})
    original, tampered = tmp_path / "good.zip", tmp_path / "bad.zip"
    export_history(db, original)
    with zipfile.ZipFile(original) as a, zipfile.ZipFile(tampered, "w") as b:
        for name in a.namelist():
            b.writestr(name, b"wrong" if name == "history.json" else a.read(name))
    with pytest.raises(LegalMathError): import_history(tampered, tmp_path / "restored")


def test_overlapping_release_is_rejected(db, root, tmp_path, case):
    from copy import deepcopy
    w = prepare_release(db, root, tmp_path, case)
    lc, releases = w["lifecycle"], w["releases"]
    first = releases.release("engineer", "release1", w["state"]["bundle_hash"], w["manifest"], w["state"]["revision"], case["valid_at"])
    changed_case = deepcopy(w["case"])
    changed_case["bundle"]["bundle_id"] = "synthetic.overlap"
    state = lc.create("author", "bundle2", changed_case["bundle"])
    inventory = [{"source_span": span, "disposition": "Synthetic unchanged source profile for overlap rejection test", "rule_ids": [changed_case["rule_id"]]} for span in changed_case["bundle"]["source_spans"]]
    state = lc.record_coverage("meaning", "coverage2", state["bundle_hash"], inventory, state["revision"])
    with db.connect() as con:
        old_manifest = db.get(con, w["manifest"])
        assessment = db.get(con, old_manifest["applicability_hash"])
    assessment.update(bundle_hash=state["bundle_hash"], assessment_id="scope.overlap")
    app = lc.assess("meaning", "scope2", assessment)
    build = releases.build("engineer", "build2", state["bundle_hash"], tmp_path / "build2", root / ".localresources/java-toolchain/jdk-17.0.20.1+1", [changed_case])
    with pytest.raises(LegalMathError):
        releases.prepare("engineer", "stale-report", build["build_manifest_hash"], w["build"]["verification_report_hash"], app["applicability_hash"], assessment["valid_from"], assessment["valid_until"])
    manifest = releases.prepare("engineer", "prepare2", build["build_manifest_hash"], build["verification_report_hash"], app["applicability_hash"], assessment["valid_from"], assessment["valid_until"])["java_release_manifest_hash"]
    state = lc.transition("author", "submit2", state["bundle_hash"], "submit", state["revision"])
    state = lc.transition("meaning", "meaning2", state["bundle_hash"], "approve_meaning", state["revision"], manifest_hash=manifest)
    state = lc.transition("engineer", "engineer2", state["bundle_hash"], "approve_engineering", state["revision"], manifest_hash=manifest)
    with pytest.raises(LegalMathError) as e:
        releases.release("engineer", "overlap", state["bundle_hash"], manifest, state["revision"], case["valid_at"])
    assert e.value.code == "E_RELEASE_BLOCKED"
