"""Prepare independent review packets without inventing reviewer conclusions."""
import json
from collections import Counter
from scripts import run_prospectus_closure_next as m

def run():
    old=m.ROOT/"docs/implementation/prospectus-corner-repair-2026-10-04"
    manifest=m.read(old/"run-manifest.json")
    accepted=manifest["accepted_evaluations"]["legal"]
    receipt=m.ROOT/accepted["receipt"]
    if m.sha(receipt)!=accepted["sha256"]:raise ValueError("Accepted legal receipt changed")
    scenarios_path=receipt.parent/"rule-scenarios.json"
    scenarios=m.read(scenarios_path)
    folder=m.OUT/"independent-review";folder.mkdir(exist_ok=True)
    rows=[]
    for scenario in scenarios:
        case=scenario["case"]
        row={"case":case,"source_scenario":str(scenarios_path.relative_to(m.ROOT)),
            "source_scenario_sha256":m.sha(scenarios_path),
            "question":"Determine the controlling source interpretation for this instrument, forum, operative date, claim and procedural stage.",
            "source_rule_and_context":{k:scenario[k] for k in ("rule","context","scope")},
            "adjudication":{"status":"UNASSIGNED","reviewer":None,"reviewer_qualifications":None,"independence_attestation":None,
                "instrument_identifiers":None,"issuer_and_claim_class":None,"forum":None,"law_effective_date":None,
                "source_observation_date":None,"procedural_stage":None,"proved_facts":None,"unknown_facts":None,
                "exceptions":None,"outcome":None,"exact_source_anchors":None,"reasoning":None,
                "disagreements":None,"decision_date":None}}
        m.write(folder/(case+".json"),row);rows.append(case)
    if len(rows)!=25 or len(set(rows))!=25:raise ValueError("Expected 25 distinct scenario records")
    # Keep model expected outcomes separate from review forms to reduce avoidable anchoring.
    m.write(folder/"development-expectations.json",{s["case"]:s["expected"] for s in scenarios})
    groups_path=m.ROOT/"docs/implementation/prospectus-evidence-closure/phases/S4/attempt-004/clause-groups.json"
    groups=m.read(groups_path);records=sum(len(g["bindings"]) for g in groups)
    queue=[]
    for group in groups:
        binding=group["bindings"][0];e=binding["evidence"];quote=e["quote"]
        reasons=[]
        if any(word in quote.lower() for word in ("subject to","unless","provided","except")):reasons.append("qualification")
        if e.get("end_page",e["page"])!=e["page"]:reasons.append("page_boundary")
        if any(word in quote.lower() for word in ("write down","written down","principal","conversion","cancel")):reasons.append("principal_or_conversion")
        queue.append({"id":group["id"],"bindings":group["bindings"],"triage_tags":reasons,
            "triage_only":True,"controlling_meaning":None,"reviewer":None,"status":"UNADJUDICATED"})
    queue.sort(key=lambda g:(-len(g["triage_tags"]),g["id"]))
    m.write(folder/"original-cohort-clause-review.json",{"source":str(groups_path.relative_to(m.ROOT)),
        "source_sha256":m.sha(groups_path),"records":records,"unique_spans":len(groups),"groups":queue,
        "note":"Priority tags organize reading; they are not accuracy labels or automatic semantic dispositions."})
    m.write(folder/"material-disputes.json",{
        "bes":m.read(m.OUT/"dossier-review.json")["conflicts"],
        "ocr":{"reviewed_extractions":str((m.DATA/"reviewed-extractions.json").relative_to(m.ROOT)),
            "sha256":m.sha(m.DATA/"reviewed-extractions.json"),"human_review":None},
        "finance":{"result":str((m.OUT/"repairs-results.json").relative_to(m.ROOT)),
            "sha256":m.sha(m.OUT/"repairs-results.json"),"independent_formula_and_scope_review":None}})
    protocol={
        "status":"AWAITING_INDEPENDENT_LABELS_AND_UNEXPOSED_COHORT","cohort":None,
        "exposed_sets":["original 36 issues","24 difficult prospectuses","30 jurisdiction corner cases",
            "25 declared scenarios","all sources inspected during 4–5 October closure"],
        "candidate_freeze":None,"baseline":"Frozen original reader; compare identical complete inputs and issue scopes",
        "labels":"Two qualified independent source reviewers record exact scope/date/exception labels, then resolve or retain disputes. Reviewer selection is pending.",
        "cohort_selection":"A separate curator predeclares inclusion criteria and hashes genuinely unexposed source packages before model execution. No convenient replacement after a failure.",
        "primary_criteria":["No false definitive answer on any deliberately incomplete input or unknown material fact",
            "Every decisive quotation replays against exact reviewed source bytes with qualifications",
            "Paired source-adjudicated correctness and coverage reported jointly, with abstentions and disputes explicit"],
        "vetoes":["corrupt or incomplete inputs","changed method during evaluation","exposed cohort","missing independent labels","lost material qualifier"],
        "explanatory_only":["test count","OCR length","number of unresolved records","runtime","reduced abstention count"],
        "promotion":"No default adoption from this engineering exercise. Intended-use acceptance and independently reviewed downstream bank investigations remain required.",
        "statistical_reporting":"Report per-case paired outcomes and uncertainty before any generalisation/ranking. Small zero-error samples cannot establish population reliability.",
        "requests":{"current_total":188,"ceiling":212,"remaining":24},
        "output_required":["cohort hashes","method hashes","reviewer declarations","labels/disputes","paired results","error analysis","scoped acceptance"]}
    m.write(folder/"unseen-validation-protocol.json",protocol)
    text="# Independent source review\n\n"
    text+="The 25 numbered forms contain source rules and declared context. All adjudication fields are unassigned. Development expectations are stored separately and should be withheld from the first review. A machine run cannot fill these fields as independent legal adjudication.\n\n"
    text+="Review each instrument identifier, issuer, class, forum, operative date, observation date, procedural stage, factual premise and exception against the controlling source. Preserve a disagreement or missing source explicitly. The review also covers the BES section-number conflict, OCR identifiers and conditional calculation scope.\n\n"
    text+=f"The original-cohort queue retains {records} unresolved records across {len(groups)} source spans. Triage tags indicate useful reading order only; no original semantic gap is declared closed by this queue.\n\n"
    text+="The unseen protocol requires a separate curator and independent labels. Every prospectus already inspected is excluded from an unseen claim. Requests remaining: 24. No request is spent merely to fill a numerical target.\n"
    (folder/"README.md").write_text(text)
    result={"status":"PASS","scenario_forms":len(rows),"independent_adjudications":0,
        "original_unresolved_records":records,"original_unique_spans":len(groups),
        "unseen_evaluation_executed":False,"unseen_protocol":"PREPARED",
        "continuation":"Local engineering completed for the reviewed successor scope; source/implementation work listed in REPORT.md remains open."}
    m.write(m.OUT/"packet-results.json",result);print(json.dumps(result,indent=2))
