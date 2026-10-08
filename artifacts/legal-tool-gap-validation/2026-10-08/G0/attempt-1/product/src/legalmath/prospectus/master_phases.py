"""Fixed actions for the reviewed prospectus evidence continuation."""
from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from xml.etree import ElementTree as ET

from . import master_control as c
from . import master_mechanisms as m
from . import master_sources as sources


def phase_result(current,phase):
    return c.read(c.ROOT/current["phases"][phase]["directory"]/"result.json")


def inventory(current):
    return c.read(c.ROOT/phase_result(current,"E1")["inventory"])


def requirements(data,rows):
    by_id={r["id"]:r for r in rows}
    return [m.input_requirements(issue,[e for e in by_id.get(issue["id"],{}).get("evidence",[]) if e["kind"] in {"principal_write_down","mandatory_common_conversion"} and e["disposition"]=="applicable"]) for issue in data["issues"]]


def integration(directory,data,rows):
    from ..transaction import intake
    from . import feature_investigation, instrument_sources, instrument_investigation, eligibility_checks
    bank,store=intake.bootstrap(c.ROOT,directory/"bank",at=c.now())
    registry=store.json(bank["registry_sha256"])
    for entry in c.read(c.ROOT/"docs/prospectus/legal/manifest.json")["sources"]:
        if entry.get("use_for_applicable_law") is False:continue
        key=Path(entry["text_path"]).stem; at=entry["retrieved_on"]
        if "T" not in at:at+="T00:00:00Z"
        raw=entry["key"]+".legal-original"
        registry[raw]=intake.record(store.put((c.ROOT/entry["path"]).read_bytes()),"law",entry["source_url"],at,media_type="application/octet-stream")
        registry[key]=intake.record(store.put((c.ROOT/entry["text_path"]).read_bytes()),"law",entry["source_url"],at,dependencies=[raw])
    bank["registry_sha256"]=store.put(registry)
    by_id={r["id"]:r for r in rows}; summaries=[]
    for issue in data["issues"]:
        request=m.issue_context(bank,issue)
        specific=None
        if issue["id"]=="ubs-sgd-at1-2024":
            specific={"profile":instrument_investigation.PROFILE,"dossier_sha256":store.put(instrument_sources.dossier(c.ROOT)),"scenario_sha256":None}
        receipt=feature_investigation.investigate(by_id[issue["id"]],issue,data["documents"],c.ROOT,request,store,instrument_request=specific)
        if receipt["may_execute_transaction"] or len(receipt["bank_investigation"]["inventory"])!=14:raise ValueError("Bank obligations or permission violated")
        c.write(directory/"receipts"/(issue["id"]+".json"),receipt,exclusive=True)
        summaries.append({"id":issue["id"],"instrument_kind":request["context"]["instrument_kind"],"obligations":14,"may_execute_transaction":False,
                          "scope":receipt["bank_investigation"]["calculations"]["scope"]["in_scope_product"],"mechanisms":len(receipt["source_obligations"]["mechanisms"])})
    c.write(directory/"bank-summary.json",summaries,exclusive=True)
    formal=eligibility_checks.prove(directory/"formal-scope")
    c.write(directory/"formal-scope.json",formal,exclusive=True)
    return summaries


def validate_rows(data,rows):
    from .source_obligations import replay
    by_id={r["id"]:r for r in rows}
    if len(by_id)!=len(data["issues"]):raise ValueError("Row identity count mismatch")
    for issue in data["issues"]:replay(by_id[issue["id"]],issue,data["documents"],c.ROOT)


def run_corpus(directory,inventory_path):
    argv=[str(c.ROOT/".venv/bin/python"),"scripts/run_bond_loss_absorption_classification.py","--inventory",c.relative(inventory_path),
          "--output",str(directory/"run"),"--checks","--plan",c.relative(c.PLAN)]
    command=c.command(argv,directory/"corpus.log",timeout=900)
    return command,c.read(directory/"run/classification.json")["results"]


def execute(phase,directory,current):
    if phase=="E0":
        baseline=c.ROOT/"docs/implementation/prospectus-gap-closure"
        manifest=c.read(baseline/"delivery-manifest.json")
        for p,h in manifest["files"].items():
            if c.sha(baseline/p)!=h:raise ValueError("Protected baseline changed: "+p)
        data=c.read(c.ROOT/"docs/prospectus/gap-closure/final-inventory.json")
        for doc in data["documents"].values():
            if c.sha(c.ROOT/doc["original"])!=doc["sha256"] or c.sha(c.ROOT/doc["text"])!=doc["text_sha256"]:raise ValueError("Changed retained source")
        from .common import JDK,LEAN,TOOLCHAIN
        versions={}
        for name,argv in {"python":[str(c.ROOT/".venv/bin/python"),"--version"],"java":[str(JDK/"bin/java"),"-version"],
                          "catala":[str(TOOLCHAIN["compiler"]),"--version"],"lean":[str(LEAN),"--version"],"poppler":["pdftotext","-v"]}.items():
            r=subprocess.run(argv,capture_output=True,text=True,timeout=30)
            if r.returncode:raise ValueError("Unavailable tool: "+name)
            versions[name]=(r.stdout+r.stderr).splitlines()[:2]
        c.write(directory/"baseline.json",{"report_sha256":c.sha(baseline/"results.json"),"inventory_sha256":c.sha(c.ROOT/"docs/prospectus/gap-closure/final-inventory.json"),"documents":len(data["documents"]),"versions":versions})
        return {"status":"PASS","resolved":["Protected baseline and 42 source identities checked","CPU toolchain and fixed prefix available"],"open_issues":[]}
    if phase=="E1":
        data=c.read(c.ROOT/"docs/prospectus/gap-closure/final-inventory.json")
        prior=c.read(c.ROOT/"docs/implementation/prospectus-gap-closure/integration/attempt-003/receipts/enel-senior-2028.json")["joined_request"]["bank_request"]
        issue=next(i for i in data["issues"] if i["id"]=="enel-senior-2028")
        defects={"scope_says_30": "30" in data["scope"] and len(data["issues"])==32,
                 "senior_fixture_marked_at1": prior["context"]["instrument_kind"]=="at1_bond" and "senior" in issue["rank"]}
        c.write(directory/"before-repair.json",{"defects":defects,"scope":data["scope"],"context":prior["context"]})
        if not all(defects.values()):raise ValueError("Declared baseline defects do not match preserved evidence")
        repaired=m.repaired_inventory(data);new=m.issue_context(prior,issue)
        if m.repaired_inventory(repaired)!=repaired or m.issue_context(new,issue)!=new:raise ValueError("Repair is not idempotent")
        c.write(directory/"inventory.json",repaired)
        c.write(directory/"after-repair.json",{"scope":repaired["scope"],"context":new["context"],"before_defects":2,"after_defects":0})
        return {"status":"PASS","inventory":c.relative(directory/"inventory.json"),"resolved":["32-case metadata and neutral debt fixture context"],
                "repairs":["Executed versioned inventory migration","Executed source-declared debt context binding"],"open_issues":["Fixture debt label is not evidence of HKMA scope"]}
    if phase=="E2":
        dossier=m.deutsche_dossier();c.write(directory/"deutsche-dossier.json",dossier)
        scenarios=[]
        for ratio in ("0.051249","0.05125","0.051251"):
            for needed in ("0","50","500"):
                scenarios.append(m.write_down(ratio=ratio,required_loss=needed,principal="100",others=[{"principal":"100","currency":"EUR","effective":True},{"principal":"80","currency":"EUR","effective":False}],currency="EUR",premise_kind="HYPOTHETICAL"))
        conditions={k:True for k in ("subsequent_financial_year","no_annual_loss_created","no_continuing_or_recreated_trigger","regulatory_conditions_met","pari_passu_conditions_met","notice_and_payment_date_met","issuer_elected_write_up")}
        ups=[]
        for elected in (True,False):
            conditions["issuer_elected_write_up"]=elected
            ups.append(m.write_up(annual_profit="100",written_down_initial="200",tier1="1000",distributions="5",mda_available="12",own_initial="100",pool_initial="200",own_prevailing="90",issuer_selected_total="12",conditions=conditions,premise_kind="HYPOTHETICAL"))
        c.write(directory/"hypothetical-calculations.json",{"write_down":scenarios,"write_up":ups,"actual_event":False})
        old=c.read(c.ROOT/"docs/implementation/prospectus-gap-closure/results.json")["results"]
        queue=requirements(inventory(current),old);c.write(directory/"evidence-requirements.json",queue)
        return {"status":"QUALIFIED","resolved":["Deutsche section 5(4) exact conditional arithmetic and boundary scenarios","Explicit per-issue private/source/calculation requirements"],
                "open_issues":["Actual capital, event, notice, holder and settlement inputs are absent","Other non-UBS/Deutsche numerical profiles still require source-specific implementation","Deutsche arithmetic does not implement all timing, regulatory determination or settlement obligations"]}
    if phase=="E3":
        tests=c.command([str(c.ROOT/".venv/bin/python"),"-m","pytest","tests/prospectus","tests/compliance","-q","--junitxml="+str(directory/"tests.xml")],directory/"tests.log")
        data=inventory(current);inv=c.ROOT/phase_result(current,"E1")["inventory"]
        command,rows=run_corpus(directory,inv);validate_rows(data,rows)
        baseline={r["id"]:r for r in c.read(c.ROOT/"docs/implementation/prospectus-gap-closure/results.json")["results"]}
        changes=[r["id"] for r in rows if r["answer"]!=baseline[r["id"]]["answer"]]
        if changes:raise ValueError("Unreviewed baseline answer changes: "+str(changes))
        summary=integration(directory,data,rows)
        frozen=c.freeze(current)
        return {"status":"PASS","regression":tests,"corpus":command,"classification":c.relative(directory/"run/classification.json"),"freeze":frozen,
                "cases":len(rows),"bank_cases":len(summary),"resolved":["Unchanged 32 baseline answers","All bank obligations retained; metadata repair used in actual integration"],"open_issues":[]}
    if phase=="E4":
        if not (c.DATA/"sources.json").exists():raise ValueError("Missing predeclared acquisition queue")
        receipts=[];repairs=[]
        for row in c.read(c.DATA/"sources.json")["requests"]:
            existing=[p for p in sorted((c.DATA/"requests").glob("*/receipt.json")) if c.read(p)["url"]==row["url"]]
            if existing:receipts.append(c.relative(existing[-1]));continue
            r=sources.acquire(row["key"],row["url"],row["purpose"],current)
            receipts.append(c.relative(c.DATA/"requests"/f"{r['budget_sequence']:03d}-{r['key']}"/"receipt.json"))
            if r.get("redirect"):
                try:
                    sources.valid_url(r["redirect"],c.read(c.OUT/"allowlist.json"))
                    follow=sources.acquire(row["key"]+"-redirect",r["redirect"],row["purpose"],current)
                    repairs.append({"kind":"executed_redirect_recovery","from":r["url"],"to":follow["url"],"status":follow["status"]})
                except ValueError as exc:repairs.append({"kind":"redirect_unavailable","reason":str(exc)})
        return {"status":"QUALIFIED","requests":len(list((c.DATA/"requests").glob("*/receipt.json"))),"receipts":receipts,"repairs":repairs,
                "resolved":["Public acquisition attempts preserved"],"open_issues":["Inspect source identities/editions and seal selection before classification"]}
    if phase=="E5":
        if not (c.DATA/"registered.json").exists():
            return {"status":"WAITING_SELECTION","open_issues":["Source acquisition needs inspection and sealed selection.json; use register before continuing"]}
        registration=c.read(c.DATA/"registered.json");inv=c.campaign_path(registration["inventory"])
        if c.sha(inv)!=registration["sha256"]:raise ValueError("Registered input changed")
        if c.sha(c.DATA/"selection.json") != registration["selection_sha256"]:
            raise ValueError("Selection changed; seal a new registration before classification")
        data=c.read(inv)
        if not data["issues"]:return {"status":"QUALIFIED","classification":None,"open_issues":["No eligible issue obtained; challenge incomplete"],"resolved":[]}
        frozen=c.read(c.ROOT/data["freeze"])
        if frozen["files"]!=c.method_files():raise ValueError("Sealed challenge method changed")
        cmd,rows=run_corpus(directory,inv);validate_rows(data,rows)
        witnesses=[]
        for row in rows:
            for e in row["evidence"]:
                if e["disposition"]=="applicable" and e["kind"] in {"principal_write_down","mandatory_common_conversion","cash_repayment"}:
                    witnesses.append({"issue_id":row["id"],"evidence_id":e["id"],"kind":e["kind"],"document":e["document"],"page":e["page"],"end_page":e["end_page"],"quote":e["quote"],"quote_sha256":c.digest(e["quote"])})
        c.write(directory/"witnesses-for-review.json",witnesses)
        return {"status":"QUALIFIED","classification":c.relative(directory/"run/classification.json"),"registered_inventory":c.relative(inv),"classification_sha256":c.sha(directory/"run/classification.json"),"command":cmd,"cases":len(rows),
                "resolved":["Frozen reader executed on sealed issue selections"],"open_issues":["Every applicable mechanism and cash witness requires contextual source inspection before promotion"],"witness_review_input":c.relative(directory/"witnesses-for-review.json")}
    if phase=="E6":
        fresh=phase_result(current,"E5")
        if not fresh.get("classification"):return {"status":"QUALIFIED","open_issues":["No unseen source evidence to review"],"repairs":[]}
        path=c.DATA/"witness-review.json"
        if not path.exists():return {"status":"WAITING_REVIEW","open_issues":["Inspect witnesses and record witness-review.json; classifications alone are insufficient"]}
        review=c.read(path);rows=c.read(c.ROOT/fresh["classification"])["results"]
        witnesses=c.read(c.ROOT/fresh["witness_review_input"])
        by_id={r["evidence_id"]:r for r in review["witnesses"]}
        if len(by_id) != len(review["witnesses"]) or set(by_id)!={w["evidence_id"] for w in witnesses}:raise ValueError("Review does not cover every applicable witness exactly once")
        if review["classification_sha256"]!=c.sha(c.ROOT/fresh["classification"]):raise ValueError("Review refers to stale classification")
        rejected=[]
        for w in witnesses:
            r=by_id[w["evidence_id"]]
            if r["quote_sha256"]!=c.digest(w["quote"]) or not r.get("reason"):raise ValueError("Review lacks source-bound reasoning")
            if r["disposition"] not in {"SUPPORTED_WITHIN_SELECTED_SOURCE","UNSUPPORTED","UNRESOLVED"}:raise ValueError("Unknown review disposition")
            if r["disposition"]!="SUPPORTED_WITHIN_SELECTED_SOURCE":rejected.append(r)
        if rejected:
            c.write(directory/"semantic-repair-queue.json",{"rejected":rejected,"required":"Add counterexample before causal patch, run review, then run from stale phase; acquisitions become exposed under next freeze"})
            return {"status":"REPAIR_REQUIRED","open_issues":["Source witness rejected; execute causal repair before dependent promotion"],"repairs":[]}
        c.write(directory/"accepted-review.json",review)
        return {"status":"QUALIFIED","resolved":[f"Inspected {len(witnesses)} complete applicable quotations"],"repairs":[c.read(p) for p in sorted((c.OUT/"repairs").glob("*.json"))],
                "open_issues":["Source-dependent model review is not human legal adjudication or population accuracy"]}
    if phase=="E7":
        data=inventory(current);rows=c.read(c.ROOT/phase_result(current,"E3")["classification"])["results"]
        fresh=phase_result(current,"E5")
        if fresh.get("classification"):
            more=c.read(c.ROOT/fresh["registered_inventory"]);data=deepcopy(data);data["documents"].update(more["documents"]);data["issues"]+=more["issues"]
            rows+=c.read(c.ROOT/fresh["classification"])["results"]
        c.write(directory/"inventory.json",data);c.write(directory/"classification.json",{"results":rows})
        validate_rows(data,rows);summaries=integration(directory,data,rows)
        c.write(directory/"evidence-requirements.json",requirements(data,rows))
        review_path=c.DATA/"source-review.json"
        source_review=sources.validate_source_review(c.read(review_path)) if review_path.exists() else {"findings":[],"status":"NOT_REVIEWED"}
        c.write(directory/"source-review.json",source_review)
        return {"status":"QUALIFIED","classification":c.relative(directory/"classification.json"),"inventory":c.relative(directory/"inventory.json"),"cases":len(rows),"bank_cases":len(summaries),
                "requirements":c.relative(directory/"evidence-requirements.json"),"resolved":["Full joined bank investigation retains all obligations and no trade permission"],
                "open_issues":["Actual client, bank-policy, mandate, event and current authority inputs remain absent","Any contracts not obtained and reviewed remain open","Unsupported per-issue numerical mechanisms remain explicit implementation work"]}
    if phase=="E8":
        from .master_report import build
        return build(directory,current)
    raise ValueError("Unknown declared phase")


def auxiliary(action,args,current):
    if action=="acquire":
        if len(args)!=3:raise ValueError("acquire requires key HTTPS-URL purpose")
        r=sources.acquire(*args,current);return {k:r.get(k) for k in ("key","status","http_status","kind","bytes","redirect","budget_sequence")}
    if action=="register":
        if len(args)!=1:raise ValueError("register requires campaign selection path")
        return sources.register(c.campaign_path(args[0]),current)
    if action=="check":
        if args!=["focused"]:raise ValueError("check supports only focused")
        folder=c.OUT/"checks"/f"attempt-{len(list((c.OUT/'checks').glob('attempt-*')))+1:03d}";folder.mkdir(parents=True)
        return c.command([str(c.ROOT/".venv/bin/python"),"-m","pytest","tests/prospectus/test_evidence_master.py","tests/prospectus/test_gap_closure.py","tests/prospectus/test_feature_investigation.py","-q","--junitxml="+str(folder/"tests.xml")],folder/"tests.log")
    if action=="repair":
        if args==["links"]:
            repaired=[]
            for p in sorted((c.DATA/"requests").glob("*/receipt.json")):
                receipt=c.read(p)
                if receipt.get("kind")=="pdf" or not receipt.get("sha256"):continue
                original=c.campaign_path(receipt["original"])
                if c.sha(original)!=receipt["sha256"]:raise ValueError("Discovery response changed")
                parser=sources.Links();parser.feed(original.read_text(errors="replace"))
                rows=[{"url":sources.urljoin(receipt["url"],r["href"]),"text":" ".join(r["text"].split())} for r in parser.links]
                target=c.DATA/"link-recovery"/receipt["sha256"]/"links.json"
                if not target.exists():c.write(target,{"receipt":c.relative(p),"source_status":receipt["status"],"links":rows},exclusive=True)
                repaired.append({"key":receipt["key"],"links":len(rows),"path":c.relative(target)})
            return {"status":"PASS","repairs":repaired}
        if args!=["derivatives"]:raise ValueError("Only fixed derivative/link repair is automatic; semantic repair requires reviewed code and tests")
        repaired=[]
        for p in sorted((c.DATA/"requests").glob("*/receipt.json")):
            r=c.read(p)
            if r["status"]=="RETAINED" and r["kind"]=="pdf":
                extraction=sources.extract(p);repaired.append(c.relative(extraction))
        return {"status":"PASS","derivatives":repaired}
    if action=="inspect":
        if not args:raise ValueError("inspect requires requests, file, source or baseline")
        if args[0]=="requests":
            return [{k:c.read(p).get(k) for k in ("key","purpose","status","http_status","kind","bytes","url","redirect","budget_sequence")} for p in sorted((c.DATA/"requests").glob("*/receipt.json"))]
        if args[0]=="file-search":
            if len(args)!=3:raise ValueError("file-search campaign-path regular-expression")
            path=c.campaign_path(args[1]);regex=re.compile(args[2],re.I);matches=[]
            for n,line in enumerate(path.read_text(errors="replace").splitlines(),1):
                for match in regex.finditer(line):
                    matches.append({"line":n,"snippet":line[max(0,match.start()-180):match.end()+500]})
                    if len(matches)>=45:break
                if len(matches)>=45:break
            return {"path":c.relative(path),"matches":matches}
        if args[0]=="links":
            if len(args) not in (2,3):raise ValueError("links receipt-path [filter]")
            receipt_path=c.campaign_path(args[1]);receipt=c.read(receipt_path)
            if c.sha(c.campaign_path(receipt["original"]))!=receipt["sha256"]:
                raise ValueError("Changed discovery source")
            repaired=c.DATA/"link-recovery"/receipt["sha256"]/"links.json"
            rows=c.read(repaired)["links"] if repaired.exists() else c.read(receipt_path.parent/"links.json")
            regex=re.compile(args[2],re.I) if len(args)==3 else None
            return [r for r in rows if regex is None or regex.search(r["text"]+" "+r["url"])][:70]
        if args[0]=="code":
            if len(args) not in (2,4):raise ValueError("code method-path [start-line count]")
            path=(c.ROOT/args[1]).resolve()
            if not path.is_relative_to(c.ROOT) or c.relative(path) not in c.method_files() or path.suffix not in {".py",".md"}:
                raise ValueError("Only reviewed method files may be read")
            start=int(args[2]) if len(args)==4 else 1;count=int(args[3]) if len(args)==4 else 180
            if start<1 or not 1<=count<=300:raise ValueError("Bounded lines required")
            return {"path":c.relative(path),"text":"\n".join(path.read_text().splitlines()[start-1:start-1+count])}
        if args[0]=="file":
            if len(args) not in (2,4):raise ValueError("file path [start-line count]")
            path=c.campaign_path(args[1]);start=int(args[2]) if len(args)==4 else 1;count=int(args[3]) if len(args)==4 else 180
            if start<1 or count<1 or count>300:raise ValueError("Bounded lines required")
            return {"path":c.relative(path),"text":"\n".join(path.read_text(errors="replace").splitlines()[start-1:start-1+count])}
        if args[0]=="source":
            if len(args) not in (2,4):raise ValueError("source receipt-path [page count]")
            path=sources.extract(c.campaign_path(args[1]));data=c.read(path)
            start=int(args[2]) if len(args)==4 else 1;count=int(args[3]) if len(args)==4 else 4
            if count<1 or count>12 or start<1:raise ValueError("Bounded page range required")
            return {"extraction":c.relative(path),"pages_total":len(data["pages"]),"pages":data["pages"][start-1:start-1+count]}
        if args[0]=="image":
            if len(args)!=2:raise ValueError("image requires one campaign-rendered image path")
            path=c.campaign_path(args[1])
            if path.suffix not in {".png",".jpg",".jpeg"} or path.stat().st_size>8_000_000:raise ValueError("Bounded PNG/JPEG required")
            import base64
            return {"image_base64":base64.b64encode(path.read_bytes()).decode(),"mime":"image/png" if path.suffix==".png" else "image/jpeg"}
        if args[0]=="baseline":
            data=c.read(c.ROOT/"docs/prospectus/gap-closure/final-inventory.json")
            if len(args)==1:return {"issues":[{"id":i["id"],"issuer":i["issuer"]} for i in data["issues"]],"documents":list(data["documents"])}
            if len(args)!=4:raise ValueError("baseline document page count")
            doc=data["documents"][args[1]];text=c.read(c.ROOT/doc["text"]);start,count=int(args[2]),int(args[3])
            if not 1<=count<=8:raise ValueError("Bounded source pages")
            return {"document":doc,"pages":text["pages"][start-1:start-1+count]}
        if args[0]=="search":
            if len(args)!=3:raise ValueError("search receipt-path regular-expression")
            path=sources.extract(c.campaign_path(args[1]));data=c.read(path)
            regex=re.compile(args[2],re.I);found=[]
            for page in data["pages"]:
                norm=" ".join(page["text"].split())
                for match in regex.finditer(norm):
                    found.append({"page":page["page"],"snippet":norm[max(0,match.start()-180):match.end()+420]})
                    if len(found)>=45:break
                if len(found)>=45:break
            return {"extraction":c.relative(path),"matches":found}
        raise ValueError("Unsupported read-only inspection")
    raise ValueError("Unsupported bounded auxiliary action")
