"""Terminal capability decisions; no automatic legal closure or next phase."""
from scripts.legal_tool_program import ROOT,OUT,DOC,read,save,ref,check_ref,used_provider,accounting
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
    frozen=previous("T0")
    corpus=read(check_ref(frozen["corpus"]))
    units={r["id"] for r in corpus["units"]}
    for finding in review["question_reviews"].values():
        if not finding.get("finding") or not finding.get("missing_premises"):
            raise ValueError("Empty question review")
        if not finding.get("source_units") or not set(finding["source_units"]) <= units:
            raise ValueError("Question review has unknown source units")
    if set(review.get("component_reviews",{})) != set(components):
        raise ValueError("Every tested or deferred component needs a reviewed disposition")
    expected_arms={(q,a) for q in expected_questions for a in ("baseline","tools")}
    if len(direct)!=8 or {(r["question"],r["arm"]) for r in direct}!=expected_arms:
        raise ValueError("Direct comparison lost a declared arm")
    if set(products)!={"baseline","tools"}:
        raise ValueError("Product comparison lost a declared arm")
    counts=accounting(read(OUT/"state.json"))
    audit_references=[ref(DOC/"t4-audit.md"),ref(review_path),
        frozen["corpus"],frozen["questions"],previous("T2")["components"]]
    for name in ("provider-allowance.json","network.json","repairs.json",
                 "time-extension.json","time-extension-invalid-1.json"):
        audit_references.append(ref(OUT/name))
    for item in read(OUT/"repairs.json")["repairs"]:
        check_ref(item["review"])
        audit_references.append(item["review"])
    save(work/"accounting.json",counts)
    repaired=OUT/"logical-english-repair/result.json"
    if repaired.exists():
        components["logical-english"]=read(repaired)
        audit_references.append(ref(repaired))
    def collect(value):
        if isinstance(value,dict):
            if "path" in value and "sha256" in value:
                check_ref(value)
                audit_references.append({"path":value["path"],"sha256":value["sha256"]})
            for child in value.values():collect(child)
        elif isinstance(value,list):
            for child in value:collect(child)
    collect(read(OUT/"time-extension.json"))
    collect(previous("T1"))
    collect(corpus)
    collect(components)
    audit_references=list({r["path"]:r for r in audit_references}.values())
    save(work/"audit-references.json",audit_references)
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
        detail=review["component_reviews"][tool]
        decisions.append({"tool":tool,"decision":decision,"capability":capability,
                          "finding":detail["finding"],"limit":detail["limit"],
                          "overturn":detail["overturn"],"substantive_obligations_closed":0})
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
    validation={"decision_process":"REVIEWED","evidence_complete":complete_evidence,
        "review":ref(work/"substantive-review.json"),"direct":live["direct"],"products":live["products"],
        "audit_references":ref(work/"audit-references.json"),"accounting":counts,
        "legal_correctness":"NOT_ESTABLISHED"}
    save(work/"validation.json",validation)
    result={"status":"DECISIONS_RECORDED" if complete_evidence else "DECISIONS_RECORDED_WITH_INCOMPLETE_EVIDENCE",
        "evidence_complete":complete_evidence,"decisions":decisions,
        "substantive_review":ref(work/"substantive-review.json"),
        "question_findings":review["question_reviews"],
        "live_direct_validated":sum(r["status"]=="VALIDATED" for r in direct),
        "live_direct_total":len(direct),"products":products,"provider_calls":used_provider(),
        "open_obligations":46,"unformalized_readings":32,"substantive_closures":0,
        "english_fidelity":"NOT_ESTABLISHED","legal_correctness":"NOT_ESTABLISHED",
        "live_product_integration":"UNTESTED","validation":ref(work/"validation.json"),
        "statistical_ranking":"NOT_SUPPORTED","default_changed":False,"next_phase":None,
        "remaining_custom_work":review["remaining_work"],
        "audit_references":audit_references,"accounting":counts,
        "live_finding":review["finding"],
        "interpretation_limit":"Bounded component and development-source review; no structured model answers or completed product trials"}
    save(work/"decision.json",result)
    lines=["# Tool comparison result, 7 October 2026","",
        "T4 records terminal decisions with incomplete live evidence. "+review["finding"],"",
        "PyArg and Carneades each matched 532 supplied graphs. Carneades also passed seven artificial CAES controls. "
        "LegalRuleML passed its schema controls. rank-bm25 returned exact retained text. These qualify narrow "
        "development capabilities; the actual product comparisons did not run. Production defaults are unchanged.","",
        "| Tool | Decision | Demonstrated capability and limit |","|---|---|---|"]
    lines += ["| "+r["tool"]+" | "+r["decision"]+" | "+
              r.get("finding",r["capability"]).replace("|","/")+" "+
              r.get("limit","").replace("|","/")+" |" for r in decisions]
    lines += ["","## Decision record","",
        "| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | What is not concluded |",
        "|---|---|---|---|---|---|",
        "| Retain optional graph checkers | 532 matched supplied graphs in each engine; CAES controls pass | No mismatch in this finite profile | Authored premises and graph construction can be wrong | Use only explicit matched semantics | Correct English interpretation or legal priorities |",
        "| Retain schema and retrieval baselines | Positive/negative XML controls and exact text identity pass | Product roundtrip and relevance remain untested | Mixed document/paragraph units distort ranking; XML may encode a wrong rule | Inspect passages and require a roundtrip before product adoption | Relevant retrieval or source equivalence |",
        "| Defer Logical English and HK citation route | LE positive controls fail; eyecite misses 2/2 HK examples | These local routes fail qualification | Adapter/declaration defects and jurisdiction coverage | Record defects; no repairs remain here | Controlled language or citation extraction is impossible |",
        "| Defer legal/product promotion | Zero validated direct answers; both product arms unattempted | Unresolved provider transport and missing legal/factual premises | Tool effect on actual product answers is unknown | A separately authorized, functioning comparison and source review would be required | Tools solved English interpretation |",
        "| End the finite program | Reviewed decisions and preserved incomplete evidence | Repair budget exhausted; no successor scheduled | Residual legal gaps persist | Retain specific open questions below | Rejection of the research direction |",
        "","## Inference status","",
        "| Evidence class | Finding |",
        "|---|---|",
        "| Hard veto screen | Two transport timeouts yielded no structured answer; LE positive controls fail; HK citation controls missed |",
        "| Viable capabilities | Bounded graph checking, official XML-schema validation and exact-text lexical retrieval |",
        "| Statistically supported ranking | None; no paired model answers were obtained |",
        "| Descriptive-only differences | Component controls and retrieval ranks only; no observed model accuracy differences |",
        "| Default-readiness | No production default change; end-to-end tool benefit untested |",
        "| Next evidence needed | Functioning provider route, complete paired product evidence and independent source/target review before any stronger claim |",
        "","## Four original questions",""]
    for qid,finding in review["question_reviews"].items():
        lines += ["**"+qid+"**. "+finding["finding"],"",
                  "Missing premises: "+finding["missing_premises"],"",
                  "Frozen source units: "+", ".join(finding["source_units"])+".",""]
    lines += ["## Remaining work","",review["remaining_work"],"",
        "The existing S4 route preserves qualified conditional results; the prior follow-up did not reproduce "
        "a duty-to-fulfillment substitution. This program gives no reason to install another engine to repair "
        "that unreproduced bug. Source-to-standard reasoning and target facts remain the substantive gaps.",
        "","## Red-team review","",
        "The strongest alternative explanation for component agreement is that all tools received the same "
        "wrong authored premises or graph. Agreement cannot detect that shared mistake. The weakest evidence "
        "is the absent live product comparison and the unestablished legal standards/target facts. "
        "The provider timeouts invalidate no frozen source or completed component trial. They leave the live "
        "comparison incomplete; the exhausted repair cap ends dispatch. This is a runtime feasibility result, "
        "not evidence against tool reuse as a research direction.","",
        "The separate plugin-catalogue 403 warning does not establish the cause of the model timeouts. "
        "No model accuracy improvement, client compliance, source generalization or complete current-treatment "
        "assessment is established.",""]
    for row in decisions:
        if "overturn" in row:lines.append("- "+row["tool"]+": "+row["overturn"])
    lines += ["","## Reproduction and accounting","",
        "Provider reservations: "+str(counts["provider_calls"])+"/48; network acquisition processes: "+
        str(counts["network_processes"])+"/12; counted repairs: "+str(counts["repairs_used"])+"/4. "
        "The explicit 24-hour reporting renewal preserves prior spending, the expired four-hour grant and the invalid earlier renewal as history.","",
        "[Frozen sources](../../T0/attempt-1/corpus.json), "
        "[component results](../../T2/attempt-1/components.json), "
        "[direct attempt dispositions](../../T3/attempt-2/direct-comparison.json), "
        "[product dispositions](../../T3/attempt-2/product-comparison.json), "
        "[substantive review](substantive-review.json), [validation](validation.json), "
        "and [execution manifest](result.json) preserve the question, method and actual evidence. "
        "The manifest records the command, commit, dirty worktree, CPU environment, elapsed time, "
        "source/method hashes and outputs. Deterministic controls require no random seed; provider "
        "sampling is unavailable because no answer returned.",""]
    (work/"result.md").write_text("\n".join(lines)+"\n")
    DOC.mkdir(parents=True,exist_ok=True)
    (DOC/"reset-memo.md").write_text("# Tool comparison reset memo\n\n"
        "T4 recorded terminal decisions with incomplete live evidence. Two reservations produced no "
        "structured model answer. All 46 obligations and 32 unformalized readings remain open. "
        "No further dispatch, repair or successor is scheduled. See "+
        str((work/"decision.json").relative_to(ROOT))+" and result.md.\n")
    return {**result,"decision":ref(work/"decision.json"),"report":ref(work/"result.md")}
