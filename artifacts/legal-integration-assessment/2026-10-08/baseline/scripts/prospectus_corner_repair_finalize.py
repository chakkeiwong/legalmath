"""Final report, reviewable patch, addendum build and preservation verification."""
from collections import Counter
from pathlib import Path
import difflib, fcntl, hashlib, json, re, shutil, sys, zipfile
import xml.etree.ElementTree as ET
from scripts import run_prospectus_corner_repair as m
from scripts.prospectus_corner_repair_provenance import inputs, orchestration

NEW = m.ROOT/"docs/prospectus/corner-repair-2026-10-04"

def latest(phase, suite=None):
    found=[]
    for path in sorted((m.OUT/"phases").glob("*/receipt.json")):
        row=m.read(path)
        if row["phase"]==phase and (suite is None or row["result"].get("suite")==suite):
            found.append((path,row))
    assert found, ("Missing phase",phase,suite)
    path,row=found[-1]
    assert row["result"]["status"]=="PASS", ("Latest phase failed",str(path))
    assert row["candidate_method"]==m.method(), ("Stale candidate phase",str(path))
    assert row.get("candidate_method_before",row["candidate_method"])==row["candidate_method"], "Method changed during phase"
    for name,digest in row["outputs"].items():
        assert m.sha(path.parent/name)==digest, ("Changed phase output",name)
    assert row.get("inputs"), "Evaluation lacks input bindings"
    for name,digest in row["inputs"].items():
        assert m.sha(m.ROOT/name)==digest, ("Stale evaluation input",str(path),name)
    required = (["scripts/prospectus_corner_repair_worker.py"] if phase in {"intake","legal","compare"} else [])
    if phase=="legal":required.append("scripts/prospectus_corner_repair_legal.py")
    for name in required:
        assert row["orchestration"][name]==m.sha(m.ROOT/name), ("Stale runner dependency",name)
    return path,row

def junit(path):
    root=ET.parse(path).getroot()
    suites=[root] if root.tag=="testsuite" else list(root.findall("testsuite"))
    return {k:sum(int(s.get(k,0)) for s in suites) for k in ("tests","failures","errors","skipped")}

def evidence():
    accepted={}
    for phase,suite in (("test","all"),("intake",None),("legal",None),("compare",None)):
        path,row=latest(phase,suite)
        accepted[phase]={"receipt":m.relative(path),"sha256":m.sha(path),"result":row["result"]}
    testpath=m.ROOT/accepted["test"]["receipt"]
    counts=junit(testpath.parent/"pytest.xml")
    assert counts["failures"]==counts["errors"]==0
    comparisons=m.read((m.ROOT/accepted["compare"]["receipt"]).parent/"comparisons.json")
    checks=m.read((m.ROOT/accepted["compare"]["receipt"]).parent/"classification-checks.json")
    paid=m.read((m.ROOT/accepted["compare"]["receipt"]).parent/"paid-controls.json")
    assert len(checks)==3 and all(c["status"]=="PASS" for c in checks)
    assert len(paid)==2 and all(c["status"]=="PASS" for c in paid)
    from scripts import prospectus_jurisdiction_study as j
    receipts=j.receipts()
    assert len(receipts)<=212
    return {"accepted":accepted,"tests":counts,"comparisons":comparisons,
            "classification":checks,"paid_controls":paid,"global_requests":len(receipts),
            "new_requests":len(receipts)-170,"remaining":212-len(receipts)}

def make_patch():
    baseline=m.read(m.OUT/"candidate-baseline.json")["files"]
    current=m.method()
    names={name for name,value in current.items() if baseline.get(name)!=value}
    names|=set(baseline)-set(current)
    fixture="tests/prospectus/fixtures/corner-mizuho.json"
    names.add(fixture)
    patch=[];changes=[]
    for name in sorted(names):
        old=m.ROOT/name
        new=m.CANDIDATE/name
        before=baseline.get(name)
        if before:
            assert old.is_file() and m.sha(old)==before, ("Baseline changed",name)
        else:
            assert not old.exists(), ("Unexpected pre-existing new file",name)
        oldtext=old.read_text() if before else ""
        newtext=new.read_text() if new.exists() else ""
        patch.extend(difflib.unified_diff(oldtext.splitlines(True),newtext.splitlines(True),
            fromfile="a/"+name if before else "/dev/null",
            tofile="b/"+name if new.exists() else "/dev/null"))
        changes.append({"path":name,"before_sha256":before,"after_sha256":m.sha(new) if new.exists() else None})
    (m.OUT/"candidate.patch").write_text("".join(patch))
    m.write(m.OUT/"candidate-changes.json",changes)
    archive=m.OUT/"candidate-method.zip"
    with zipfile.ZipFile(archive,"w",zipfile.ZIP_DEFLATED) as package:
        for name in sorted(set(current)|{fixture}):
            package.write(m.CANDIDATE/name,name)
    return changes

def report(data):
    a=data["accepted"];counts=data["tests"]
    compare=a["compare"]["result"];law=a["legal"]["result"];intake=a["intake"]["result"]
    lines=["# Executed prospectus repair — 4 October 2026","",
        "The isolated candidate fixes all three retained unpaid-cancellation exclusions and both Mizuho paid-amortisation false positives. "
        "The full candidate prospectus suite passes "+str(counts["tests"])+" tests. "
        "The original 293-file reader and prior study results remain the protected comparator.","",
        "## What changed","",
        "Cancellation evidence now binds the unpaid principal relation to the complete reviewed clause, its prerequisites and exceptions. "
        "The final-maturity withholding exception, certified-exhaustion certificate and notice, and deferred-cancellation misconduct exceptions survive source replay. "
        "Three-valued evaluation preserves missing facts. Paid amortisation requires its own payment relation and cannot hide a separate unpaid cancellation.","",
        "Intake reports empty and partial extraction explicitly and validates declared issuer, class, identifier, edition, role, base reference and required document sets. "
        "The first BES intake used final-terms dates as issue dates; manual image review corrected the actual issue dates to 15 July 2011, 21 January 2014 and 8 May 2014. "
        "All three bundles remain unresolved for incorporated accounts and precedence review.","",
        "The legal component executes typed boolean and date rules over source-bound declared premises. "
        "It separates contractual features, measures, recognition, procedure and enforcement. "
        "It rejects wrong scope, changed source bytes, mislocated quotations, stage changes and missing/conflicting facts. "
        "PDF anchors use the hashed text rather than an unbound page derivative. "
        "The 120-day boundary is checked under declared calendar-day premises; service facts and legal time-counting conventions remain external.","",
        "## Fixed-input comparison","",
        "| Input | Original answer | Candidate answer | Original unresolved records | Candidate unresolved records |",
        "| --- | --- | --- | --- | --- |"]
    label=lambda x:"Abstain" if x is None else "Conditional positive" if x else "Conditional negative"
    for row in data["comparisons"]:
        lines.append("| "+row["id"]+" | "+label(row["baseline_answer"])+" | "+label(row["candidate_answer"])+" | "+
                     str(row["baseline_unresolved"])+" | "+str(row["candidate_unresolved"])+" |")
    lines += ["","The seven offering documents move from seven abstentions to five abstentions and two conditional positive readings. "
        "Three source probes and the original Mizuho programme are additional fixed inputs. "
        "Counts describe this selected stress set; they are not a population accuracy estimate or a finding of actual loss.","",
        "## Verification evidence","",
        "- Full prospectus suite: "+str(counts["tests"])+" passed; zero failures or errors.",
        "- Original clause exclusions: 3/3 repaired with condition witnesses; real paid-amortisation controls: 2/2 preserved.",
        "- Declared legal scenarios: "+str(law["checks_passed"])+"/"+str(law["declared_scenarios"])+" match their engineering expectations; "+
          str(law["rule_results"]["CONDITIONAL"])+" conditional, "+str(law["rule_results"]["UNRESOLVED"])+" unresolved.",
        "- Extraction: 2 OCR_REQUIRED, 1 PARTIAL_TEXT, 4 TEXT_PRESENT; no automatic OCR performed.",
        "- Public follow-up: "+str(data["new_requests"])+" requests; "+str(data["global_requests"])+"/212 cumulative; "+str(data["remaining"])+" remaining.","",
        "Legal scenarios evaluate source-reviewed declarations; their expected labels are not independently adjudicated truth. "
        "The general evaluator contains no case-ID dispatch. Unit tests alter dates, stages, claim identity, conditions and source material separately.","",
        "## Decisions and remaining gaps","",
        "| Decision | Primary criterion | Veto status | Main uncertainty | Next justified action | Not concluded |",
        "| --- | --- | --- | --- | --- | --- |",
        "| Retain isolated cancellation/repayment repair | Five real clause controls pass | No observed regression in 885-test suite | Unseen syntax and distant cross-references | Independent review and unseen paired cases | General English or legal completeness |",
        "| Retain intake checks | Missing/wrong inputs rejected; valid declared control accepted | OCR and dependency vetoes remain | Scanned fields, incorporated accounts, precedence | Review OCR derivatives and complete BES dossiers | Complete issue analysis |",
        "| Retain typed legal evaluator | 25 declared scenarios and mutation checks pass | Independent adjudication absent | Rule interpretation and factual applicability | Independent legal review of premises and outcomes | Legal accuracy or final investor recovery |",
        "| Keep acquisition gaps explicit | All requests retained and budget counted | Missing primary instruments remain | Portuguese Annex 2B; HETA measure/list; original offers; exact Italian bankruptcy articles | Use a specific newly identified official or labelled mirror route | Search snippets or HTTP 200 as legal evidence |",
        "| Keep candidate separate | Reproducible candidate and reviewable patch | No production promotion | External review and unseen-case generalisation | Review patch and adjudicate before default adoption | Production readiness or transaction permission |","",
        "The follow-up recovered official historical Italian pages, including Law 130 Article 4. "
        "Its Article 67 exemption does not supply the separate Article 65 exemption. "
        "The generic bankruptcy pages and their explanatory notes do not replace the missing exact operative articles. "
        "Google navigation shells, unrelated Bing results and two HTTP 500 article responses were retained without source promotion. "
        "See [acquisition review](ACQUISITION-REVIEW.md).","",
        "The remaining source list is Portuguese 29 December 2015 decision/Annex 2B; original HETA decree and debt/guarantee list; "
        "Dana 2013 listing particulars; Lloyds 2009 offer/trust deed; Ukraine 2013 offer; Popular/Snoras originals; "
        "and the exact historical Italian bankruptcy articles. The three BES incorporation and precedence reviews and independent legal adjudication also remain open.","",
        "## Execution review","",
        "The initial wrong-interpreter setup run, missing-fixture broad run and empty-extraction failure remain in phases/003-test, 005-test and 008-test. "
        "The missing-fixture errors were harness defects; the empty-extraction failure was a candidate defect and triggered its repair. "
        "Two overlapping master launches were rejected by the shared lock before creating a phase and were rerun sequentially. "
        "No evidence was overwritten to make these failures disappear.","",
        "The strongest alternative explanation for many abstentions is deliberately broad input scope or missing document dependencies. "
        "The five source-verified clause defects and their paired controls are narrower evidence. "
        "An independently reviewed counterexample with a lost qualifier or wrong payment relation would overturn the corresponding repair claim. "
        "The weakest evidence remains legal interpretation and unseen-document generalisation. "
        "This rejects neither the research direction nor incomplete candidate work; it retains the tested repairs while blocking promotion.","",
        "Results are deterministic engineering checks, not a stochastic comparison; no superiority ranking is asserted. "
        "The target is condition-preserving classification of the retained passages. "
        "The code computes bounded English features and evaluates declared premises. "
        "Their equality to unrestricted legal meaning is not proved.","",
        "## Reproduction and artifacts","",
        "Master entry point: python3 -m scripts.run_prospectus_corner_repair PHASE. "
        "Available phases are prepare, diagnose, test, intake, legal, fetch, compare, finalize and verify. "
        "Run one phase at a time. Each records a receipt and refreshes NEXT-PHASE.md. "
        "Any candidate change makes finalisation and verification reject stale evaluation phases.","",
        "Candidate code uses the existing project .venv interpreter for workers and pytest; the master launcher is separately recorded. "
        "CUDA_VISIBLE_DEVICES=-1 is set before candidate work; no GPU or paid model calls were used. "
        "All random seeds are N/A because these checks are deterministic.",""]
    for phase,item in a.items():
        lines.append("- "+phase+": ["+item["receipt"].split("/phases/")[-1]+"]("+str(Path(item["receipt"]).relative_to(m.OUT.relative_to(m.ROOT)))+")")
    lines += ["","[Reviewable patch](candidate.patch), [candidate changes](candidate-changes.json), "
              "[LaTeX addendum](addendum.pdf), [run manifest](run-manifest.json), "
              "[reset memo](RESET-MEMO.md). Human prose acceptance and independent legal adjudication remain pending.",""]
    (m.OUT/"REPORT.md").write_text("\n".join(lines))

def finalize(folder,args):
    previous=m.OUT/"run-manifest.json"
    if previous.exists():
        snapshot=m.OUT/"publication-snapshots"/m.sha(previous)
        snapshot.mkdir(parents=True,exist_ok=True)
        shutil.copy2(previous,snapshot/"run-manifest.json")
        for name,digest in m.read(previous)["artifacts"].items():
            source=m.ROOT/name
            if source.is_file() and m.sha(source)==digest:
                dest=snapshot/source.relative_to(m.OUT)
                dest.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(source,dest)
    data=evidence()
    changes=make_patch()
    check=m.command(["git","apply","--check",str(m.OUT/"candidate.patch")],folder,"patch-check")
    assert check["exit_code"]==0, "Patch does not apply to preserved baseline"
    report(data)
    law=data["accepted"]["legal"]["result"]
    values={"AllTests":data["tests"]["tests"],"LegalCases":law["declared_scenarios"],
            "LegalConditional":law["rule_results"]["CONDITIONAL"],
            "LegalUnresolved":law["rule_results"]["UNRESOLVED"],
            "NewRequests":data["new_requests"],"RemainingRequests":data["remaining"]}
    (m.OUT/"results.tex").write_text("".join("\\newcommand{\\"+k+"}{"+str(v)+"}\n" for k,v in values.items()))
    for link in re.findall(r"\\href\{([^}]+)\}",(m.OUT/"addendum.tex").read_text()):
        if not link.startswith("http"):assert (m.OUT/link).is_file(), ("Broken LaTeX link",link)
    build=m.command(["latexmk","-pdf","-interaction=nonstopmode","-halt-on-error","addendum.tex"],
                    folder,"latex",cwd=m.OUT,timeout=180)
    assert build["exit_code"]==0, "Addendum build failed"
    import fitz
    pages=[]
    with fitz.open(m.OUT/"addendum.pdf") as doc:
        for n,page in enumerate(doc):
            dest=m.OUT/"render"/f"page-{n+1:03d}.png"
            dest.parent.mkdir(exist_ok=True)
            page.get_pixmap(dpi=100).save(dest)
            pages.append({"page":n+1,"text":page.get_text(),"image":m.relative(dest),"image_sha256":m.sha(dest)})
    m.write(m.OUT/"rendered-pages.json",{"pdf_sha256":m.sha(m.OUT/"addendum.pdf"),"pages":pages})
    (m.OUT/"RESET-MEMO.md").write_text(
        "# Repair execution reset memo\n\nBranch: feature/prospectus-evidence-master. Original HEAD and dirty method are preserved.\n\n"
        "Candidate: docs/implementation/prospectus-corner-repair-2026-10-04/candidate.\n"
        "Passing evaluation receipts are bound in run-manifest.json. Do not rerun old acquisitions or overwrite old PDFs.\n\n"
        "All 3 cancellation and 2 paid-amortisation checks pass; full suite "+str(data["tests"]["tests"])+" tests passes. "
        "25 declared legal scenarios are engineering checks, not independent legal outcomes. "
        "Source and OCR/dependency gaps remain open; see REPORT.md and ACQUISITION-REVIEW.md.\n\n"
        "Budget: "+str(data["global_requests"])+"/212 public requests; "+str(data["remaining"])+" remain. "
        "No broad search repeats or repeated unavailable URLs. Continue acquisition only with a specific new source route.\n\n"
        "Before final completion, inspect all addendum pages and record rendered-review.json, then run the verify phase. "
        "If code changes, rerun affected evaluation phases; finalisation rejects a changed candidate. "
        "Human prose acceptance and independent adjudication remain pending.\n")
    artifacts={}
    names=["REPORT.md","RESET-MEMO.md","SOURCE-REVIEW.md","ACQUISITION-REVIEW.md","DOCUMENT-PLAN.md",
           "candidate.patch","candidate-changes.json","candidate-method.zip","addendum.tex","results.tex",
           "addendum.pdf","rendered-pages.json"]
    for name in names:artifacts[m.relative(m.OUT/name)]=m.sha(m.OUT/name)
    for page in pages:artifacts[page["image"]]=page["image_sha256"]
    manifest={"schema":"prospectus-corner-repair.v1","at":m.now(),
        "git_commit":__import__("subprocess").check_output(["git","rev-parse","HEAD"],cwd=m.ROOT,text=True).strip(),
        "candidate_method":m.method(),"orchestration":orchestration(),"inputs":inputs(),
        "accepted_evaluations":data["accepted"],"tests":data["tests"],
        "command":"python3 -m scripts.run_prospectus_corner_repair finalize",
        "master_executable":sys.executable,"candidate_interpreter":str(m.ROOT/".venv/bin/python"),
        "compute":"CPU only; CUDA_VISIBLE_DEVICES=-1; GPU intentionally hidden; no device probe",
        "seeds":"N/A deterministic","data_version":m.sha(NEW/"source-index.json"),
        "plan":m.relative(m.PLAN),"result":m.relative(m.OUT/"REPORT.md"),
        "requests":{"cumulative":data["global_requests"],"new":data["new_requests"],"remaining":data["remaining"]},
        "patch_check":check,"build":build,"artifacts":artifacts,"human_prose_acceptance":"PENDING",
        "legal_adjudication":"PENDING","production_promotion":False}
    m.write(m.OUT/"run-manifest.json",manifest)
    return {"status":"PASS","changed_files":len(changes),"tests":data["tests"]["tests"],
            "report":m.relative(m.OUT/"REPORT.md"),"manifest":m.relative(m.OUT/"run-manifest.json"),
            "addendum_pages":len(pages),"rendered_inspection":"PENDING"}

def verify(folder,args):
    # The old verifier owns this same lock; invoke it before taking our own.
    baseline=m.command([sys.executable,"-m","scripts.verify_prospectus_corner_archive"],
                       folder,"original-archive",timeout=120)
    assert baseline["exit_code"]==0, "Preserved original archive check failed"
    with (m.ROOT/"docs/implementation/prospectus-evidence-closure/.lock").open("a+") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        data=evidence()
        manifest=m.read(m.OUT/"run-manifest.json")
        assert manifest["candidate_method"]==m.method()
        assert manifest["orchestration"]==orchestration(), "Final orchestration changed"
        assert manifest["accepted_evaluations"]==data["accepted"]
        for mapping in ("inputs","artifacts"):
            for name,digest in manifest[mapping].items():
                assert m.sha(m.ROOT/name)==digest, ("Final binding changed",name)
        state=m.read(m.OUT/"state.json")
        for item in state["phases"]:
            path=m.ROOT/item["receipt"]
            assert m.sha(path)==item["sha256"]
            row=m.read(path)
            for name,digest in row["outputs"].items():
                assert m.sha(path.parent/name)==digest, ("Historical phase changed",str(path),name)
        queue={r["key"]:r for r in m.read(NEW/"public-queue.json")}
        records=m.read(NEW/"source-index.json")["sources"]
        assert len(records)==len(queue)==data["new_requests"]
        for row in records:
            assert row["url"]==queue[row["key"]]["url"]
            receipt=m.read(m.ROOT/row["receipt"])
            assert m.sha(m.ROOT/row["receipt"])==row["receipt_sha256"]
            assert m.sha(m.ROOT/row["original"])==row["sha256"]==receipt["sha256"]
            for path,digest in receipt["files"].items():assert m.sha(m.ROOT/path)==digest
            policy=NEW/"policy-snapshots"/(receipt["acquisition_policy_sha256"]+".json")
            assert m.sha(policy)==receipt["acquisition_policy_sha256"]
            if row.get("text"):assert m.sha(m.ROOT/row["text"])==row["text_sha256"]
        review=m.read(m.OUT/"rendered-review.json")
        rendered=m.read(m.OUT/"rendered-pages.json")
        assert review["pdf_sha256"]==rendered["pdf_sha256"]==m.sha(m.OUT/"addendum.pdf")
        assert review["inspected_pages"]==[p["page"] for p in rendered["pages"]]
        assert review["layout_status"]=="PASS" and review["human_prose_acceptance"]=="PENDING"
        result={"status":"PASS","original_archive":baseline,"frozen_method_files":293,
                "phase_receipts":len(state["phases"]),"candidate_files":len(m.method()),
                "tests":data["tests"]["tests"],"new_requests":data["new_requests"],
                "remaining_requests":data["remaining"],"pdf_pages_inspected":len(review["inspected_pages"]),
                "run_manifest_sha256":m.sha(m.OUT/"run-manifest.json"),
                "rendered_review_sha256":m.sha(m.OUT/"rendered-review.json"),
                "legal_adjudication":"PENDING","production_promotion":False}
        m.write(folder/"verification.json",result)
        m.write(m.OUT/"verification.json",result)
        return result
