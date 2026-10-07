"""Terminal capability decisions; no automatic legal closure or next phase."""
from scripts.legal_tool_program import ROOT,OUT,DOC,read,save,ref,check_ref,used_provider
from scripts.legal_tool_components import previous

def run(work):
    components=read(check_ref(previous("T2")["components"]))
    live=previous("T3")
    direct=read(check_ref(live["direct"]))
    products=read(check_ref(live["products"]))
    review_path=DOC/"substantive-review.json"
    if not review_path.exists():
        raise RuntimeError("The bounded source/API and live-output review must precede terminal decisions")
    review=read(review_path)
    if review.get("status")!="REVIEWED_WITH_LIMITS":raise ValueError("Missing reviewed findings")
    expected_questions={r["id"] for r in read(check_ref(previous("T0")["questions"]))}
    if set(review.get("question_reviews",{}))!=expected_questions:
        raise ValueError("Every frozen question needs substantive disposition")
    if review.get("direct")!=live["direct"] or review.get("products")!=live["products"]:
        raise ValueError("Substantive review is not bound to these live results")
    repaired=OUT/"logical-english-repair/result.json"
    if repaired.exists():components["logical-english"]=read(repaired)
    save(work/"substantive-review.json",review)
    decisions=[]
    for tool,row in components.items():
        if row.get("status") in ("TRIAL_FAILED","FAILED_CONTROLS"):
            decision="DEFER_FAILED_CONTROL"
            capability=row.get("error",row.get("scope","Controls failed; capability unqualified"))
        elif tool=="pyarg" and row.get("status")=="PASS":
            decision="ADOPT_OPTIONAL_CHECKER"
            capability="Pinned external grounded/preferred check on supplied bounded graphs"
        elif tool=="retrieval" and row.get("status")=="EXECUTED":
            decision="ADAPT_AS_EXPLICIT_RETRIEVAL_BASELINE"
            capability="Rank and return exact retained source passages; relevance requires inspection"
        else:
            decision=row.get("decision","DEFER")
            capability=row.get("reason",row.get("scope","No qualified additional capability demonstrated"))
        decisions.append({"tool":tool,"decision":decision,"capability":capability,
                          "substantive_obligations_closed":0})
    for tool,reason in (
      ("Tweety/s(CASP)","Alternative graph/rule engines; no selected unmet trial beyond PyArg/clingo"),
      ("KeY","No selected additional JML proof obligation addressing source interpretation"),
      ("MAPIE","No eligible calibration corpus; confidence claims unsupported"),
      ("LangGraph","Existing durable journal executes this bounded comparison"),
      ("existing execution/extraction tools","Retained capability; no new general accuracy claim")):
        decisions.append({"tool":tool,"decision":"RETAIN_OR_DEFER","capability":reason,
                          "substantive_obligations_closed":0})
    complete_evidence=(len(direct)==8 and all(r["status"]=="VALIDATED" for r in direct)
        and set(products)=={"baseline","tools"}
        and all(p.get("execution_complete") for p in products.values()))
    result={"status":"DECISIONS_RECORDED" if complete_evidence else "DECISIONS_RECORDED_WITH_INCOMPLETE_EVIDENCE",
        "evidence_complete":complete_evidence,"decisions":decisions,
        "substantive_review":ref(work/"substantive-review.json"),
        "question_findings":review["question_reviews"],
        "live_direct_validated":sum(r["status"]=="VALIDATED" for r in direct),
        "live_direct_total":len(direct),"products":products,"provider_calls":used_provider(),
        "open_obligations":46,"unformalized_readings":32,"substantive_closures":0,
        "english_fidelity":"NOT_ESTABLISHED","legal_correctness":"NOT_ESTABLISHED",
        "statistical_ranking":"NOT_SUPPORTED","default_changed":False,"next_phase":None,
        "remaining_custom_work":"Only after source-specific unmet capability is demonstrated; no automatic new engine",
        "interpretation_limit":"Source review is bounded to the retained responses and development sources; trial dispositions do not establish legal correctness"}
    save(work/"decision.json",result)
    lines=["# Tool comparison result","","The bounded tool trials have ended with the following capability decisions.",
        "The original 46 obligations remain open. Trial completion does not establish legal interpretation.",
        "","| Tool | Decision | Capability or limit |","|---|---|---|"]
    lines += ["| "+r["tool"]+" | "+r["decision"]+" | "+r["capability"].replace("|","/")+" |" for r in decisions]
    lines += ["","## Decision and inference status","",
        "| Decision item | Status | Next justified action |",
        "|---|---|---|",
        "| Primary capability criteria | See actual per-tool receipts | Use only the stated supported capability |",
        "| Promotion vetoes | Source, question, missing premise and semantics checks remain mandatory | Reject any output violating them |",
        "| Hard veto screen | Invalid provider output and unavailable tools retained individually | Repair only a reproduced defect within budget |",
        "| Statistically supported ranking | None | More independent, permitted evidence would be required |",
        "| Descriptive differences | Paired model outputs and tool diagnostics | Inspect arguments against sources |",
        "| Default readiness | No default changed | Optional integration only |",
        "| Main uncertainty | Source-to-standard and observation-to-judgment reasoning | Resolve a named source/fact question |",
        "","Strongest alternative explanation: prompt organisation or sampling, rather than the external algorithm, caused any observed model differences.",
        "A contrary source passage, lost uncertainty or a mismatched external semantics would overturn the affected capability finding.",
        "The weakest evidence is substantive legal support and the small non-blind model comparison.",
        "",
        "Detailed live responses, source-span checks and actual product dossiers are retained in T3.",
        "No prospective generalisation, legal accuracy rate or client compliance is established."]
    lines += ["","## Actual comparison findings","",
              "Evidence completeness: "+str(complete_evidence)+". Provider reservations: "+str(used_provider())+".",""]
    for qid,finding in review["question_reviews"].items():
        lines += [qid+": "+finding["finding"],""]
    lines += ["Remaining work: "+review.get("remaining_work","Source-to-standard and factual application remain unresolved")+".",""]
    (work/"result.md").write_text("\n".join(lines)+"\n")
    save(work/"validation.json",{"decision_process":"REVIEWED","evidence_complete":complete_evidence,
        "review":ref(work/"substantive-review.json"),"direct":live["direct"],"products":live["products"],
        "legal_correctness":"NOT_ESTABLISHED"})
    DOC.mkdir(parents=True,exist_ok=True)
    (DOC/"reset-memo.md").write_text("# Tool comparison reset memo\n\nProgram execution reached T4. See "+
        str((work/"decision.json").relative_to(ROOT))+" and result.md. No successor is scheduled.\n")
    return {**result,"decision":ref(work/"decision.json"),"report":ref(work/"result.md")}
