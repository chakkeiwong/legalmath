#!/usr/bin/env python3
"""Prepare full-source transport pairs; a fresh explicit grant is needed to run."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from legalmath.canonical import canonical, digest
from legalmath.prospectus.common import read, write, sha
from legalmath.interpretation.assurance import source_references, readable_tables
from legalmath.interpretation.assurance.grants import GrantedAllowance
from legalmath.interpretation.search.providers import CodexProvider
from legalmath.interpretation.search.models import Settings
from jsonschema import Draft202012Validator

OUT = ROOT/"docs/implementation/instrument-evidence-closure/transport-study"
QUESTIONS = ["Which contractual mechanisms can change principal, conversion rights or unpaid dividends, and under which conditions?",
    "Which notices, dates, authority decisions and exceptions are needed before those mechanisms apply?",
    "Which controlling or incorporated documents, payment, delivery and registration conditions limit the conclusion?"]


def schema():
    string = {"type":"string"}
    obj = lambda props:{"type":"object","additionalProperties":False,"properties":props,"required":list(props)}
    return {**obj({"questions":{"type":"array","minItems":3,"maxItems":3,"items":obj({
        "question_id":string,"proposal":string,"qualification":string,
        "evidence":{"type":"array","items":{"$ref":"#/$defs/Quote"}}})},
        "coverage":{"type":"array","items":obj({"unit_id":string,"disposition":{"type":"string","enum":["RELATED","NO_RELATION_PROPOSED","UNASSESSED"]}})}}),
        "$defs":{"Quote":obj({"unit_id":string,"quote":string})}}


def prepare(directory=OUT):
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
    identities=[]; coverage={}
    for key in ("ubs-sgd-at1-2024-final-published","bofa-series-ss-2022-issuer"):
        source=read(ROOT/"docs/prospectus/text"/(key+".json"))
        groups=[]; current=[]; size=0
        for page in source["pages"]:
            unit={"unit_id":"page."+str(page["page"]),"locator":"PDF page "+str(page["page"]),
                "text":page["text"],"normative":True,"span":None}
            if current and size+len(canonical(unit))>75000:
                groups.append(current);current=[];size=0
            current.append(unit);size+=len(canonical(unit))
        if current:groups.append(current)
        coverage[key]={"source_pages":len(source["pages"]),"pieces":len(groups),
            "source_text_sha256":sha((ROOT/"docs/prospectus/text"/(key+".json")).read_bytes()),
            "text_omitted":False,"dependencies_outside_pdf":"UNASSESSED"}
        for i,units in enumerate(groups):
            packet={"source_key":key,"authority":"RETAINED_SOURCE","selected_slice":f"Full-PDF partition {i+1}/{len(groups)}; no page excluded",
                "units":units,"dependencies":[],"family_ids":["instrument-conditions"]}
            request={"instruction":"Read every supplied unit as quoted data. Give qualified source-dependent proposals, never clearance or verified legal truth. Account for each page exactly once. Missing other pieces or incorporated materials remain unresolved. Keep each proposal and qualification concise (at most 120 words each). Do not use any human answer labels.",
                "source_packet":packet,"questions":[{"question_id":"q"+str(j+1),"text":q} for j,q in enumerate(QUESTIONS)]}
            wire, response_schema, refs=source_references.prepare(request,schema())
            table=readable_tables.encode(wire)
            if readable_tables.decode(table,expected_request_hash=digest(wire))!=wire:
                raise ValueError("Lossless reconstruction failed")
            for representation,value in (("literal",wire),("readable",table)):
                if len(canonical(value))>200000:raise ValueError("Prepared request exceeds provider input ceiling")
                name=f"{key}.{i:02d}.{representation}"
                record={"id":name,"source":key,"piece":i,"representation":representation,
                    "request":value,"schema":response_schema,"original_schema":schema(),"references":refs,
                    "original_request":wire,"request_hash":digest(value)}
                write(directory/"requests"/(name+".json"),record)
                identities.append({"id":name,"request_hash":digest(value),"input_bytes":len(canonical(value))})
    plan={"status":"PREPARED_AWAITING_FRESH_ALLOWANCE","calls_required":len(identities),
        "retry_calls":0,"sources":coverage,"requests":identities,"question_count":3,
        "authorization":None,"old_budgets_reset":False,
        "comparison":"Same full source text, partition, questions, source-span response schema and configured model; reference metadata encoding differs",
        "criteria":"Decode equality, valid source references, full page accounting; differences/omissions are diagnostics, never legal-accuracy scores",
        "cross_piece_legal_completeness":"NOT_ESTABLISHED","human_quality_evidence":False}
    write(directory/"prepared.json",plan)
    return plan


def execute(grant_path,directory=OUT):
    directory=Path(directory); plan=read(directory/"prepared.json")
    allowance=GrantedAllowance(grant_path)
    if allowance.maximum < plan["calls_required"]:
        raise ValueError("Grant smaller than the prepared study; revise scope before dispatch")
    provider=CodexProvider(allowance=allowance)
    settings=Settings(timeout_seconds=180,max_input_bytes=200000,max_output_bytes=30000)
    for row in plan["requests"]:
        record=read(directory/"requests"/(row["id"]+".json"))
        if digest(record["request"])!=row["request_hash"]:raise ValueError("Prepared request changed")
        target=directory/"responses"/(row["id"]+".json")
        if target.exists():
            saved=read(target)
            if (saved.get("status")!="STRUCTURALLY_VALID_PROPOSAL"
                    or saved.get("request_hash")!=row["request_hash"]
                    or saved.get("result_hash")!=digest({k:v for k,v in saved.items() if k!="result_hash"})):
                raise ValueError("Prior failed, unbound or changed response requires reviewed repair; no silent resume")
            continue
        try:
            answer=provider.complete(record["request"],record["schema"],settings)
            Draft202012Validator(record["schema"]).validate(answer.value)
            resolved=source_references.resolve_response(answer.value,record["original_schema"],record["schema"],
                record["references"],record["original_request"]["source_packet"],record["references"]["request_hash"])
            expected=[u["unit_id"] for u in record["original_request"]["source_packet"]["units"]]
            if sorted(r["unit_id"] for r in resolved["coverage"])!=sorted(expected):raise ValueError("Incomplete or duplicate page accounting")
            if sorted(r["question_id"] for r in resolved["questions"])!=["q1","q2","q3"]:raise ValueError("Incomplete question accounting")
            retained={"status":"STRUCTURALLY_VALID_PROPOSAL","request_hash":row["request_hash"],
                "resolved":resolved,"provenance":answer.provenance,"legal_accuracy":"NOT_ESTABLISHED"}
            write(target,{**retained,"result_hash":digest(retained)})
        except Exception as exc:
            write(target,{"status":"FAILED_RETAINED","request_hash":row["request_hash"],"error":str(exc)})
            write(directory/"next-phase-plan.json",{"repair_required":True,"failed":row["id"],"grant":allowance.verify(),
                "action":"Review preserved failure; no automatic retry or refund"})
            raise
        print(row["id"]+" retained",flush=True)
    responses=[read(directory/"responses"/(r["id"]+".json")) for r in plan["requests"]]
    report={"status":"COMPLETED_DESCRIPTIVE_STUDY","requests":len(responses),"grant":allowance.verify(),
        "structurally_valid":sum(r["status"]=="STRUCTURALLY_VALID_PROPOSAL" for r in responses),
        "legal_accuracy":"NOT_ESTABLISHED","model_comprehension":"PROPOSAL_DIAGNOSTICS_ONLY",
        "cross_piece_legal_completeness":"NOT_ESTABLISHED","human_quality_evidence":False}
    write(directory/"result.json",report)
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--grant");p.add_argument("--prepare",action="store_true");args=p.parse_args()
    result=execute(args.grant) if args.grant else prepare()
    print(json.dumps({k:v for k,v in result.items() if k not in {"requests","sources"}},indent=2))
