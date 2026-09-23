"""Complete public-source engineering walkthrough with explicit synthetic authority."""
from copy import deepcopy
from pathlib import Path
import json
import subprocess

from .canonical import canonical, digest
from .storage import Database
from .storage.archive import export_history, import_history
from .sources.intake import import_spi
from .sources.discovery import import_pilot
from .review.coverage import coverage_report
from .review.lifecycle import Lifecycle
from .review.releases import Releases
from .review.amendment import changes
from .ir.evaluate import evaluate
from .events.records import create_stream, append_event
from .events.replay import replay, consent_fact
from .errors import LegalMathError

IDENTITIES = {
    "synthetic.author": {"roles": ["author"], "token": "local-demo-author"},
    "synthetic.meaning": {"roles": ["meaning"], "token": "local-demo-meaning"},
    "synthetic.engineer": {"roles": ["engineering"], "token": "local-demo-engineer"},
}


def walkthrough(repository, workdir, jdk):
    root, out = Path(repository).resolve(), Path(workdir).resolve()
    if out.exists() and any(out.iterdir()):
        raise LegalMathError("E_INTEGRITY", details="Demo needs a fresh working directory.")
    out.mkdir(parents=True, exist_ok=True)
    db = Database(out / "database")
    lc, releases = Lifecycle(db), Releases(db)
    lc.register(IDENTITIES)
    imported = import_spi(db, root)
    pilot = import_pilot(db, root)
    bundle = json.loads((root / "examples/java-dry-run/spec/spi-control.bundle.json").read_text())
    bundle["bundle_id"] = "spi.local_example"
    for i in bundle["interpretations"]:
        i["statement"] += " This version is exercised only under local synthetic engineering authority; bank interpretation remains pending."
    original_cases = json.loads((root / "examples/java-dry-run/spec/decision-cases.json").read_text())
    cases = [{**c, "bundle": bundle, "rule_id": "spi.streamlining", "expected": {"status": c["expected_status"], "blocking_inputs": c["expected_blocking_inputs"]}} for c in original_cases]
    state = lc.create("synthetic.author", "bundle", bundle)
    bh = state["bundle_hash"]
    inventory = json.loads((root / "examples/java-dry-run/spec/circular-disposition.json").read_text())["numbered_provisions"]
    with db.connect() as con:
        coverage = coverage_report(db, con, bundle, inventory)
    state = lc.record_coverage("synthetic.meaning", "coverage", bh, inventory, state["revision"])
    # These resolutions are restricted to the synthetic scenario. The original
    # interpretation with its open bank questions is preserved in the repository.
    for issue in coverage["issues"]:
        result = lc.resolve_issue("synthetic.meaning", "resolve." + issue, bh, issue,
            "Synthetic demonstration only: use the documented fixture premise for this engineering replay. The bank owner still must adjudicate " + issue + ".",
            cases[0]["known_at"], state["revision"])
        state["revision"] = result["revision"]
    app = {"assessment_id": "synthetic.spi_scope", "bundle_hash": bh,
        "legal_entity": "synthetic.bank", "regulated_role": "synthetic.distributor", "activity": "solicited",
        "product_class": "synthetic.funds", "client_class": "individual", "jurisdiction": "HK",
        "valid_from": bundle["valid_from"], "valid_until": bundle["valid_until"], "conclusion": "in_scope",
        "reason": "Selected public dry-run profile, solely for engineering acceptance.",
        "source_span_ids": [bundle["source_spans"][0]["id"]], "reviewer_id": "synthetic.meaning"}
    applicability = lc.assess("synthetic.meaning", "scope", app)
    event_cases = json.loads((root / "corpus/events/conformance.json").read_text())
    build = releases.build("synthetic.engineer", "build", bh, out / "candidate", jdk, cases, event_cases)
    manifest = releases.prepare("synthetic.engineer", "prepare", build["build_manifest_hash"], build["verification_report_hash"], applicability["applicability_hash"], bundle["valid_from"], bundle["valid_until"])["java_release_manifest_hash"]
    state = lc.transition("synthetic.author", "submit", bh, "submit", state["revision"])
    state = lc.transition("synthetic.meaning", "meaning", bh, "approve_meaning", state["revision"], manifest_hash=manifest)
    state = lc.transition("synthetic.engineer", "engineering", bh, "approve_engineering", state["revision"], manifest_hash=manifest)
    released = releases.release("synthetic.engineer", "release", bh, manifest, state["revision"], cases[0]["valid_at"])
    exported = releases.export_java(released["release_hash"], out / "java-release")
    (out / "host-snapshot.json").write_bytes(canonical(cases[0]["snapshot"]))
    host = out / "BankHost.java"
    host.write_text('''import java.nio.file.*;
public final class BankHost {
 public static void main(String[] args) throws Exception {
  System.out.println(''' + build["class_name"] + '''.evaluate(Files.readString(Path.of(args[0])),"spi.streamlining",args[1],args[1],"production"));
 }
}
''')
    caller_classes = out / "host-classes"
    caller_classes.mkdir()
    jar = out / "java-release/policy.jar"
    subprocess.run([str(Path(jdk) / "bin/javac"), "--release", "17", "-Xlint:all", "-Werror", "-cp", str(jar), "-d", str(caller_classes), str(host)], check=True, capture_output=True, timeout=30)
    native = subprocess.check_output([str(Path(jdk) / "bin/java"), "-cp", str(caller_classes) + ":" + str(jar), "BankHost", str(out / "host-snapshot.json"), cases[0]["valid_at"]], timeout=30)
    java_result = json.loads(native)
    if java_result["status"] != "TRUE": raise LegalMathError("E_INTEGRITY")
    (out / "host-result.json").write_bytes(canonical(java_result))

    def save_decision(snapshot, at, known, key):
        request = {"bundle_hash": bh, "snapshot": snapshot, "rule_id": "spi.streamlining", "valid_at": at,
            "known_at": known, "mode": "production", "release_hash": released["release_hash"], "operational_at": at}
        def operation(con):
            releases.select(con, applicability["scope_key"], at, at)
            result = evaluate(bundle, snapshot, "spi.streamlining", at, known, "production")
            ph = db.put(con, "evaluation", {"request": request, "result": result})
            con.execute("INSERT OR IGNORE INTO evaluations VALUES(?,?,?,?)", (result["result_hash"], ph, bh, released["release_hash"]))
            return result
        return db.mutate("synthetic.author", key, {"op": "demo_evaluate", **request}, operation)

    original = save_decision(cases[0]["snapshot"], cases[0]["valid_at"], cases[0]["known_at"], "original")
    at = "2026-09-21T02:02:00.000000Z"
    header = {"stream_id": "mslee.consent", "profile": "consent", "profile_version": "0.1", "subject": "client.synthetic.lee",
        "category": "funds", "actor": "synthetic.bank", "action": "streamline", "obligation_id": None,
        "inception": bundle["valid_from"], "ordering_authority": "synthetic.connector", "initial_snapshot": None}
    common = {"stream_id": header["stream_id"], "actor": header["actor"], "action": header["action"], "subject": header["subject"],
        "category": header["category"], "obligation_id": None, "recorded_at": at}
    events = [{**common, "id": "lee.grant", "sequence": 1, "kind": "consent.granted", "occurred_at": bundle["valid_from"], "evidence_id": "lee.written_consent"},
        {**common, "id": "lee.withdrawal", "sequence": 2, "kind": "consent.withdrawn", "occurred_at": "2026-09-21T02:01:00.000000Z", "evidence_id": "lee.withdrawal_notice"}]
    with db.transaction() as con:
        create_stream(db, con, header)
        for i, event in enumerate(events): append_event(db, con, header["stream_id"], event, i + 1)
        req = {"header": header, "events": events, "valid_at": at, "known_at": at,
            "completeness": {"complete_from": header["inception"], "complete_through": at, "recorded_at": at, "evidence_id": "connector.complete_export"}}
        consent = replay(req)
        rh = db.put(con, "replay", {"request": req, "result": consent})
        con.execute("INSERT INTO replays VALUES(?,?)", (rh, header["stream_id"]))
    snapshot = deepcopy(cases[0]["snapshot"])
    snapshot["facts"]["active_consent"] = consent_fact(consent, bundle["valid_from"], bundle["valid_until"])
    withdrawn = save_decision(snapshot, at, at, "withdrawn")
    if withdrawn["status"] != "FALSE": raise LegalMathError("E_INTEGRITY")
    amendment = deepcopy(bundle)
    amendment["bundle_id"] = "spi.synthetic_amendment"
    amendment["valid_from"], amendment["valid_until"] = "2026-10-01T00:00:00.000000Z", "2026-11-01T00:00:00.000000Z"
    next(r for r in amendment["rules"] if r["id"] == "spi.financial")["body"]["args"][0]["right"]["value"] = "4000000001"
    amendment["interpretations"][0]["statement"] += " SYNTHETIC AMENDMENT: increase the portfolio threshold by one cent to test change handling; not an SFC amendment."
    changed = lc.create("synthetic.author", "amendment", amendment, parent=bh)
    changed = lc.record_coverage("synthetic.meaning", "amendment.coverage", changed["bundle_hash"], inventory, changed["revision"])
    impact = changes(bundle, amendment)
    if "spi.streamlining" not in impact["affected_rule_ids"]: raise LegalMathError("E_INTEGRITY")
    (out / "amendment-impact.json").write_bytes(canonical(impact))
    for issue in coverage["issues"]:
        resolution = lc.resolve_issue("synthetic.meaning", "amendment.resolve." + issue, changed["bundle_hash"], issue,
            "Synthetic amendment scenario only; apply the one-cent test change and retain the documented fixture definitions. Bank meaning remains pending.",
            amendment["valid_from"], changed["revision"])
        changed["revision"] = resolution["revision"]
    amended_assessment = {**app, "assessment_id": "synthetic.amended_scope", "bundle_hash": changed["bundle_hash"],
        "valid_from": amendment["valid_from"], "valid_until": amendment["valid_until"]}
    amended_app = lc.assess("synthetic.meaning", "amendment.scope", amended_assessment)
    amended_snapshot = deepcopy(cases[0]["snapshot"])
    for entry in amended_snapshot["facts"].values():
        if entry["status"] == "known":
            entry.update(valid_from=amendment["valid_from"], valid_until=amendment["valid_until"], recorded_at=amendment["valid_from"])
    amended_case = {"id": "one_cent_synthetic_amendment", "bundle": amendment, "snapshot": amended_snapshot,
        "rule_id": "spi.streamlining", "valid_at": amendment["valid_from"], "known_at": amendment["valid_from"],
        "expected": {"status": "FALSE", "value": False}}
    amended_build = releases.build("synthetic.engineer", "amendment.build", changed["bundle_hash"], out / "amended-candidate", jdk, [amended_case], event_cases)
    amended_manifest = releases.prepare("synthetic.engineer", "amendment.prepare", amended_build["build_manifest_hash"], amended_build["verification_report_hash"], amended_app["applicability_hash"], amendment["valid_from"], amendment["valid_until"])["java_release_manifest_hash"]
    changed = lc.transition("synthetic.author", "amendment.submit", changed["bundle_hash"], "submit", changed["revision"])
    changed = lc.transition("synthetic.meaning", "amendment.meaning", changed["bundle_hash"], "approve_meaning", changed["revision"], manifest_hash=amended_manifest)
    changed = lc.transition("synthetic.engineer", "amendment.engineering", changed["bundle_hash"], "approve_engineering", changed["revision"], manifest_hash=amended_manifest)
    amended_release = releases.release("synthetic.engineer", "amendment.release", changed["bundle_hash"], amended_manifest, changed["revision"], amendment["valid_from"])
    releases.export_java(amended_release["release_hash"], out / "amended-java-release")
    with db.connect() as con:
        if releases.select(con, applicability["scope_key"], at, at)["hash"] != released["release_hash"]:
            raise LegalMathError("E_INTEGRITY")
        if releases.select(con, applicability["scope_key"], amendment["valid_from"], amendment["valid_from"])["hash"] != amended_release["release_hash"]:
            raise LegalMathError("E_INTEGRITY")
    package = export_history(db, out / "history.zip")
    restored = import_history(out / "history.zip", out / "restored-database")
    with restored.connect() as con:
        stored = con.execute("SELECT payload_hash FROM evaluations WHERE result_hash=?", (original["result_hash"],)).fetchone()[0]
        record = restored.get(con, stored)
        r = record["request"]
        replayed = evaluate(restored.get(con, r["bundle_hash"]), r["snapshot"], r["rule_id"], r["valid_at"], r["known_at"], r["mode"])
    if replayed != original: raise LegalMathError("E_INTEGRITY")
    result = {"status": "OFFLINE_WALKTHROUGH_PASSED", "authority": "LOCAL_SYNTHETIC", "bundle_hash": bh,
        "release_hash": released["release_hash"], "java": exported, "decision_cases": len(cases), "event_cases": len(event_cases),
        "coverage_provisions": len(coverage["provisions"]), "pilot_sources": len(pilot["sources"]),
        "original_decision": original["result_hash"], "withdrawal_decision": withdrawn["result_hash"], "withdrawal_outcome": withdrawn["status"],
        "amendment_bundle_hash": changed["bundle_hash"], "history_archive": package, "original_replay_equal": True,
        "amendment_release_hash": amended_release["release_hash"], "amendment_jar_sha256": amended_build["jar_sha256"],
        "human_usability": "PENDING", "bank_legal_approval": "PENDING", "production_bank_connection": False}
    (out / "walkthrough.json").write_bytes(canonical(result))
    (out / "local-identities.json").write_bytes(canonical(IDENTITIES))
    (out / "local-identities.json").chmod(0o600)
    return result
