"""Product-record adapters and discriminating external-engine controls."""
from copy import deepcopy
from dataclasses import asdict
import re
import shutil
from scripts.legal_gap_program import ROOT, OLD, OUT, DOC, RES, read, save, ref, command, worker, repair


def validate_graph(case):
    ids = case["ids"]
    if len(ids) != len(set(ids)) or len(ids) > 8:
        raise ValueError("Graph requires unique identities and at most eight arguments")
    if any(len(edge) != 2 or not set(edge) <= set(ids) for edge in case["attacks"]):
        raise ValueError("Unknown graph endpoint")


def graph_trial(folder):
    from legalmath.interpretation.semantics.arguments import Argument, Attack, Theory, evaluate
    source = ROOT / "artifacts/legal-interpretation-program/2026-10-06-offline-v1/P3/attempt-4/graph.json"
    raw = read(source)
    original = {"id": "product-retained", "ids": [a["id"] for a in raw["arguments"]],
                "attacks": [[a["source"], a["target"]] for a in raw["attacks"]]}
    original["attacks"] = sorted([list(e) for e in {tuple(e) for e in original["attacks"]}])
    cases = [original]
    for a in original["ids"]:
        for b in original["ids"]:
            case = deepcopy(original)
            case["id"] = "toggle-" + str(len(cases))
            edge = [a, b]
            if edge in case["attacks"]:
                case["attacks"].remove(edge)
            else:
                case["attacks"].append(edge)
            cases.append(case)
    for case in cases:
        validate_graph(case)
        theory = Theory(tuple(Argument(i, i) for i in case["ids"]),
                        tuple(Attack(a, b, "rebuttal", b) for a, b in case["attacks"]))
        case["expected"] = {}
        for semantics in ("grounded", "preferred"):
            result = evaluate(theory, semantics)
            if result.completion != "complete":
                raise ValueError("Local graph comparator incomplete")
            case["expected"][semantics] = [list(e) for e in result.extensions]
    pyarg = worker("pyarg", {"cases": cases}, folder / "pyarg")
    native = folder / "carneades"
    native.mkdir(parents=True)
    save(native / "input.json", {"cases": cases})
    command([OLD / "T2/attempt-1/carneades-adapter/trial", native / "input.json", native / "output.json"], native, "carneades")
    carneades = read(native / "output.json")
    differences = []
    expected = {c["id"]: c["expected"] for c in cases}
    for name, result in (("pyarg", pyarg), ("carneades", carneades)):
        if {r["id"] for r in result["cases"]} != set(expected):
            raise ValueError("External solver omitted a graph")
        for row in result["cases"]:
            if any(row[s] != expected[row["id"]][s] for s in ("grounded", "preferred")):
                differences.append({"tool": name, "id": row["id"]})
    save(folder / "cases.json", cases)
    changed = sum(c["expected"] != cases[0]["expected"] for c in cases[1:])
    return {"status": "PASS" if not differences else "FAILED", "source": ref(source),
            "cases": len(cases), "attack_changes_affecting_extensions": changed,
            "differences": differences, "original_result": pyarg["cases"][0],
            "raw": [ref(folder / "pyarg/output.json"), ref(native / "output.json")],
            "limit": "Graph fidelity under declared semantics; source warrants and priorities remain unproved"}


def rule_trial(folder):
    from scripts.legal_interpretation_s2_data import packet, inventory
    _, standards = inventory(packet())
    rows = [{"id": r.id, "requirements": [q.model_dump(mode="json") for q in r.requirements],
             "modality": r.modality, "consequence": r.consequence,
             "sources": ["urn:legalmath:source:" + s.unit_id + ":" + s.unit_hash for s in r.sources]} for r in standards]
    result = worker("interchange", {"rules": rows}, folder)
    (folder / "rules.lrml").write_text(result.pop("xml"))
    result.update(standards=len(rows), supported_fields=list(rows[0]),
        unsupported_fields=["warrant truth", "full temporal/scope semantics", "deontic force of SHOULD", "unformalized readings"],
        limit="Native constitutive atoms encode conditional propositions, not established deontic duties; full product meanings are not certified")
    save(folder / "input-standards.json", [r.model_dump(mode="json") for r in standards])
    from scripts.legal_interpretation_s3_data import projection, reading
    from legalmath.translation.expressions import expression
    _, source, *_ = projection()
    live_readings = [reading(source, letter) for letter in ("A", "B", "C")]
    boolean = worker("boolean", {"readings": [{"id": r["local_id"],
        "scope": expression(r["formalization"]["scope"], "scope"),
        "result": expression(r["formalization"]["result"], "result")} for r in live_readings]}, folder / "product-readings")
    result["product_boolean_roundtrip"] = boolean
    return result


def retrieval_trial(folder, corpus, questions, targets):
    units = {u["id"]: u["text"] for u in corpus["units"]}
    for rows in targets.values():
        for target in rows:
            if target["quote"] not in units[target["unit_id"]]:
                raise ValueError("Invalid predeclared retrieval target")
    result = worker("retrieval", {"corpus": corpus, "questions": questions, "targets": targets}, folder)
    for row in result["rows"]:
        for passage in row["passages"]:
            if units[passage["unit_id"]][passage["start"]:passage["end"]] != passage["text"]:
                raise ValueError("Retrieval changed source identity or offsets")
    result["source_identity"] = "CHECKED"
    return result


PROLOG = r'''
:- op(800, fx, user:(<-)).
:- use_module(library(http/json)).
:- use_module(library(readutil)).
:- initialization(main, main).
main :-
 current_prolog_flag(argv, [Module, Input, Output]),
 use_module(Module), read_file_to_string(Input, Text, []), atom_string(Atom, Text),
 le_input:clear_errors,
 catch((le_input:text_to_logic(Atom, Translation) -> Success=true ; Success=false, Translation=[]),
       Exception, (Success=false, Translation=[], term_string(Exception, ExceptionText))),
 findall(S, (le_input:error_notice(A,B,C,D), term_string(error_notice(A,B,C,D), S)), Errors),
 copy_term(Translation, Stable), numbervars(Stable, 0, _),
 term_string(Stable, Terms, [quoted(true), numbervars(true)]),
 findall(C, (member(if(_, H, B), Translation), copy_term((H:-B), Clause),
             numbervars(Clause, 0, _), term_string(Clause, C, [quoted(true), numbervars(true)])), Clauses),
 (var(ExceptionText) -> ExceptionText="" ; true),
 open(Output, write, Stream),
 json_write_dict(Stream, _{parsed:Success, errors:Errors, exception:ExceptionText, translation:Terms, clauses:Clauses}),
 close(Stream).
'''


def le_trial(folder):
    folder.mkdir(parents=True)
    pin = read(RES / "logical-english.json")
    source = ROOT / pin["source"]
    adapter = folder / "parse.pl"
    adapter.write_text(PROLOG)
    texts = {
        "author-example": (source / "kb/tutorial01.le").read_text(),
        "old-positive": (OLD / "logical-english-repair/logical-english/proposed-p14.le").read_text(),
        "malformed": "the templates are: @@@ invalid syntax",
    }
    texts["changed-trigger"] = texts["old-positive"].replace("    if SFC requests the assurance from the custodian.", ".")
    env = {"SWI_HOME_DIR": str(RES / "swipl/usr/lib/swi-prolog"), "LD_LIBRARY_PATH": str(RES / "swipl/usr/lib")}
    def trial(directory, module):
        directory.mkdir(exist_ok=True)
        results = {}
        for name, content in texts.items():
            inp, out = directory / (name + ".le"), directory / (name + ".json")
            inp.write_text(content)
            command([RES / "swipl/usr/bin/swipl", "-q", "-f", "none", "-s", adapter,
                     "--", module, inp, out], directory, name, env=env, timeout=40)
            row = read(out)
            row["load_errors"] = [line for line in (directory / (name + ".log")).read_text().splitlines() if line.startswith("ERROR:")]
            row["accepted"] = row["parsed"] and not row["errors"] and not row["exception"] and not row["load_errors"]
            results[name] = row
        save(directory / "controls.json", results)
        return results
    before = trial(folder / "original", source / "le_input.pl")
    final = before
    patched = False
    if not before["author-example"]["accepted"] or not before["old-positive"]["accepted"]:
        repair("LE settings attempts declaration at a valid section boundary and retains its backtracking error; test a boundary lookahead on a local copy", ref(folder / "original/controls.json"))
        copied = folder / "patched-source"
        shutil.copytree(source, copied)
        path = copied / "le_input.pl"
        text = path.read_text()
        anchor = "settings(AllR, AllS) -->"
        guard = ("settings([], [], Stay, Stay) :-\n"
                 "    ( phrase(rules_previous(_), Stay, _) ; phrase(ontology_, Stay, _) ;\n"
                 "      phrase(scenario_, Stay, _) ; phrase(query_, Stay, _) ;\n"
                 "      phrase(the_plots_are_, Stay, _) ), !.\n")
        if text.count(anchor) != 1:
            raise ValueError("Pinned LE parser changed")
        path.write_text(text.replace(anchor, guard + anchor, 1))
        final = trial(folder / "repaired", path)
        patched = True
    passed = all(final[n]["accepted"] for n in ("author-example", "old-positive", "changed-trigger")) and not final["malformed"]["accepted"]
    trigger_preserved = final["old-positive"]["clauses"] != final["changed-trigger"]["clauses"]
    return {"status": "PASS" if passed and trigger_preserved else "FAILED_CONTROLS",
            "original": before, "final": final, "local_copy_patch": patched,
            "changed_trigger_detected": trigger_preserved,
            "limit": "Controlled authored conditional only; source-to-rule equivalence and execution of all readings untested"}


def case_trial(folder):
    from scripts.legal_interpretation_s2_cases import build
    from legalmath.interpretation.semantics.precedent import JudgmentManifest, Proposition, Authority, Treatment, assess_authority
    from legalmath.interpretation.semantics.records import Interval
    value = build()
    rows = []
    for case in value["cases"]:
        manifest = JudgmentManifest(**case["manifest"])
        proposition = Proposition(**case["propositions"][0])
        authority = Authority(proposition.proposition_id, "HK", "Court of First Instance", None, None,
                              Interval(start=None, end=None), ("target-applicability",), "unknown")
        for label, treatments in (("unverified-treatment", []),
             ("overruled-control", [Treatment(manifest.judgment_id, "synthetic-later", "overruled", ("synthetic",), "2026-01-01", "source-backed")])):
            result = assess_authority(manifest, proposition, authority, treatments, "2026-10-08")
            rows.append({"case": manifest.judgment_id, "control": label, "result": result})
    save(folder / "case-records.json", value)
    return {"status": "BOUNDARIES_CHECKED", "controls": rows,
            "source_checks": [c["source_check"] for c in value["cases"]],
            "unresolved_text_tension": value["unresolved_text_tension"],
            "unimplemented_target_tests": ["absent-consent target classifier", "changed-terms target classifier", "different-relationship target classifier"],
            "limit": "Existing factor/authority records preserve unresolved force; no qualified target analogy classifier exists"}


def run(folder):
    corpus = read(OLD / "T0/attempt-1/corpus.json")
    questions = read(OLD / "T0/attempt-1/questions.json")
    benchmark = read(DOC / "benchmark.json")
    results = {}
    tasks = {
        "graphs": lambda: graph_trial(folder / "graphs"),
        "legalruleml": lambda: rule_trial(folder / "legalruleml"),
        "logical-english": lambda: le_trial(folder / "logical-english"),
        "retrieval": lambda: retrieval_trial(folder / "retrieval", corpus, questions, benchmark["retrieval_targets"]),
        "eyecite": lambda: worker("citations", {"texts": ["[2023] HKCFI 914", "[2025] HKCFI 493", "[2020] UKSC 12", "Brown v. Board of Education, 347 U.S. 483 (1954).", "Id. at 487."]}, folder / "eyecite"),
        "case-factors": lambda: case_trial(folder / "case-factors"),
    }
    for name, task in tasks.items():
        print("TOOL " + name, flush=True)
        try:
            results[name] = task()
        except Exception as exc:
            import traceback
            results[name] = {"status": "FAILED", "error": str(exc), "traceback": traceback.format_exc()}
        save(folder / "tools.json", results)
    results["not-selected"] = benchmark["not_selected"]
    save(folder / "tools.json", results)
    return {"status": "INTEGRATION_EVIDENCE_RECORDED", "tools": ref(folder / "tools.json"),
            "product_live_test": "PENDING_G3", "legal_closures": 0}
