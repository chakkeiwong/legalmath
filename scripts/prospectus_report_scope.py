"""Bounded, resumable source-report cohort; retained OCR, no network or GPU."""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
from legalmath.prospectus.successor.contracts import digest
from legalmath.prospectus.successor import service

BASE = ROOT / "docs/implementation/prospectus-integration-closure"
SOURCES = BASE / "bes-original-acquisition"
HERE = BASE / "source-report-scope-2026-10-12"
PLAN = "docs/plans/prospectus-source-report-scope-2026-10-12.md"
REVIEW = {"kind": "DEVELOPMENT", "reviewer": "Codex retained-source review",
          "reason": "Matched source wording; supplied interpretation, not independent legal acceptance"}
FIELDS = ("identity", "subject", "assurance_level", "criteria", "conclusion", "addressee",
          "purpose", "reliance_limits", "translation_status", "translation_priority", "report_date",
          "publication_date", "historical_availability", "edition_authenticity")
CASES = {
    "statutory-2009": {
        "source": "language-profile/legacy-audit-001/eng/source-product.json.gz",
        "document": "bes-report-2009", "pages": [174, 175], "regions": {},
        "codes": {"identity": "STATUTORY_FINANCIAL_AUDIT", "subject": "FINANCIAL_STATEMENTS",
                  "assurance_level": "REASONABLE", "conclusion": "AFFIRMATIVE_FINANCIAL_OPINION"},
        "quotes": {
            "identity": ["AUDITORS’ REPORT CONSOLIDATED FINANCIAL STATEMENTS (ISSUED BY THE STATUTORY AUDITOR, A CMVM REGISTERED AUDITOR)"],
            "subject": ["consolidated financial statements as at and for the year ended 31 December 2009"],
            "assurance_level": ["obtain reasonable assurance about whether the consolidated financial statements are free of material misstatements."],
            "criteria": ["Technical Standards and Guidelines issued by the Portuguese Institute of Statutory Auditors", "International Financial Reporting Standards (IFRS) as adopted by the European Union, and the information contained therein is complete, true, current, clear, objective and lawful."],
            "conclusion": ["In our opinion, the consolidated financial statements referred to above present fairly in all material respects the consolidated financial position of Banco Espirito Santo, S.A. as at 31 December 2009, the consolidated results of its operations, consolidated comprehensive income, consolidated changes in equity and consolidated cash flows for the year then ended in accordance with the International Financial Reporting Standards (IFRS) as adopted by the European Union, and the information contained therein is complete, true, current, clear, objective and lawful."],
            "translation_status": ["This report is a free translation to English from the original Portuguese version"],
            "report_date": ["Lisbon, 4 March 2010"],
        },
    },
    "committee-2009": {
        "source": "coverage-expansion/review-repair-001/consumer/report.json.gz",
        "request": "coverage-expansion/review-repair-001/prepare/request.json",
        "document": "bes-report-2009", "pages": [176, 177], "regions": {},
        "codes": {"identity": "COMMITTEE_REPORT", "subject": "FINANCIAL_STATEMENTS_AND_PROFIT_APPROPRIATION",
                  "conclusion": "CONCURRENCE_WITH_AUDITORS"},
        "quotes": {
            "identity": ["REPORT OF THE AUDIT COMMITTEE FOR THE YEAR 2009"],
            "subject": ["our opinion on the Annual Report of the Board of Directors and the related unconsolidated and consolidated financial statements prepared by the Management of Banco Espirito Santo, S.A. for the year ended 31 December 2009, as well as on the related Board of Directors’ proposal for the appropriation of the unconsolidated profit for the financial year 2009."],
            "conclusion": ["Furthermore, we have reviewed the Reports of the bank’s Statutory Auditors issued on March 4, 2010, on the unconsolidated and consolidated financial statements of Banco Espirito Santo, S.A. for the year ended 31 December 2009, which contain their unqualified professional opinions, with which we concur, on those financial statements."],
            "addressee": ["To the Shareholders of Banco Espirito Santo, S.A.,"],
            "report_date": ["Lisbon, March 9, 2010"],
        },
    },
    "sustainability-2010-en": {
        "source": "reading-order/consumer-001/source-product.json.gz",
        "document": "bes-report-2010", "pages": [88, 89],
        "regions": {89: ["bes2010-p89-body", "bes2010-p89-sidebar"]},
        "codes": {"identity": "LIMITED_SUSTAINABILITY_ASSURANCE", "subject": "SUSTAINABILITY_INFORMATION",
                  "assurance_level": "LIMITED", "conclusion": "NEGATIVE_ASSURANCE"},
        "quotes": {
            "identity": ["Independent Limited Assurance Report (This Report is a free translation"],
            "subject": ["provide limited assurance on the sustainability information included in"],
            "assurance_level": ["The extent of evidence gathering procedures performed in a limited assurance engagement is less than that for a reasonable assurance engagement, and therefore a lower level of assurance is provided."],
            "criteria": ["International Standard on Assurance Engagements (ISAE) 3000", "The alignment of GBES with inclusiveness, materiality and response principles of AA1000APS (2008)", "The compliance with the Sustainability Reporting Guidelines (G3) of the Global Reporting Initiative (GRI) as described in chapter 8 “Final Notes” of the Report."],
            "conclusion": ["Based on the procedures performed, as described above, nothing has come to our attention that causes us to believe that the sustainability information included in the Report of GBES for the year ended 31 December 2010 is not presented fairly, in all material respects with:"],
            "addressee": ["To the Executive Board of Directors of Grupo Banco Espirito Santo S.A."],
            "purpose": ["Our limited assurance report is made solely to GBES in accordance with the terms of our engagement. Our work has been prepared only with the objective of stating to GBES those matters we have been engaged to state in this limited assurance report and for no other purpose."],
            "reliance_limits": ["We do not accept or assume responsibility to any third party than GBES for our work, for this limited assurance report, or for the conclusions we have reached."],
            "translation_status": ["This Report is a free translation to English from the Portuguese version"],
            "translation_priority": ["This Report is a free translation to English from the Portuguese version In case of doubt or misinterpretation the Portuguese version will prevail"],
            "report_date": ["Lisbon, 4 March 2011"],
        },
    },
    "sustainability-2010-pt": {
        "source": "portuguese-2010/region-consumer-001/source-product.json.gz",
        "document": "bes-report-2010-pt", "pages": [88, 89],
        "regions": {89: ["pt-p89-body", "pt-p89-margin"]},
        "codes": {"identity": "LIMITED_SUSTAINABILITY_ASSURANCE", "subject": "SUSTAINABILITY_INFORMATION",
                  "assurance_level": "LIMITED", "conclusion": "NEGATIVE_ASSURANCE"},
        "quotes": {
            "identity": ["RELATÓRIO INDEPENDENTE DE GARANTIA LIMITADA DE FIABILIDADE"],
            "subject": ["informação de sustentabilidade incluída no Relatório de Gestão"],
            "assurance_level": ["Os procedimentos de recolha de prova, efectuados num trabalho de garantia limitada de fiabilidade, são mais limitados do que num trabalho de garantia razoável de fiabilidade e por isso é obtida menor garantia de fiabilidade."],
            "criteria": ["ISAE 3000", "O alinhamento do GBES com os princípios de inclusividade, materialidade e resposta da norma AA 1000APS (2008)", "A sua conformidade com as Directrizes para a Elaboração de Relatórios de Sustentabilidade (“Sustainability Reporting Guidelines (G3)”) do “Global Reporting Initiative (GRI)"],
            "conclusion": ["nada chegou ao nosso conhecimento, que nos leve a concluir que a informação de sustentabilidade incluída no Relatório do GBES, para o exercício findo em 31 de Dezembro de 2010, não esteja isenta de distorções materialmente relevantes que afectem:"],
            "addressee": ["Ao Conselho de Administração Executivo do", "Grupo Banco Espírito Santo, S.A."],
            "purpose": ["é emitido unicamente para o GBES", "não se destina a ser utilizado para nenhum outro propósito."],
            "reliance_limits": ["Não aceitamos ou assumimos qualquer responsabilidade perante terceiras entidades, para além do GBES, pelo nosso trabalho, por este Relatório de garantia limitada de fiabilidade ou pelas nossas conclusões."],
            "report_date": ["Lisboa, 4 de Março de 2011"],
        },
    },
}


def read(path):
    if str(path).endswith(".gz"):
        with gzip.open(path, "rt") as stream:
            return json.load(stream)
    return json.loads(path.read_text())


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


def source(case):
    value = read(SOURCES / case["source"])
    if "request" in case:
        request = read(SOURCES / case["request"])
        if value["report_sha256"] != digest({k: v for k, v in value.items() if k != "report_sha256"}):
            raise ValueError("Retained report changed")
        graph = value["source_map"]
        if graph["bundle_sha256"] != digest(request["bundle"]):
            raise ValueError("Retained graph/request bundle mismatch")
        return service.seal("P1", request["bundle"], {"request": digest(request)},
                            {"request": request, "graph": graph})
    service.verify(value, "P1")
    return value


def oracle_reading(graph, case):
    """Independent freeze projection from complete source units or existing P1 regions."""
    chunks = []
    for page in case["pages"]:
        items = case["regions"].get(page, case["regions"].get(str(page)))
        if items:
            projection, = [p for p in graph["layout"]["projections"] if p["document"] == case["document"]]
            mappings = {m["item"]: m for m in projection["mappings"] if m["page"] == page}
            chunks.extend(mappings[item]["text"] for item in items)
        else:
            chunks.extend(u["raw"] for u in graph["units"] if u["document"] == case["document"]
                          and u["page"] == page and u["visible"])
    return "\n".join(chunks)


def span(text, quote):
    # Whitespace-only matching; no accent, negation, punctuation or case repair.
    pattern = r"\s+".join(re.escape(word) for word in quote.split())
    matches = list(re.finditer(pattern, text))
    if len(matches) != 1:
        raise ValueError(f"Expected one exact span, got {len(matches)}: {quote[:90]}")
    found = matches[0]
    return {"start": found.start(), "end": found.end(), "quote": found.group()}


def freeze(freeze_id):
    if not re.fullmatch(r"freeze-[0-9]{3}", freeze_id):
        raise ValueError("Expected freeze-NNN directory")
    directory = HERE / freeze_id
    directory.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    inputs, frozen = {}, {}
    for name, case in CASES.items():
        p1 = source(case)
        request, graph = p1["payload"]["request"], p1["payload"]["graph"]
        text = oracle_reading(graph, case)
        document, = [d for d in request["bundle"]["documents"] if d["id"] == case["document"]]
        if digest((ROOT / document["path"]).read_bytes()) != document["sha256"]:
            raise ValueError("Source bytes changed")
        facts = {}
        for field in FIELDS:
            quotes = case["quotes"].get(field, [])
            facts[field] = ({"status": "SUPPLIED", "spans": [span(text, q) for q in quotes],
                             **({"value": case["codes"][field]} if field in case["codes"] else {})}
                            if quotes else {"status": "UNKNOWN", "reason": "Not established by this retained report reading"})
        spec = {"id": name, "document": case["document"], "source_sha256": document["sha256"],
                "pages": [{"page": page, "mode": "layout", "items": case["regions"][page]}
                          if page in case["regions"] else {"page": page, "mode": "raw"}
                          for page in case["pages"]], "text_sha256": digest(text.encode())}
        frozen[name] = {"source": case["source"], **({"request": case["request"]} if "request" in case else {}),
                        "p1_sha256": p1["sha256"], "graph_sha256": digest(graph),
                        "reading": spec, "facts": facts, "expected_codes": case["codes"],
                        "source_language": document["language"]}
        write(directory / (name + ".json"), frozen[name])
        (directory / (name + ".txt")).write_text(text)
        for path in [SOURCES / case["source"], ROOT / document["path"],
                     *([SOURCES / case["request"]] if "request" in case else [])]:
            inputs[str(path.relative_to(ROOT))] = digest(path.read_bytes())
        print(json.dumps({"frozen": name, "text_chars": len(text), "supplied_facts": sum(v["status"] == "SUPPLIED" for v in facts.values())}), flush=True)
    write(directory / "result.json", {"status": "FROZEN", "cases": list(frozen), "inputs": inputs,
          "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
          "command": ".venv/bin/python -m scripts.prospectus_report_scope freeze --freeze-id " + freeze_id, "interpreter": sys.executable,
          "cpu_gpu": "CPU only; GPU intentionally hidden", "seed": "N/A; deterministic",
          "plan": PLAN, "wall_seconds": time.monotonic() - started,
          "created_utc": datetime.now(timezone.utc).isoformat(),
          "limits": "Development source review; no independent legal acceptance or new source completeness"})
    write(directory / "manifest.json", {"files": {p.name: digest(p.read_bytes()) for p in sorted(directory.iterdir()) if p.is_file()}})


def consume_case(name, freeze_id, attempt):
    from legalmath.prospectus.successor import report_scope
    if name not in CASES or not re.fullmatch(r"freeze-[0-9]{3}", freeze_id) or not re.fullmatch(r"attempt-[0-9]{3}", attempt):
        raise ValueError("Expected known case, freeze-NNN and attempt-NNN")
    frozen = HERE / freeze_id
    directory = HERE / "cases" / name / attempt
    directory.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    code_paths = list((ROOT / "src/legalmath/prospectus/successor").glob("*.py"))
    code_paths += [Path(__file__), ROOT / PLAN, ROOT / "tests/prospectus_successor/test_report_scope.py"]
    code = {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in code_paths}
    write(directory / "started.json", {
        "command": f".venv/bin/python -m scripts.prospectus_report_scope consume --case {name} --freeze-id {freeze_id} --attempt {attempt}",
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "interpreter": sys.executable, "service_module": service.__file__, "code_inputs": code,
        "cpu_gpu": "CPU only; CUDA_VISIBLE_DEVICES=-1 before application imports",
        "seeds": "N/A; deterministic retained-product replay", "plan": PLAN,
        "freeze_manifest_sha256": digest((frozen / "manifest.json").read_bytes()),
        "created_utc": datetime.now(timezone.utc).isoformat(),
    })
    stage = "verify-frozen-inputs"
    try:
        for member, expected in read(frozen / "manifest.json")["files"].items():
            if digest((frozen / member).read_bytes()) != expected:
                raise ValueError("Frozen cohort changed: " + member)
        original_inputs = read(frozen / "result.json")["inputs"]
        case = read(frozen / (name + ".json"))
        for key in ("source", "request"):
            if key in case:
                path = SOURCES / case[key]
                if digest(path.read_bytes()) != original_inputs[str(path.relative_to(ROOT))]:
                    raise ValueError("Frozen source product changed")
        p1 = source(case)
        if p1["sha256"] != case["p1_sha256"] or digest(p1["payload"]["graph"]) != case["graph_sha256"]:
            raise ValueError("Frozen P1 or graph changed")
        graph = p1["payload"]["graph"]
        stage = "baseline-consumer"
        print(json.dumps({"case": name, "stage": stage}), flush=True)
        p2 = service.construction_product(p1, ROOT)
        p3 = service.interpretation_product(p1, p2)
        baseline = service.consume({"P1": p1, "P2": p2, "P3": p3,
            "P4": service.law_product(p1, p3), "P5": service.financial_product(p1, p2, p3)}, ROOT)
        write(directory / "baseline-answer.json", baseline)
        baseline_assembly = digest(p2["payload"]["assembly"])
        baseline_dependencies = deepcopy(p3["payload"]["dependencies"])
        del p2, p3

        stage = "report-consumer"
        print(json.dumps({"case": name, "stage": stage}), flush=True)
        request = deepcopy(p1["payload"]["request"])
        reading_input = {"version": "source-report-readings.v1", "graph_sha256": digest(graph),
                         "review": REVIEW, "reports": [case["reading"]]}
        request["source_report_readings"] = reading_input
        p1 = service.seal("P1", request["bundle"], {"request": digest(request)}, {"request": request, "graph": graph})
        p2 = service.construction_product(p1, ROOT)
        selected = p2["payload"]["source_report_readings"]
        scope_input = {"version": "source-report-scope.v1", "readings_sha256": digest(selected), "review": REVIEW,
            "reports": [{"id": name, "reading_sha256": selected["reports"][0]["sha256"], "facts": case["facts"]}]}
        p3 = service.interpretation_product(p1, p2, {"source_report_scope": scope_input})
        answer = service.consume({"P1": p1, "P2": p2, "P3": p3,
            "P4": service.law_product(p1, p3), "P5": service.financial_product(p1, p2, p3)}, ROOT)
        write(directory / "reading-admission.json", reading_input)
        write(directory / "scope-admission.json", scope_input)
        write(directory / "selected-reading.json", selected)
        write(directory / "answer.json", answer)
        facts = answer["source_reports"][0]["facts"]
        checks = {"matched_questions_equal": baseline["questions"] == answer["questions"],
                  "matched_assembly_equal": baseline_assembly == digest(p2["payload"]["assembly"]),
                  "matched_dependencies_equal": baseline_dependencies == p3["payload"]["dependencies"],
                  "reviewed_codes_match": all(facts[k].get("value") == v for k, v in case["expected_codes"].items()),
                  "conditional_scope_consumed": answer["source_reports"][0]["status"] == "CONDITIONAL_SUPPLIED_READING",
                  "external_facts_unknown": all(facts[k]["status"] == "UNKNOWN" for k in report_scope.EXTERNAL),
                  "independent_acceptance_not_claimed": not answer["independent_legal_acceptance"],
                  "text_matches_frozen_reading": selected["reports"][0]["text"] == (frozen / (name + ".txt")).read_text()}

        stage = "negative-controls"
        controls = {}

        def reject(label, function, *args):
            try:
                function(*args)
            except ValueError as error:
                controls[label] = {"status": "REJECTED", "reason": str(error)}
                return
            raise AssertionError("Corruption accepted: " + label)

        for label in ("stale_graph", "different_edition", "changed_text"):
            bad = deepcopy(reading_input)
            if label == "stale_graph":
                bad["graph_sha256"] = "0" * 64
            else:
                bad["reports"][0]["source_sha256" if label == "different_edition" else "text_sha256"] = "0" * 64
            reject(label, report_scope.readings, graph, bad)
        for label in ("changed_quote", "subject_swap", "missing_qualification", "changed_report_date", "promoted_publication_date", "stale_reading"):
            bad = deepcopy(scope_input)
            row = bad["reports"][0]
            if label == "changed_quote":
                row["facts"]["conclusion"]["spans"][0]["quote"] += " invented"
            elif label == "subject_swap":
                row["facts"]["subject"]["value"] = ("FINANCIAL_STATEMENTS" if case["expected_codes"]["subject"] != "FINANCIAL_STATEMENTS" else "SUSTAINABILITY_INFORMATION")
            elif label == "missing_qualification":
                del row["facts"]["reliance_limits"]
            elif label == "changed_report_date":
                row["facts"]["report_date"]["spans"][0]["quote"] = "1 January 2000"
            elif label == "promoted_publication_date":
                row["facts"]["publication_date"] = deepcopy(row["facts"]["report_date"])
            else:
                row["reading_sha256"] = "0" * 64
            reject(label, report_scope.admit, selected, bad)
        if any(p["mode"] == "layout" for p in case["reading"]["pages"]):
            for label in ("drop_margin", "reverse_regions"):
                bad = deepcopy(reading_input)
                page = next(p for p in bad["reports"][0]["pages"] if p["mode"] == "layout")
                if label == "drop_margin":
                    page["items"].pop()
                else:
                    page["items"].reverse()
                reject(label, report_scope.readings, graph, bad)
        incomplete = deepcopy(scope_input)
        incomplete["reports"][0]["facts"]["conclusion"] = {"status": "UNKNOWN", "reason": "Negative-control missing conclusion"}
        response, = report_scope.explain(report_scope.admit(selected, incomplete))
        checks["explicit_unknown_withholds_complete_scope"] = response["status"] == "INCOMPLETE_SOURCE_READING"
        checks["code_unchanged_during_run"] = all(digest((ROOT / path).read_bytes()) == sha for path, sha in code.items())
        write(directory / "controls.json", controls)
        write(directory / "dependencies.json", p3["payload"]["dependencies"])
        result = {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
                  "case": name, "negative_controls": len(controls),
                  "question_statuses": {q: value["status"] for q, value in answer["questions"].items()},
                  "original_dependencies": request["bundle"].get("dependencies", []),
                  "reading_sha256": selected["reports"][0]["sha256"],
                  "limits": "Supplied development reading; no legal truth, source-completeness or package suitability verdict"}
    except Exception as error:
        (directory / "error.log").write_text(traceback.format_exc())
        result = {"status": "FAIL", "case": name, "stage": stage, "error": str(error), "type": type(error).__name__}
    result["wall_seconds"] = time.monotonic() - started
    write(directory / "result.json", result)
    write(directory / "manifest.json", {"files": {p.name: digest(p.read_bytes()) for p in sorted(directory.iterdir()) if p.is_file()}})
    print(json.dumps({k: result[k] for k in ("status", "case", "negative_controls", "stage", "error", "wall_seconds") if k in result}), flush=True)
    return 0 if result["status"] == "PASS" else 1


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("action", choices=["freeze", "consume"])
    parser.add_argument("--freeze-id", default="freeze-001")
    parser.add_argument("--case", choices=CASES)
    parser.add_argument("--attempt", default="attempt-001")
    args = parser.parse_args()
    if args.action == "freeze":
        freeze(args.freeze_id)
    else:
        raise SystemExit(consume_case(args.case, args.freeze_id, args.attempt))


if __name__ == "__main__":
    main()
