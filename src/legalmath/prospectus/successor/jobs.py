"""Finite offline phase jobs; each reports its uncompleted program obligations."""
from pathlib import Path
import shutil
import subprocess
import sys
from .contracts import QUESTIONS, VERSION, digest, read, write
from .controller import REL

BASF = "docs/implementation/prospectus-basf-continuation-2026-10-05/phases/012-construct/basf-selection-admission.json"


def result(remaining, engineering="PARTIAL", evidence="PENDING_INDEPENDENT_REVIEW"):
    return {"artifact_ready": True, "engineering": engineering, "evidence": evidence, "remaining": remaining}


def p0(root, folder, state):
    baseline = root / REL / "baseline"
    if not (baseline / "manifest.json").exists():
        paths = list((root / "docs/monograph/chapters").glob("02*.tex"))
        paths += [root / ("docs/monograph/" + name) for name in
                    ("monograph.tex", "technical-companion.tex", "monograph.pdf", "technical-companion.pdf",
                     "references.bib", "appendices/prospectus-difficulty.tex")]
        paths += list((root / "docs/implementation/prospectus-delivery-program-2026-10-06").glob("*"))
        paths += [root / "docs/plans/prospectus-delivery-program-2026-10-06.md"]
        paths += [root / "docs/implementation/prospectus-evidence-closure/phases/S7/attempt-005/human-review-packet.json"]
        probe = read(root / "docs/implementation/prospectus-root-cause-2026-10-06/probes/manifest.json")
        paths += [root / p for p in probe["reader_bindings"]]
        records = {}
        for path in sorted(set(paths)):
            if path.is_file():
                relative = path.relative_to(root)
                target = baseline / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)
                records[str(relative)] = digest(path.read_bytes())
        write(baseline / "manifest.json", records)
    records = read(baseline / "manifest.json")
    for relative, expected in records.items():
        if digest((baseline / relative).read_bytes()) != expected:
            raise ValueError("Protected baseline changed")
    write(folder / "baseline.json", records)
    write(folder / "questions.json", {"version": VERSION, "questions": QUESTIONS,
        "legacy_projection": "prospectus-loss-absorption.v2; statutory disclosure included, holder-only conversion excluded"})
    protocol = {"reviewers": [], "assignment_status": "UNASSIGNED",
        "first_readings": 2, "disagreement": "third independent adjudicator or reasoned agreement",
        "blinded_to_predictions": True, "original_records_reported": 1467, "unique_spans_reported": 1307,
        "forms_reported": 25, "overlap": "NOT_YET_RECONCILED; DO_NOT_ADD_COUNTS",
        "batch_limit_unique_spans": 50, "cohort": "NOT_RESERVED; exposed retained corpus is development",
        "grouping": ["issuer", "family", "template", "source_version", "language", "layout", "time_path"],
        "release": "zero wrong supported answers and useful decidable positives/negatives in frozen finite scope",
        "automatic_risk_thresholds": None, "labels": [],
        "prohibited": "Implementer labels and recognizer replay cannot serve as independent legal truth"}
    write(folder / "reviewer-protocol.json", protocol)
    return result(["Assign independent reviewers and freeze unexposed groups",
                   "Reconcile all 1467 context records, 1307 spans and 25-form overlap"], "PARTIAL")


def basf_request(root):
    packet = read(root / BASF)
    docs = []
    for key, row in packet["sources"].items():
        receipt = root / row["acquisition_receipt"]
        meta = read(receipt)
        dates = {"basf-2032-final": "2023-03-06T00:00:00Z",
                 "basf-base-september-2022-exchange": "2022-09-09T00:00:00Z"}
        docs.append({"id": key, "path": row["original"], "sha256": row["sha256"], "format": "pdf",
            "language": "de/en", "authority": "Retained issuer/exchange copy; see acquisition receipt",
            "document_date": dates.get(key), "page_count": row["pages"],
            "known_from": meta.get("retrieved_at", meta.get("finished_at", meta.get("at"))),
            "acquisition": {"path": row["acquisition_receipt"], "sha256": digest(receipt.read_bytes())}})
    return {"version": VERSION, "bundle": {"instrument_id": "basf-senior-2032",
        "issue_date": "2023-03-08T00:00:00Z", "effective_at": "2023-03-08T00:00:00Z",
        "known_at": "2026-10-06T23:59:59Z", "purpose": "review", "documents": docs,
        "dependencies": []}, "scope": {"complete": False, "reason": "Selected contract and incorporation remain under construction"},
        "construction": {"profile": "basf-option-i", "admission_path": BASF,
                         "admission_sha256": digest((root/BASF).read_bytes())}}


def p1(root, folder, state):
    from .source_graph import build
    request = basf_request(root)
    graph = build(request["bundle"], root)
    write(folder / "request.json", request)
    write(folder / "source-graph.json", graph)
    sample = []
    for u in graph["units"]:
        if u["document"] == "basf-base-september-2022-exchange" and 108 <= u["page"] <= 133:
            sample.append(f"{u['id']} {u['bbox']} {u['raw']}")
    (folder / "german-option-i-lines.txt").write_text("\n".join(sample) + "\n")
    write(folder / "source-summary.json", {"documents": [{k: d[k] for k in ("id", "page_count", "sha256", "issues")} for d in graph["documents"]],
        "units": len(graph["units"]), "references": len(graph["references"]),
        "blank_or_unread": [u["id"] for u in graph["units"] if not u["raw"].strip()],
        "geometry_review": "PENDING; extraction is not reviewed reading order"})
    return result(["Review German margin reading order and complete source-date metadata",
                   "Extend geometry admission to seven offerings, BES17 and remaining Deutsche pages"])

def parent(root,state,phase):
    return root/state[phase]["directory"]


def p2(root,folder,state):
    from .basf import construct
    graph=read(parent(root,state,"P1")/"source-graph.json")
    candidate=construct(graph,read(root/BASF))
    write(folder/"basf-assembly.json",candidate)
    (folder/"german-option-i-candidate.txt").write_text(candidate["candidate_text"])
    write(folder/"assembly-summary.json",{"operations":len(candidate["operations"]),
        "unresolved_brackets":len(candidate["remaining_brackets"]),
        "unbalanced_offsets":candidate["unbalanced_offsets"],"rules":candidate["rules"],
        "full_german_contract_constructed":False})
    return result(candidate["remaining"]+["Construct remaining Deutsche/BES and G13–G17 agreements"])


def checks(root,folder,selection):
    # Existing application environment supplies dependencies, but code under test
    # is this checkout, explicitly recorded. P6 uses an installed package instead.
    env=__import__("os").environ.copy()
    env["PYTHONPATH"]=str(root/"src")
    env["CUDA_VISIBLE_DEVICES"]="-1"
    cmd=[str(root/".venv/bin/python"),"-m","pytest","-q","tests/prospectus_successor",
         "-k",selection,"--junitxml="+str(folder/"tests.xml")]
    run=subprocess.run(cmd,cwd=root,env=env,capture_output=True,text=True,timeout=180)
    (folder/"tests.log").write_text(run.stdout+run.stderr)
    write(folder/"test-command.json",{"argv":cmd,"environment":{"PYTHONPATH":env["PYTHONPATH"],"CUDA_VISIBLE_DEVICES":"-1"},
          "returncode":run.returncode})
    if run.returncode:raise RuntimeError("Engineering checks failed; see tests.log")
    return run.stdout


def p3(root,folder,state):
    checks(root,folder,"not dated_authority and not month_order and not no_independent_review")
    from .service import assess
    request=read(parent(root,state,"P1")/"request.json")
    report=assess(request,root)
    write(folder/"basf-report.json",report)
    return result(["Independent real-slice semantic review pending",
                   "Automatic grammar is a bounded English development baseline; German meaning remains unresolved"])


def p4(root,folder,state):
    checks(root,folder,"dated_authority")
    from ..legal_review import verify_dossier
    write(folder/"retained-law-dossier.json",verify_dossier(root))
    return result(["Admit dated primary authority for Annex2B/HETA/Dana/Lloyds/Ukraine/Popular/Snoras/Italian65/67",
                   "Supply actual forum, event, procedure and suspension facts"])


def p5(root,folder,state):
    checks(root,folder,"month_order")
    from .financial_profiles import INVENTORY
    write(folder/"financial-support.json",{"profiles":INVENTORY,
        "full_settlement_supported":False,"actual_event":"NOT_ESTABLISHED"})
    return result(["Complete source-backed rounding, calendars, adjustments, accrued amounts and delivery",
                   "Independent hand calculations and actual scenario facts pending"])


def p6(root,folder,state):
    import os
    import tempfile
    install=Path(tempfile.mkdtemp(prefix="legalmath-prospectus-installed-"))
    python=root/".venv/bin/python"
    cmd=[str(python),"-m","pip","install","--no-index","--no-deps","--no-build-isolation",
         "--target",str(install),str(root)]
    run=subprocess.run(cmd,cwd=root,capture_output=True,text=True,timeout=180)
    (folder/"install.log").write_text(run.stdout+run.stderr)
    if run.returncode:raise RuntimeError("Offline local installation failed")
    # Do not change the shared editable environment; isolated install wins.
    env={**os.environ,"PYTHONPATH":str(install),"CUDA_VISIBLE_DEVICES":"-1"}
    request=parent(root,state,"P1")/"request.json"
    cmd=[str(python),str(install/"bin/legalmath"),"prospectus","assess",
         "--request",str(request),"--repository",str(root),"--output",str(folder/"installed-report.json")]
    run=subprocess.run(cmd,cwd=install,env=env,capture_output=True,text=True,timeout=180)
    (folder/"cli.log").write_text(run.stdout+run.stderr)
    if run.returncode:raise RuntimeError("Installed assessment failed")
    installed=install/"legalmath/prospectus/successor/service.py"
    if digest(installed.read_bytes())!=digest((root/"src/legalmath/prospectus/successor/service.py").read_bytes()):
        raise ValueError("Installed package differs from worktree")
    write(folder/"installed-package.json",{"directory":str(install),"service_sha256":digest(installed.read_bytes()),
        "command":cmd,"source_path_injection":False})
    # Recompute the existing real bank investigator with unchanged obligations.
    from .. import eligibility
    from ...transaction.evidence import Store
    from .integration import investigate
    old=root/"docs/implementation/prospectus-evidence-closure/phases/S3/attempt-004/bank"
    shutil.copytree(old/"store",folder/"bank-store")
    store=Store(folder/"bank-store")
    bank_request=read(old/"request.json")
    registry=store.json(bank_request["registry_sha256"])
    from ...transaction.intake import record
    source_ids=[]
    bank_request["context"]["instrument_id"]=read(request)["bundle"]["instrument_id"]
    for doc in read(request)["bundle"]["documents"]:
        registry[doc["id"]]=record(store.put((root/doc["path"]).read_bytes()),"law",
            doc["authority"],doc.get("known_from"),media_type="application/pdf",provenance="supplied")
        source_ids.append(doc["id"])
    bank_request["registry_sha256"]=store.put(registry)
    joined={"profile":eligibility.PROFILE,"bank_request":bank_request,
        "product_assertions_sha256":store.put({}),"issuer_basis_source_ids":[],
        "prospectus_source_ids":source_ids,"contract_event_source_id":None}
    bank=investigate(read(request)["bundle"],{"request":joined,"store":store})
    write(folder/"bank-obligations.json",bank)
    complete_request=read(request)
    complete_request["bank"]={"request":joined,"store":str((folder/"bank-store").relative_to(root))}
    write(folder/"integrated-request.json",complete_request)
    cmd=[str(python),str(install/"bin/legalmath"),"prospectus","assess",
         "--request",str(folder/"integrated-request.json"),"--repository",str(root),
         "--output",str(folder/"integrated-report.json")]
    run=subprocess.run(cmd,cwd=install,env=env,capture_output=True,text=True,timeout=180)
    (folder/"integrated-cli.log").write_text(run.stdout+run.stderr)
    if run.returncode:raise RuntimeError("Installed bank integration failed")
    integrated=read(folder/"integrated-report.json")
    if len(integrated["questions"]["Q6"]["value"]["inventory"])!=14:
        raise ValueError("Installed report lost bank obligations")
    return result(["Independent acceptance of assembled real contract pending",
                   "Install/report path passed; bank facts and product-to-regulatory interpretation remain unresolved"],
                  "PARTIAL")


def p7(root,folder,state):
    from .evaluation import score
    checks(root,folder,"no_independent_review")
    evaluation=score([],[],[{"id":"reserved-cohort-pending","questions":["Q1","Q2"]}],{})
    write(folder/"evaluation.json",evaluation)
    return result(["Assign two independent first readers, adjudicator and curator",
                   "Freeze unexposed cohorts and independent labels before paired A/B/D run"],
                  "IMPLEMENTED_GUARD; EVALUATION_NOT_EXECUTED","BLOCKED_INDEPENDENT_REVIEW")


def p8(root,folder,state):
    from .release import assess
    evaluation=read(parent(root,state,"P7")/"evaluation.json")
    release=assess(evaluation,[],[])
    write(folder/"release.json",release)
    return result(release["remaining"]+["Rendered LaTeX review and human acceptance must accompany any release"],
                  "IMPLEMENTED_GUARD; RELEASE_BLOCKED","BLOCKED_INDEPENDENT_REVIEW")

