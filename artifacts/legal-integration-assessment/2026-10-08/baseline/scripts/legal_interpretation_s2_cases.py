"""Opinion-aware records from retained original court documents, with transfer limits."""
from dataclasses import asdict
import hashlib
import json
import re
import zipfile
from xml.etree import ElementTree as ET
from pathlib import Path
from legalmath.canonical import digest
from legalmath.interpretation.semantics.records import SourceSpan, Interval
from legalmath.interpretation.semantics.precedent import (
    JudgmentManifest, Passage, Proposition, Factor, Move, Authority, Treatment,
    validate_case, assess_authority)
ROOT=Path(__file__).resolve().parents[1]
ACQ=ROOT/"artifacts/legal-interpretation-program/successor-s2/acquisition"
QUESTION="What do the retained Gatecoin judgments establish, and what premises are missing for transfer to 26EC22?"
def source(identity):
    path=ACQ/identity/"response.bin";result=json.loads((path.parent/"result.json").read_text())
    if result["http_status"]!=200 or result["format"]!="DOCX_TEXT_WITH_FOOTNOTES":
        raise ValueError("Required official court document not acquired")
    with zipfile.ZipFile(path) as archive:
        ns={"w":"http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs=[]
        for name in ("word/document.xml","word/footnotes.xml","word/endnotes.xml"):
            if name in archive.namelist():
                xml=ET.fromstring(archive.read(name))
                paragraphs += ["".join(t.text or "" for t in p.findall(".//w:t",ns)) for p in xml.findall(".//w:p",ns)]
    text=re.sub(r"\s+"," ","\n".join(paragraphs)).strip()
    return text,{"path":str(path.relative_to(ROOT)),"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
        "url":result["final_url"],"retrieved_at":result["retrieved_at"],
        "extraction":"OOXML document, footnotes and endnotes w:t text in document order; whitespace normalized; no visual fidelity certification"}
def excerpt(text,start,end):
    i=text.index(start);return text[i:text.index(end,i+len(start))].strip()
def build():
    text23,raw23=source("gatecoin-2023-official");text25,raw25=source("gatecoin-2025-official")
    packet={"units":[{"unit_id":"gatecoin-2023","text":text23},{"unit_id":"gatecoin-2025","text":text25}]}
    definitions=[
      ("gatecoin-2023","[2023] HKCFI 914","2023-03-31",text23,raw23,[
        ("conclusion-82",excerpt(text23,"For the reasons discussed above, in respect of Question 1, I hold that:","As for Question 2"),
         "Cryptocurrency can be property capable of trust, but the 2018 terms did not create the claimed trust for the customers subject to them; the non-consenting exception is preserved.","holding"),
        ("terms-and-intention",excerpt(text23,"The principles on certainty of intention have been summarised","During the currency of the 2016"),
         "Terms such as trust or ownership are not conclusive when the objectively assessed relationship compels a different conclusion.","reasoning")]),
      ("gatecoin-2025","[2025] HKCFI 493","2025-01-24",text25,raw25,[
        ("earlier-decision",excerpt(text25,"By Decision dated 31 March 2023","The Liquidators were directed"),
         "The later court records the earlier property/trust conclusions and non-consenting-customer exception.","reasoning"),
        ("classification-8",excerpt(text25,"For the reasons explained in","The 7 scenarios are"),
         "The detailed reasoning treats four scenarios as non-consenting absent contrary evidence, two as requiring further proof, and rejects the factual existence of the seventh scenario.","reasoning"),
        ("disposition-95",excerpt(text25,"For all the above reasons, in respect of the 4 issues","I give the directions"),
         "The disposition addresses customer classification, pooled beneficial interests, allocation, breach-of-trust compensation and the failure of Samara's claimed trust against Gatecoin.","holding"),
        ("annexure-issue1",excerpt(text25,"The following categories of automated transactions taking place","The nature of each Non-Consenting"),
         "The annexure gives operative classifications and evidence requirements; its text must be reconciled with paragraphs 8 and 95 before an executable classifier is claimed.","reasoning")]),
    ]
    built=[]
    for identity,citation,day,body,raw,items in definitions:
        passages=[];propositions=[]
        for name,quote,statement,role in items:
            start=body.index(quote);pid=identity+"."+name
            s=SourceSpan(source_hash=digest(packet),edition=citation+"; decision "+day,
                unit_id=identity,unit_hash=digest(body),locator=name+";unicode:"+str(start),
                start=start,end=start+len(quote),quote=quote,request_hash=digest(QUESTION),role="reasoning")
            passages.append(Passage(pid,s,"Linda Chan J","reasoning",quote))
            propositions.append(Proposition(pid,statement,role,(pid,),
                "Proposed reading of the specified passages, checked against full reasons and disposition; not an independently proved ratio.","proposed"))
        manifest=JudgmentManifest(identity,raw["url"],digest(packet),"Hong Kong Court of First Instance","HK",
            day,"Liquidators' application for directions under section 200(3), with customer-specific terms and facts.",
            ("Linda Chan J, sole reasons; quoted party submissions remain distinct from the court's own conclusion.",),
            ("Complete subsequent treatment","Application to an SFC-authorised product","Source-to-rule transfer","Rendered DOCX fidelity"),True)
        factors=[Factor(identity+".terms","Customer terms and consent",
            "Version of terms, acceptance events, customer class and actual legal relationship matter.",
            tuple(p.proposition_id for p in propositions),
            "These features distinguish the case from a generic token holder or Product Provider.","proposed")]
        moves=[Move("distinction",(factors[0].factor_id,),propositions[0].proposition_id,
            "The litigation concerns cryptocurrency exchange insolvency and the parties' specific terms; it does not interpret paragraph 10 or footnote 5 of 26EC22.","proposed")]
        treatments=[Treatment(identity,None,"unknown",(),None,"unresolved")]
        if identity=="gatecoin-2023":
            treatments.insert(0,Treatment(identity,"gatecoin-2025","followed",
                ("gatecoin-2025.earlier-decision",),"2025-01-24","source-backed"))
        authorities=[]
        for proposition in propositions:
            authority=Authority(proposition.proposition_id,"HK","Court of First Instance",None,None,
                Interval(start=None,end=None),("target-applicability","treatment-completeness"),"unknown")
            authorities.append({"premises":{**asdict(authority),"temporal_scope":authority.temporal_scope.model_dump(mode="json")},"assessment":assess_authority(
                manifest,proposition,authority,treatments,"2026-10-06")})
        check=validate_case(packet,digest(QUESTION),manifest,passages,propositions,factors,moves)
        built.append({"manifest":asdict(manifest),"raw_source":raw,
            "passages":[{**asdict(p),"span":p.span.model_dump(mode="json")} for p in passages],
            "propositions":[asdict(p) for p in propositions],"factors":[asdict(f) for f in factors],
            "moves":[asdict(m) for m in moves],"treatments":[asdict(t) for t in treatments],
            "authority":authorities,"source_check":check})
    # Treatment linkage is checked across cases, separately from validate_case.
    passage_ids={p["passage_id"] for c in built for p in c["passages"]}
    for c in built:
        for treatment in c["treatments"]:
            if not set(treatment["source_ids"])<=passage_ids:raise ValueError("Unbound treatment source")
    return {"question":QUESTION,"packet":packet,"cases":built,
        "unresolved_text_tension":{
            "passages":["gatecoin-2025.classification-8","gatecoin-2025.disposition-95","gatecoin-2025.annexure-issue1"],
            "issue":"Paragraph 8 rejects the seventh scenario as factually absent; paragraph 95 groups scenarios five to seven in an exception statement, and the annexure lists its own classifications. No automatic harmonization or complete classifier is supplied.",
            "status":"OPEN_SOURCE_INTERPRETATION"},
        "rejected_candidate":{"request":"cheung-2009","actual":"Rank Profit Industries Ltd v Secretary for Justice [2009] HKCFA 63",
            "reason":"The hypothesized Cheung citation identifies a different judgment; excluded from Cheung authority."},
        "legal_force_for_26EC22":"NOT_ESTABLISHED","treatment_completeness":"NOT_ESTABLISHED"}
