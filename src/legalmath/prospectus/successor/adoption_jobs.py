"""Bounded adoption jobs registered with the existing delivery controller."""
import importlib.metadata
import os
from pathlib import Path
import re
import sys
from .contracts import digest, read, write
from . import jobs

REL = "docs/implementation/prospectus-adoption"
BASE = "docs/implementation/prospectus-repair-2026-10-06/phases/P1/attempt-009"
OCR = "docs/prospectus/closure-2026-10-05/reviewed-extractions.json"
PLAN = "docs/plans/prospectus-adoption-execution-2026-10-07.md"


def bindings(root, phase):
    paths = [p for p in (root / "src/legalmath").rglob("*") if p.is_file() and "__pycache__" not in p.parts
             and p.suffix in {".py", ".json", ".java", ".lean"}]
    paths += list((root / "tests/prospectus_successor").glob("*.py"))
    paths += list((root / "scripts").glob("prospectus_adoption*.py"))
    paths += [root / "scripts/prospectus_delivery.py", root / "pyproject.toml", root / PLAN,
              root / jobs.BASF, root / OCR, root / jobs.INVENTORY, root / BASE / "receipt.json"]
    paths += [p for p in (root / REL / "inputs").rglob("*") if p.is_file()]
    # First attempt uses these declarations; later receipts additionally bind
    # actual inputs and their absence, including external tool identities.
    for row in read(root / jobs.BASF)["sources"].values():
        paths += [root / row[k] for k in ("original", "text", "acquisition_receipt")]
    inventory = read(root / jobs.INVENTORY)["documents"]
    from ..closure_mechanisms import PROFILES
    for profile in PROFILES.values():
        row = inventory[profile["document"]]
        paths += [root / row[k] for k in ("original", "text")]
    for row in read(root / OCR).values():
        paths += [root / row[k] for k in ("original", "raw", "text", "review", "language_model")]
    result = {str(p.relative_to(root)): digest(p.read_bytes()) for p in sorted(set(paths))}
    result["environment"] = {"python": sys.version, "packages": sorted(
        (d.metadata["Name"], d.version) for d in importlib.metadata.distributions() if d.metadata["Name"])}
    return result


def result(remaining=(), engineering="BOUNDED_ENGINEERING_PASS", **diagnostics):
    return {"artifact_ready": True, "engineering": engineering,
            "evidence": "DEVELOPMENT_ONLY; INDEPENDENT_ACCEPTANCE_PENDING", "remaining": list(remaining),
            "criteria": diagnostics, "decision": "Keep optional checked mechanisms; release not accepted"}


def phase_plan(phase, state):
    from .controller import DAG, command
    criteria = {
        "A0": "Verify original bytes, historical receipts and exact page occurrences; ambiguous printed labels remain open",
        "A1": "No raw interval disappears; shared definitions survive; unresolved uses remain visible",
        "A2": "Declared finite/Z3 corpus agrees; inconsistent premises conflict; unresolved references cannot support an answer",
        "A3": "All designated critical spans and governing attachments correct; resolve an existing baseline defect",
        "A4": "Exact derived fractions and transfers; QuantLib within 1e-12 years and dates identical",
        "A5": "Incremental equals fresh; corrupt/interrupted publications rejected; installed CLI agrees with checkout",
        "A6": "Real independent labels, frozen scope, source-bound facts and signoffs required before acceptance"}
    parents = {key: {"receipt": state.get(key, {}).get("receipt_sha256"),
                     "result": state.get(key, {}).get("engineering"),
                     "remaining": state.get(key, {}).get("remaining", [])} for key in DAG[phase]}
    return {"phase": phase, "question": "Does this mechanism close the declared engineering failure without a silent premise?",
        "primary_criterion": criteria[phase], "parents": parents, "command": command("phase", "--phase", phase),
        "promotion_veto": "Critical source/meaning loss, wrong supported answer, guessed convention or missing independence",
        "continuation_veto": "Corrupt input/comparator, invalid design, unexpected paid execution or exhausted attempt/time bound",
        "repair_trigger": "Classify and preserve failed result; amend implementation or admit changed reviewed evidence",
        "explanatory_only": ["test count", "timing", "OCR similarity", "bracket count"],
        "audit": "PASS for bounded conditional engineering; inherited unresolved legal and human premises are not silently discharged",
        "nonclaims": ["population accuracy", "full contract construction", "actual event occurrence", "native-process confinement"],
        "refresh_basis": "Exact parent receipts and unresolved premises above; acceptance criterion unchanged"}


def parent(root, state, phase, name="product.json"):
    return root / state[phase]["directory"] / name


def regression(root, folder, context, selection):
    argv = [str(root / ".venv/bin/python"), "-m", "pytest", "-q", "tests/prospectus_successor",
            "-k", selection, "--junitxml=" + str(folder / "tests.xml")]
    env = {**os.environ, "PYTHONPATH": str(root / "src"), "CUDA_VISIBLE_DEVICES": "-1"}
    run = context.tool(argv, timeout=180, env=env)
    (folder / "tests.log").write_bytes(run.stdout + run.stderr)
    write(folder / "test-command.json", {"argv": argv, "returncode": run.returncode,
          "environment": {"PYTHONPATH": env["PYTHONPATH"], "CUDA_VISIBLE_DEVICES": "-1"}})
    if run.returncode:
        raise ValueError("Focused engineering check failed; see tests.log")
    return run.stdout.decode()


def a0(root, folder, state, *, context):
    from ..closure_mechanisms import PROFILES
    context.environment("CUDA_VISIBLE_DEVICES")
    receipt = context.read_json(BASE + "/receipt.json")
    def historical(name):
        return context.read_json(BASE + "/" + name, expected=receipt["outputs"][name])
    graph = historical("source-graph.json")
    packet = context.read_json(jobs.BASF)
    inventory = context.read_json(jobs.INVENTORY)["documents"]
    docs = []
    selected = []
    requests = [(key, packet["sources"][key], pages, graph["units"]) for key, pages in (
        ("basf-base-september-2022-exchange", [112]), ("basf-supplement-february-2023-exchange", [12]))]
    for profile in PROFILES.values():
        key = profile["document"]
        layout = historical(key + "-layout.json")
        requests.append((key, inventory[key], profile["pages"], layout["units"]))
    for key, row in context.read_json(OCR).items():
        layout = historical(key + "-layout.json")
        requests.append((key, row, list(range(1, row["pages"] + 1)), layout["units"]))
        for field, sha in (("raw", "raw_sha256"), ("text", "text_sha256"), ("review", "review_sha256")):
            context.read_bytes(row[field], expected=row[sha])
        context.read_bytes(row["language_model"])
    for key, row, pages, units in requests:
        context.read_bytes(row["original"], expected=row["sha256"])
        info = context.tool(["pdfinfo", str(root / row["original"])], inputs=[row["original"]], timeout=30)
        count_match = re.search(rb"^Pages:\s+(\d+)", info.stdout, re.M)
        if info.returncode or count_match is None:
            raise ValueError("Cannot verify source PDF page count")
        page_count = int(count_match[1])
        mapping = []
        for page in pages:
            chosen = [u for u in units if u["document"] == key and u["page"] == page]
            if not chosen or page > page_count:
                raise ValueError("Frozen page has no source units: " + key + ":" + str(page))
            labels = [{"unit": u["id"], "quote": u["raw"], "bbox": u.get("bbox")} for u in chosen
                      if re.fullmatch(r"\s*\d{1,4}\s*", u["raw"]) and u.get("bbox")
                      and (u["bbox"][1] < 70 or u["bbox"][1] > 680)]
            matching = [r for r in labels if r["quote"].strip() == str(page)]
            mapping.append({"pdf_index_zero_based": page-1, "file_page_one_based": page,
                "pdf_metadata_label": None, "printed_label_candidates": labels,
                "printed_page": page if len(matching) == 1 else None,
                "verification": "MATCHED_RETAINED_PAGE_NUMBER_OCCURRENCE" if len(matching) == 1 else "UNRESOLVED_PRINTED_LABEL"})
            selected.extend(chosen)
        docs.append({"id": key, "path": row["original"], "sha256": row["sha256"],
                     "pdf_pages": page_count, "page_mapping": mapping,
                     "cohort": "EXPOSED_DEVELOPMENT", "family": "BES" if key.startswith("jur") else key.split("-")[0],
                     "template_group": "UNADJUDICATED; not eligible for heldout claims"})
    questions = [
        {"id": "basf-common-definition", "document": "basf-base-september-2022-exchange", "file_page": 112,
         "question": "Does the common Actual/Actual reference-period definition survive the unchecked optional final-terms field?",
         "expected": "RETAIN_COMMON_DEFINITION", "label_origin": "retained implementer source-image review; not independent"},
        {"id": "basf-ranges", "document": "basf-supplement-february-2023-exchange", "file_page": 12,
         "question": "Are both 195–209 and 209–290 preserved as conflicting incorporation ranges?",
         "expected": "UNRESOLVED_ALTERNATIVES", "label_origin": "retained source review; no adjudication"}]
    for profile, row in PROFILES.items():
        questions.append({"id": profile, "document": row["document"], "questions": ["Q1", "Q2", "Q5"],
                          "expected": None, "label_origin": "source-bound scenarios; independent gold absent"})
    for key in context.read_json(OCR):
        questions.append({"id": key, "document": key, "questions": ["Q3", "Q4"], "expected": None,
                          "label_origin": "reviewed transcription exists; word-to-correction and legal labels unadmitted"})
    evidence = [{"unit": u["id"], "document": u["document"], "page": u["page"], "quote": u["raw"]}
                for u in selected if u["document"].startswith("basf") and
                any(s in u["raw"] for s in ("Actual/Actual", "Bezugsperiode", "195", "209", "290", "Folgendes"))]
    write(folder / "raw-units.json", selected)
    write(folder / "questions.json", {"context": graph["context"], "questions": questions,
        "bank_issue_dates": "Not inferred from filenames; profile questions remain source-conditional",
        "reviewed_evidence_groups": evidence, "unknown_gold_is_not_negative": True})
    write(folder / "product.json", {"version": "adoption-inputs.v1", "documents": docs,
        "raw_units_sha256": digest((folder / "raw-units.json").read_bytes()), "questions": questions,
        "historical_source_graph": {"path": BASE + "/source-graph.json", "sha256": receipt["outputs"]["source-graph.json"]},
        "comparison": "Automatic raw units and reviewed transcriptions remain separate; no common independent gold yet"})
    unresolved = sum(m["printed_page"] is None for d in docs for m in d["page_mapping"])
    return result(["Admit reviewed evidence groups/labels for bank and BES pages",
                   "Resolve printed labels for " + str(unresolved) + " retained file pages before label-dependent scoring"],
                  documents=len(docs), file_pages=sum(len(d["page_mapping"]) for d in docs),
                  raw_units=len(selected), primary="SOURCE_BYTES_AND_HISTORICAL_RECEIPTS_VERIFIED",
                  printed_label_unresolved=unresolved)


def a1(root, folder, state, *, context):
    from .basf import construct
    inputs = context.read_json(str(parent(root, state, "A0").relative_to(root)))
    ref = inputs["historical_source_graph"]
    graph = context.read_json(ref["path"], expected=ref["sha256"])
    construction = construct(graph, context.read_json(jobs.BASF))
    write(folder / "product.json", construction)
    regression(root, folder, context, "ast or interval or basf or override")
    account = construction["interval_accounting"]
    if account["gaps"]:
        raise ValueError("BASF source intervals vanished without disposition")
    return result(construction["remaining"], primary="ZERO_UNACCOUNTED_BASF_BODY_INTERVALS; SHARED_DEFINITION_RETAINED",
                  unresolved_intervals=len(account["unresolved"]), bracket_count_explanatory=len(construction["remaining_brackets"]))


def a2(root, folder, state, *, context):
    regression(root, folder, context, "solver or closure or predicate or reference")
    from .predicates import solve
    large = {"all": ["fact" + str(i) for i in range(24)]}
    results = {"open": solve(large, {}), "entailed": solve(large, {"fact"+str(i): True for i in range(24)}),
               "negative": solve(large, {"fact0": False}), "conflict": solve(large, {"fact0": "conflict"})}
    write(folder / "product.json", {"version": "adoption-logic.v1", "named_large_cases": results,
                                   "scope": "Boolean constraints and conservative typed-reference closure"})
    return result(["Admit source-backed German semantic expressions and governing-reference targets"],
                  primary="DECLARED_TRUTH_TABLE_CORPUS_AND_REFERENCE_FAILURE_CHECKS_PASS")


def a3(root, folder, state, *, context):
    regression(root, folder, context, "annotation or layout")
    from .adoption_trials import layout_trial
    trial = layout_trial(root, folder, state, context)
    write(folder / "product.json", trial)
    return result(trial["remaining"], engineering=trial["engineering"], primary=trial["primary"])


def a4(root, folder, state, *, context):
    regression(root, folder, context, "coupon or financial or holder or calendar")
    from .adoption_trials import coupon_trial
    trial = coupon_trial(root, folder, state, context)
    admission = context.read_json(REL + "/inputs/A4/coupon.json", optional=True)
    if admission is not None:
        from .financial_profiles import assess
        inputs = context.read_json(str(parent(root, state, "A0").relative_to(root)))
        ref = inputs["historical_source_graph"]
        graph = context.read_json(ref["path"], expected=ref["sha256"])
        trial["admitted_coupon_result"] = assess(jobs.basf_request(root)["bundle"], admission, graph)
        if trial["admitted_coupon_result"]["status"] != "CONDITIONAL":
            trial["remaining"].append("Admitted coupon rejected: " + str(trial["admitted_coupon_result"]["unresolved"]))
    write(folder / "product.json", trial)
    return result(trial["remaining"], engineering=trial["engineering"], primary=trial["primary"])


def a5(root, folder, state, *, context):
    regression(root, folder, context, "read_context or recovery or controller or admission or published or DependencyMachine")
    import tempfile
    install = Path(tempfile.mkdtemp(prefix="legalmath-adoption-installed-"))
    command = [str(root/".venv/bin/python"), "-m", "pip", "install", "--no-index", "--no-deps", "--no-build-isolation", "--target", str(install), str(root)]
    run = context.tool(command, timeout=180, env={**os.environ, "CUDA_VISIBLE_DEVICES": "-1"})
    (folder/"install.log").write_bytes(run.stdout+run.stderr)
    if run.returncode:
        raise ValueError("Offline installed-package probe failed")
    files = {}
    for source in sorted((root/"src/legalmath").rglob("*")):
        if source.is_file() and source.suffix in {".py", ".json", ".java", ".lean"} and "__pycache__" not in source.parts:
            relative = source.relative_to(root/"src")
            expected = digest(source.read_bytes())
            if not (install/relative).is_file() or digest((install/relative).read_bytes()) != expected:
                raise ValueError("Installed package differs: " + str(relative))
            files[str(relative)] = expected
    from .acceptance import installed_semantic_checks
    installed = installed_semantic_checks(root, folder, install,
        {**os.environ, "PYTHONPATH": str(install), "CUDA_VISIBLE_DEVICES": "-1"}, root/".venv/bin/python")
    write(folder/"installed-package.json", {"command": command, "directory": str(install), "files": files,
          "checks": installed["checks"], "native_reads": "Unenforced; broad package and source hashes retained"})
    write(folder / "product.json", {"version": "adoption-dependencies.v1", "broad_bindings_retained": True,
        "native_process_confinement": False, "observed_reads": [s["directory"] + "/read-context.json" for s in state.values()],
        "test_scope": "Capability snapshots, mutations and controller recovery; see tests.xml"})
    return result(["Native imports and subprocess reads remain outside capability enforcement; keep broad bindings"],
                  primary="INCREMENTAL_EQUALITY_AND_REQUIRED_MUTATIONS_PASS")


def a6(root, folder, state, *, context):
    regression(root, folder, context, "independent or release or adjudicat or law or fact")
    registry = context.read_json(jobs.LEGAL + "/source-registry.json")
    sources = []
    for key, row in registry.items():
        bound = {}
        for field in ("original", "text"):
            if row.get(field):
                raw = context.read_bytes(row[field])
                bound[field] = {"path": row[field], "sha256": digest(raw)}
        sources.append({"id": key, "bindings": bound, "applicability": "REQUIRES_DATED_QUESTION_REVIEW"})
    review = context.read_json(REL + "/inputs/A6/review.json", optional=True)
    facts = context.read_json(REL + "/inputs/A6/facts.json", optional=True)
    evaluation_result, legal_result = {"status": "BLOCKED_INDEPENDENT_REVIEW"}, None
    if review is not None:
        from .anchors import fields
        from .evaluation import score
        required = {"cohort", "identities", "labels", "predictions", "method_sha256", "support", "signoffs", "exposure_exclusions"}
        fields(review, required, required)
        exposed = {d["id"] for d in context.read_json(str(parent(root, state, "A0").relative_to(root)))["documents"]}
        exposed.update(review["exposure_exclusions"])
        if any(c["id"] in exposed for c in review["cohort"]):
            raise ValueError("Exposed development records cannot be admitted as heldout")
        evaluation_result = score(review["predictions"], review["labels"], review["cohort"], review["identities"], review["method_sha256"])
    if facts is not None:
        from .service import source_product
        from .law_facts import assess
        for doc in facts["bundle"]["documents"]:
            context.read_bytes(doc["path"], expected=doc["sha256"])
            if doc.get("acquisition"):
                context.read_bytes(doc["acquisition"]["path"], expected=doc["acquisition"]["sha256"])
            if doc.get("ocr"):
                context.read_bytes(doc["ocr"]["path"], expected=doc["ocr"]["sha256"])
        graph = source_product(facts, root)["payload"]["graph"]
        legal_result = assess(facts["bundle"], facts.get("law_bases", []), facts.get("facts", []), graph, facts.get("law_relation"))
    from .release import assess as assess_release
    release_result = assess_release(evaluation_result, review["support"] if review else [], review["signoffs"] if review else [])
    packet = {"version": "adoption-acceptance.v1", "source_inventory": sources,
        "review_admission": review, "actual_fact_admission": facts, "development_cohort_exposed": True,
        "evaluation": evaluation_result, "legal_result": legal_result, "release_assessment": release_result,
        "required_records": ["Unexposed family cohort and frozen questions", "Two blind independent first readings",
                             "Distinct adjudicator and preserved disagreements", "Dated event/client records for actual-event questions",
                             "P7 scored predictions and P8 scope/report-bound signoffs"],
        "release": "NOT_ACCEPTED", "predictions_exposure": "Do not show development predictions to new first readers"}
    write(folder / "product.json", packet)
    write(folder / "review-request.json", {"identities": [], "cohort": [], "readings": [], "adjudication": [],
        "status": "UNASSIGNED", "recommendations": False, "premerge": False,
        "instructions": "Preserve individual readings before adjudication. Do not fill with implementer labels."})
    return result(packet["required_records"], engineering="RELEASE_PREREQUISITES_CHECKED; EXTERNAL_EVIDENCE_MISSING",
                  primary="RELEASE_REMAINS_BLOCKED", source_records=len(sources), actual_events_established=False)
