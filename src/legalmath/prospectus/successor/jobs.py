"""Finite offline phase jobs; each reports its uncompleted program obligations."""
from pathlib import Path
import shutil
import subprocess
import sys
from .contracts import QUESTIONS, VERSION, digest, read, write
from .controller import REL

BASF = "docs/implementation/prospectus-basf-continuation-2026-10-05/phases/012-construct/basf-selection-admission.json"
LEGAL = "docs/implementation/prospectus-corner-repair-2026-10-04/phases/018-legal"
INVENTORY = "docs/implementation/prospectus-evidence-closure/phases/S1/attempt-007/inventory.json"
GROUPS = "docs/implementation/prospectus-evidence-closure/phases/S4/attempt-004/clause-groups.json"
FORMS = "docs/implementation/prospectus-closure-2026-10-05/independent-review"


def admitted(root, phase, name, default):
    path = root / REL / "inputs" / phase / name
    return read(path) if path.exists() else default


def product(root, state, phase):
    return read(parent(root, state, phase) / "product.json")


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
    forms = [read(p) for p in sorted((root / FORMS).glob("CC*.json"))]
    groups = read(root / GROUPS)
    occurrences = []
    for group in groups:
        for binding in group["bindings"]:
            e = binding["evidence"]
            occurrences.append({"span_id":group["id"],"instrument_id":binding["issue_id"],
                                "document":e["document"],"source_sha256":e["source_sha256"],
                                "start":e["start"],"end":e["end"],"questions":["Q1","Q2"],
                                "question_mapping":"legacy feature scope; not independent labels"})
    links=[]
    for form in forms:
        hashes={a["source_sha256"] for a in form["source_rule_and_context"]["rule"]["anchors"]}
        links.append({"case":form["case"],"source_editions":sorted(hashes),
                      "candidate_spans_same_edition":sorted({o["span_id"] for o in occurrences if o["source_sha256"] in hashes}),
                      "status":"EDITION_LINK_ONLY; questions and instrument applicability require adjudication",
                      "adjudication":form["adjudication"]["status"]})
    write(folder / "occurrence-reconciliation.json", {"span_groups":len(groups),"instrument_contexts":len(occurrences),
          "forms":len(forms),"occurrences":occurrences,"form_links":links,
          "counts_are_additive":False,"form_question_overlap":"UNADJUDICATED"})
    review = admitted(root,"P0","review.json",{"identities":{},"cohort":[],"exposure_exclusions":[]})
    if set(review) != {"identities","cohort","exposure_exclusions"}:
        raise ValueError("Review admission requires identities, frozen cohort and exposure exclusions")
    if {c["id"] for c in review["cohort"]}.intersection(review["exposure_exclusions"]):
        raise ValueError("Exposed cases cannot be admitted as heldout")
    write(folder / "review-admission.json", review)
    return result(["Assign independent reviewers and freeze unexposed groups",
                   "Adjudicate question/instrument overlap after preserving all context-to-span and form-to-edition links"], "PARTIAL")


def basf_request(root):
    packet = read(root / BASF)
    docs = []
    for key, row in packet["sources"].items():
        receipt = root / row["acquisition_receipt"]
        meta = read(receipt)
        dates = {"basf-2032-final": "2023-03-06T00:00:00Z",
                 "basf-base-september-2022-exchange": "2022-09-09T00:00:00Z",
                 "basf-supplement-february-2023-exchange": "2023-02-27T00:00:00Z",
                 "basf-annual-2022-exchange": "2023-02-24T00:00:00Z"}
        docs.append({"id": key, "path": row["original"], "sha256": row["sha256"], "format": "pdf",
            "language": "de/en", "authority": "Retained issuer/exchange copy; see acquisition receipt",
            "document_date": dates.get(key), "page_count": row["pages"],
            "known_from": meta.get("retrieved_at", meta.get("finished_at", meta.get("at"))),
            "acquisition": {"path": row["acquisition_receipt"], "sha256": digest(receipt.read_bytes())}})
    return {"version": VERSION, "bundle": {"instrument_id": "basf-senior-2032",
        "issue_date": "2023-03-08T00:00:00Z", "effective_at": "2023-03-08T00:00:00Z",
        "known_at": "2026-10-06T23:59:59Z", "purpose": "review", "documents": docs,
        "dependencies": []}, "scope": {q:{"complete":False,"reason":"Selected contract and incorporation remain under construction"} for q in ("Q1","Q2","Q4","Q5","Q6")},
        "construction": {"profile": "basf-option-i", "admission_path": BASF,
                         "admission_sha256": digest((root/BASF).read_bytes())}}


def p1(root, folder, state):
    from .service import source_product
    request = admitted(root,"P1","request.json",basf_request(root))
    p = source_product(request, root)
    graph = p["payload"]["graph"]
    write(folder / "product.json",p)
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
    from .source_graph import retained_ocr_units, pdf_units
    from ..closure_mechanisms import PROFILES
    layouts=[]
    retained=read(root/"docs/prospectus/closure-2026-10-05/reviewed-extractions.json")
    for key,meta in retained.items():
        if any(digest((root/meta[key]).read_bytes())!=meta[sha]
               for key,sha in (("original","sha256"),("review","review_sha256"),("text","text_sha256"))):
            raise ValueError("Retained scan/review changed")
        doc={"id":key,"sha256":meta["sha256"],"language":"en","ocr":{"path":meta["raw"],"sha256":meta["raw_sha256"]}}
        units,count,extraction=retained_ocr_units(doc,root)
        if digest((root/meta["language_model"]).read_bytes())!=extraction["runtime"]["language_sha256"]:
            raise ValueError("Retained OCR language model changed")
        write(folder/(key+"-layout.json"),{"units":units,"extraction":extraction})
        layout={"document":key,"source_sha256":meta["sha256"],"pages":count,"units":len(units),
                "words":sum(len(u.get("words",[])) for u in units),"raw_extraction":extraction,
                "reviewed_transcription":{"path":meta["text"],"sha256":meta["text_sha256"]},
                "original_review":{"path":meta["review"],"sha256":meta["review_sha256"]},
                "unresolved":"Attach reviewed row/identifier corrections to word geometry before automatic interpretation"}
        layouts.append(layout)
    inventory=read(root/INVENTORY)["documents"]
    for profile in PROFILES.values():
        doc=inventory[profile["document"]]
        units,count,extraction=pdf_units(root/doc["original"],{**doc,"language":"de/en" if "deutsche" in doc["id"] else "en"})
        chosen=[u for u in units if u["page"] in profile["pages"]]
        write(folder/(doc["id"]+"-layout.json"),{"units":chosen,"extraction":extraction})
        layouts.append({"document":doc["id"],"pages":count,"source_sha256":doc["sha256"],
                        "inspected_profile_pages":profile["pages"],"units":len(chosen),
                        "status":"RAW_WORD_GEOMETRY_PRESERVED; bilingual/column order remains reviewable"})
    write(folder/"layout-admission.json",layouts)
    return result(["Review German margin reading order; source dates now recovered from supplement p1 and annual report p296",
                   "Admit reviewed row/column order for seven retained documents; OCR raw geometry and corrected transcriptions retained separately"])

def parent(root,state,phase):
    return root/state[phase]["directory"]


def p2(root,folder,state):
    from .service import construction_product, seal
    from .contract_assembly import assemble
    p1=product(root,state,"P1")
    p=construction_product(p1,root)
    override=admitted(root,"P2","assembly.json",None)
    if override is not None:
        p=seal("P2",p1["payload"]["request"]["bundle"],{"P1":p1["sha256"]},
               {"assembly":assemble(p1["payload"]["graph"],override),"selected_contract":None})
    write(folder/"product.json",p)
    candidate=p["payload"]["selected_contract"]
    if candidate is None:
        return result(p["payload"]["assembly"]["unresolved"])
    mapped = candidate["character_map"]
    if "".join(candidate["candidate_text"][m["start"]:m["end"]] for m in mapped) != candidate["candidate_text"]:
        raise ValueError("Selected contract character map does not cover its output")
    if any(candidate["candidate_text"][m["start"]:m["end"]] != candidate["raw_body"][m["raw_start"]:m["raw_end"]]
           for m in mapped if m["operation"] == "COPY"):
        raise ValueError("Copied contract characters differ from source")
    write(folder/"basf-assembly.json",candidate)
    (folder/"german-option-i-candidate.txt").write_text(candidate["candidate_text"])
    write(folder/"assembly-summary.json",{"operations":len(candidate["operations"]),
        "unresolved_brackets":len(candidate["remaining_brackets"]),
        "unbalanced_offsets":candidate["unbalanced_offsets"],"rules":candidate["rules"],
        "character_map_check":"PASS; copy intervals and substituted source bases retained",
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
    from .service import interpretation_product
    p=interpretation_product(product(root,state,"P1"),product(root,state,"P2"),
                             admitted(root,"P3","interpretation.json",None))
    write(folder/"product.json",p)
    write(folder/"question-summary.json",{q:{"status":v["status"],"unresolved_count":len(v["unresolved"])} for q,v in p["payload"]["questions"].items()})
    return result(["Independent real-slice semantic review pending",
                   "Automatic grammar is a bounded English development baseline; German meaning remains unresolved"])


def p4(root,folder,state):
    checks(root,folder,"dated_authority")
    from ..legal_review import verify_dossier
    write(folder/"retained-law-dossier.json",verify_dossier(root))
    from .cases import law_cases
    from .service import law_product
    rows=law_cases(root,admitted(root,"P4","cases.json",None))
    write(folder/"law-cases.json",rows)
    write(folder/"product.json",law_product(product(root,state,"P1"),product(root,state,"P3"),rows,
                                           admitted(root,"P4","law.json",None)))
    return result(["Review rule translations and effective law editions for the 25 retained hypothetical cases",
                   "Supply actual forum, event, procedure and suspension facts"])


def p5(root,folder,state):
    checks(root,folder,"month_order")
    from .financial_profiles import INVENTORY as financial_inventory
    from .cases import financial_cases
    from .service import financial_product
    rows=financial_cases(root,admitted(root,"P5","scenarios.json",None))
    write(folder/"financial-cases.json",rows)
    write(folder/"product.json",financial_product(product(root,state,"P1"),product(root,state,"P2"),product(root,state,"P3"),rows,
                                                 admitted(root,"P5","scenario.json",None)))
    write(folder/"financial-support.json",{"profiles":financial_inventory,
        "full_settlement_supported":False,"actual_event":"NOT_ESTABLISHED"})
    return result(["Complete source-backed rounding, calendars, adjustments, accrued amounts and delivery",
                   "Independent hand calculations and actual scenario facts pending"])


def p6(root,folder,state):
    import os
    import tempfile
    from copy import deepcopy
    from .service import consume
    from .. import eligibility
    from ...transaction.evidence import Store
    from ...transaction.intake import record
    from ...transaction.catalog import inventory
    from .integration import context_identity
    install=Path(tempfile.mkdtemp(prefix="legalmath-prospectus-installed-"))
    python=root/".venv/bin/python"
    command=[str(python),"-m","pip","install","--no-index","--no-deps","--no-build-isolation",
             "--target",str(install),str(root)]
    run=subprocess.run(command,cwd=root,capture_output=True,text=True,timeout=180)
    (folder/"install.log").write_text(run.stdout+run.stderr)
    if run.returncode:
        raise RuntimeError("Offline local installation failed")
    env={**os.environ,"PYTHONPATH":str(install),"CUDA_VISIBLE_DEVICES":"-1"}
    package={}
    for source in sorted(p for p in (root/"src/legalmath").rglob("*") if p.is_file() and p.suffix in {".py", ".java", ".json", ".lean"}):
        relative=source.relative_to(root/"src")
        installed=install/relative
        if not installed.is_file() or digest(source.read_bytes())!=digest(installed.read_bytes()):
            raise ValueError("Installed package differs from worktree: "+str(relative))
        package[str(relative)]=digest(installed.read_bytes())
    write(folder/"installed-package.json",{"files":package,"install_command":command,"directory":str(install),
                                         "source_path_injection":False})
    products={phase:product(root,state,phase) for phase in ("P1","P2","P3","P4","P5")}
    request=products["P1"]["payload"]["request"];bundle=request["bundle"]
    graph=products["P1"]["payload"]["graph"]
    manifest={"products":{phase:{"path":str((parent(root,state,phase)/"product.json").relative_to(root)),
                                "sha256":digest((parent(root,state,phase)/"product.json").read_bytes())}
                          for phase in products}}
    old=root/"docs/implementation/prospectus-evidence-closure/phases/S3/attempt-004/bank"
    shutil.copytree(old/"store",folder/"bank-store")
    store=Store(folder/"bank-store")
    prior=read(old/"request.json")
    registry=store.json(prior["registry_sha256"])
    source_ids=[]
    for doc in bundle["documents"]:
        registry[doc["id"]]=record(store.put((root/doc["path"]).read_bytes()),"law",doc["authority"],
                                  doc.get("known_from"),media_type="application/pdf",provenance="supplied")
        source_ids.append(doc["id"])
    # A new explicit hypothetical purchase context. Actual client/entity/capacity
    # facts remain unknown; the old prospectus and its AT1 kind are not transferred.
    context={"action":"buy","booking_entity_id":"not-established","client_id":"not-supplied",
             "establishment_id":"hk-not-established","instrument_id":bundle["instrument_id"],
             "instrument_kind":"senior_bond","service":"purchase-investigation",
             "effective_at":bundle["known_at"],"known_at":bundle["known_at"],
             "facts_sha256":store.put({}),"policy_sha256":prior["context"]["policy_sha256"],
             "route_sha256":prior["context"]["route_sha256"]}
    bank_request={"profile":prior["profile"],"capacity":"unresolved","context":context,"registry_sha256":store.put(registry)}
    joined={"profile":eligibility.PROFILE,"bank_request":bank_request,"product_assertions_sha256":store.put({}),
            "issuer_basis_source_ids":[],"prospectus_source_ids":source_ids,"contract_event_source_id":None}
    units=[u for u in graph["units"] if u["document"]=="basf-base-september-2022-exchange" and u["page"]==110
           and u["bbox"] and 495<=u["bbox"][1]<=539]
    if not units:
        raise ValueError("Senior status clause missing from context source")
    anchors=[{"unit":u["id"],"document":u["document"],"source_sha256":u["source_sha256"],
              "start":0,"end":len(u["raw"]),"quote":u["raw"]} for u in units]
    admission={"bundle_context_sha256":digest(context_identity(bundle)),"bank_context_sha256":digest(context),
               "instrument_kind":"senior_bond","sources":anchors,
               "reason":"Hypothetical current purchase investigation of the BASF 2032 senior notes; contractual terms assessed at issue date using retained knowledge. Later amendments and actual client facts remain unresolved."}
    bank=admitted(root,"P6","bank.json",{"request":joined,"store":str((folder/"bank-store").relative_to(root)),
                                       "context_admission":admission})
    manifest["bank"]=bank
    write(folder/"products.json",manifest)
    command=[str(python),str(install/"bin/legalmath"),"prospectus","consume","--products",str(folder/"products.json"),
             "--repository",str(root),"--output",str(folder/"integrated-report.json")]
    run=subprocess.run(command,cwd=install,env=env,capture_output=True,text=True,timeout=180)
    (folder/"integrated-cli.log").write_text(run.stdout+run.stderr)
    if run.returncode:
        raise RuntimeError("Installed phase consumer failed; see integrated-cli.log")
    integrated=read(folder/"integrated-report.json")
    expected=consume(products,root,{**bank,"store":Store(root/bank["store"])})
    if integrated!=expected or integrated["questions"]["Q6"]["value"]["inventory"]!=inventory(bank["request"]["bank_request"]["profile"]):
        raise ValueError("Installed product consumer or obligation inventory differs")
    # Mutate each sealed input through the real installed CLI. Each must be rejected.
    checks=[]
    for phase in products:
        changed=deepcopy(products[phase]);changed["payload"]["tampered"]=True
        path=folder/("mutated-"+phase+".json");write(path,changed)
        candidate=deepcopy(manifest)
        candidate["products"][phase]={"path":str(path.relative_to(root)),"sha256":digest(path.read_bytes())}
        manifest_path=folder/("mutation-"+phase+".json");write(manifest_path,candidate)
        argv=[str(python),str(install/"bin/legalmath"),"prospectus","consume","--products",str(manifest_path),
              "--repository",str(root),"--output",str(folder/("unexpected-"+phase+".json"))]
        bad=subprocess.run(argv,cwd=install,env=env,capture_output=True,text=True,timeout=180)
        (folder/("mutation-"+phase+".log")).write_text(bad.stdout+bad.stderr)
        if bad.returncode==0 or "Phase product content changed" not in bad.stdout+bad.stderr:
            raise ValueError("Installed CLI accepted mutation: "+phase)
        checks.append({"phase":phase,"mutation":"payload changed while recorded product identity retained","outcome":"REJECTED"})
    write(folder/"installed-consumption-checks.json",{"command":command,"checks":checks,
            "exact_report_equality":True,"consumed_products":integrated["consumed_products"],"inventory":inventory(prior["profile"])})
    from .acceptance import installed_semantic_checks
    installed_semantic_checks(root,folder,install,env,python)
    return result(["Independent acceptance of assembled real contract pending",
                   "Actual client/bank facts and product-to-regulatory interpretation unresolved"],
                  "INSTALLED_PRODUCT_CONSUMPTION_PASS")


def p7(root,folder,state):
    from .evaluation import score
    checks(root,folder,"no_independent_review")
    review=read(parent(root,state,"P0")/"review-admission.json")
    cohort=review["cohort"]
    evaluation=score(admitted(root,"P7","predictions.json",[]),admitted(root,"P7","labels.json",[]),
                     cohort,review["identities"],state["P6"]["method"]) if cohort else {
                         "status":"BLOCKED_INDEPENDENT_REVIEW","scores":None,"reason":"No frozen unexposed cohort supplied"}
    write(folder/"evaluation.json",evaluation)
    if evaluation["status"] == "FINITE_DESCRIPTIVE_ONLY":
        return result(["Review finite error counts and bind accepted support scope and sign-offs"],
                      "FINITE_EVALUATION_EXECUTED",evaluation["status"])
    return result(["Assign two independent first readers, adjudicator and curator",
                   "Freeze unexposed cohorts and independent labels before paired A/B/D run"],
                  "IMPLEMENTED_GUARD; EVALUATION_NOT_EXECUTED","BLOCKED_INDEPENDENT_REVIEW")


def p8(root,folder,state):
    from .release import assess
    evaluation=read(parent(root,state,"P7")/"evaluation.json")
    release=assess(evaluation,admitted(root,"P8","support.json",[]),admitted(root,"P8","signoffs.json",[]))
    write(folder/"release.json",release)
    return result(release["remaining"]+["Rendered LaTeX review and human acceptance must accompany any release"],
                  "IMPLEMENTED_GUARD; RELEASE_BLOCKED","BLOCKED_INDEPENDENT_REVIEW")
