"""Retained-source inventory and individual S2 obligations; no answer labels."""
from copy import deepcopy
from pathlib import Path
import json
import os
import sys
_TASK_ROOT=Path(__file__).resolve().parents[1]
if __name__=="__main__" and Path(sys.prefix)!=_TASK_ROOT/".venv":
    os.execv(str(_TASK_ROOT/".venv/bin/python"),[str(_TASK_ROOT/".venv/bin/python"),"-m","scripts.legal_interpretation_s2_data",*sys.argv[1:]])
os.environ["CUDA_VISIBLE_DEVICES"]="-1"
from legalmath.canonical import digest
from legalmath.interpretation.semantics.records import SourceSpan, Scope, Interval
from legalmath.interpretation.semantics.standards import (
    Standard, Requirement, Assessment, PremiseEvidence, evaluate)
ROOT=Path(__file__).resolve().parents[1]
P0=ROOT/"artifacts/legal-interpretation-program/2026-10-06-offline-v1/P0/attempt-2"
INSPECT=ROOT/"artifacts/legal-interpretation-program/successor-s2/inspection"
UNITS={"p10":"d3b41d4d7e61c.u38.3432","p11":"d3b41d4d7e61c.u41.3664",
 "p14":"d3b41d4d7e61c.u50.4316","p15":"d3b41d4d7e61c.u53.4565",
 "p16":"d3b41d4d7e61c.u56.4803","fn1":"d3b41d4d7e61c.u85.7210",
 "fn5":"d3b41d4d7e61c.u89.8054","ut":"ut-current.parent",
 "intro":"ut-current.intro","securities":"tokenised-securities.circular",
 "appendix":"tokenised-securities.appendix"}
def read(p):return json.loads(p.read_text())
def packet():return read(P0/"packet.json")
def texts(value):return {u["unit_id"]:u["text"] for u in value["units"]}
def catalogue(value):
    result={}
    for unit in value["units"]:
        name=unit["unit_id"]
        if name.startswith("ut-"):
            edition="Retained current UT PDF: January 2019 section markings and October 2024 contents; effective interval unknown"
            provenance="artifacts/assurance-gap-continuation/2026-10-01/authority-sources/ut-current.pdf"
        elif name.startswith("tokenised-securities"):
            edition="23EC52, retained 2 November 2023 circular/Appendix; applicable interval unknown"
            provenance="artifacts/assurance-gap-continuation/2026-10-01/authority-context.json"
        else:
            edition="26EC22, revised 20 April 2026; applicable assessment interval unknown"
            provenance="docs/papers/Circular on tokenisation of SFC-authorised investment products_SFC(2026).json"
        result[name]={"edition":edition,"role":"regulator","provenance":provenance,
            "premise_status":"Retained source assertion; applicability and extraction fidelity remain qualified"}
    return result
def span(value,cat,unit,quote,question):
    text=texts(value)[unit];start=text.find(quote)
    if start<0:raise ValueError("Quote not present in "+unit+": "+quote[:100])
    s=SourceSpan(source_hash=digest(value),edition=cat[unit]["edition"],unit_id=unit,
        unit_hash=digest(text),locator=f"{unit}:unicode:{start}:{start+len(quote)}",
        start=start,end=start+len(quote),quote=quote,request_hash=digest(question),role=cat[unit]["role"])
    s.verify(text,digest(value),digest(question))
    return s
def between(text,start,end):
    i=text.index(start);return text[i:text.index(end,i+len(start))].strip()
def inventory(value):
    cat=catalogue(value);t=texts(value)
    definitions={
     "product-provider":("observed-fact","The assessed entity has the Product Provider role for this product and activity throughout the assessment interval."),
     "intermediary":("observed-fact","The assessed entity acts as intermediary for the specified activity, product and period."),
     "26EC22-applicable":("authority-premise","This retained edition of 26EC22 applies to the entity, product, activity and whole assessment interval, with relevant conditions, amendments and relaxations accounted for."),
     "23EC52-applicable":("authority-premise","This retained edition of 23EC52 applies in the specified intermediary capacity for the whole interval."),
     "ut-applicable":("authority-premise","This retained UT provision applies to this scheme and actor for the whole assessment interval, including actual conditions and relaxations."),
     "p14-request":("observed-fact","An applicable SFC request for paragraph 14 demonstration covers the assessed activity and interval."),
     "p15-request":("observed-fact","An applicable SFC request for paragraph 15 third-party audit or verification covers the assessed activity and interval."),
     "p16-request":("observed-fact","An applicable SFC request for paragraph 16 satisfactory legal opinion covers the application and interval."),
     "register-actor":("observed-fact","The entity is the scheme or, for a unit trust, the trustee or person appointed by that trustee to maintain the register."),
     "register-address-request":("observed-fact","The Commission has made an applicable request for the address where this register is kept."),
     "management-company":("observed-fact","The assessed entity is the management company for this scheme and period."),
     "valuation-outsourced":("observed-fact","A third party is engaged in valuation of this scheme's assets within the scope of UT 6.11C."),
     "issuance-involvement":("observed-fact","The intermediary issues or is substantially involved in issuance of the assessed Tokenised Securities."),
     "dealing-advising-intent":("observed-fact","The Tokenised Securities at issue are securities which this intermediary intends to deal in or advise on."),
     "securities-distribution-role":("observed-fact","The intermediary deals in, advises on or manages portfolios investing in the assessed Tokenised Securities."),
     "before-activity":("observed-fact","The assessment concerns controls before commencement of that identified related activity."),
    }
    rules=[]
    def add(identity,question,consequence,modality,source_specs,keys,warrant,limits):
        interpretation=Requirement(id=identity+".interpretation",kind="inference-premise",
            statement="Assume this source-to-rule interpretation, including its stated trigger, object, standard and applicability transfer: "+warrant)
        rules.append(Standard(id=identity,question=question,consequence=consequence,modality=modality,
            sources=tuple(span(value,cat,UNITS[u],q,question) for u,q in source_specs),
            requirements=tuple(Requirement(id=k,kind=definitions[k][0],statement=definitions[k][1]) for k in keys)+(interpretation,),
            warrant=warrant,limits=tuple(limits)))
    p=lambda k:t[UNITS[k]]
    common=["This derives a conditional duty or responsibility statement, not satisfaction, breach, liability or overall compliance.",
            "The source-to-rule interpretation and supplied premises remain unproved."]
    add("p10-responsibility","Does this scope carry the proposed paragraph 10 retained-responsibility requirement?",
        "Retain ultimate responsibility for management, operational soundness and ownership record keeping regardless of outsourcing.",
        "SHOULD",[("p10",p("p10")),("fn1",p("fn1"))],["26EC22-applicable","product-provider"],
        "Paragraph 10 and footnote 1 support a continuing responsibility requirement; this rule does not select a discharge test.",common+
        ["Allocation, exercised supervision and achieved adequacy remain distinct propositions."])
    add("p11-records","Does the proposed separate paragraph 11 records and compatibility duty apply?",
        "Ensure proper ownership-interest records are maintained and the arrangement is operationally compatible with involved service providers.",
        "SHOULD",[("p11",p("p11"))],["26EC22-applicable","product-provider"],
        "Represent the paragraph 11 requirement separately from paragraph 10 sufficiency.",common+
        ["No definition of proper records, priority of entries or sufficient interoperability evidence is supplied."])
    add("p14-confirmation","Is confirmation required on the proposed paragraph 14 reading?",
        "Confirm management and operational soundness, ownership record keeping and smart-contract integrity to the SFC.",
        "SHOULD",[("p14",p("p14"))],["26EC22-applicable","product-provider"],
        "The inserted request condition attaches to demonstration; confirmation is represented separately.",common)
    add("p14-A-demonstration","Under reading A, is paragraph 14 demonstration triggered?",
        "Demonstrate to the SFC's satisfaction the paragraph 14 subjects: management and operational soundness, ownership record keeping and smart-contract integrity.",
        "SHOULD",[("p14",p("p14")),("fn5",p("fn5"))],["26EC22-applicable","product-provider","p14-request"],
        "Reading A takes the express main-text request condition for demonstration; footnote 5's object and standard remain disputed.",common+
        ["A is a retained proposal, not an authoritative preference over B or C."])
    add("fn5-B-demonstration","Under reading B, is the standing footnote 5 demonstration duty triggered?",
        "Demonstrate at least compliance with paragraphs 10–13 and absence of smart-contract vulnerabilities or security flaws with a high level of confidence.",
        "SHOULD",[("p14",p("p14")),("fn5",p("fn5"))],["26EC22-applicable","product-provider"],
        "Reading B treats the unqualified footnote demonstration wording as standing; the contrary main-text condition is retained.",common+
        ["High confidence is retained as source language; no numerical threshold is invented.",
         "B's attachment premise does not refute A or C."])
    add("fn5-C-demonstration","Under reading C, is request-triggered demonstration of footnote 5 minimum content required?",
        "Demonstrate to the SFC's satisfaction at least compliance with paragraphs 10–13 and absence of smart-contract vulnerabilities or security flaws with a high level of confidence.",
        "SHOULD",[("p14",p("p14")),("fn5",p("fn5"))],["26EC22-applicable","product-provider","p14-request"],
        "Reading C attaches footnote minimum content to the main-text request-triggered demonstration.",common+
        ["A/C trigger agreement is not agreement on object and standard; C is an unresolved interpretive premise."])
    for identity,unit,trigger,consequence in (
        ("p15-audit","p15","p15-request","Obtain third-party audit or verification on management and operational soundness, ownership record keeping and smart-contract integrity."),
        ("p16-opinion","p16","p16-request","Obtain satisfactory legal opinion supporting the application.")):
        add(identity,"Does the separately requested "+identity+" duty apply?",consequence,"SHOULD",
            [(unit,p(unit))],["26EC22-applicable","product-provider",trigger],
            "Preserve this paragraph's own SFC request, activity and object; a different request does not satisfy it.",common)
    register="6.8 The scheme, or in the case of a unit trust, the trustee or the person so appointed by the trustee must maintain a register of holders."
    add("ut68-register","Does the proposed UT 6.8 register-maintenance duty apply?",
        "Maintain the register of holders in the specified register-keeper capacity.","MUST",
        [("ut",register)],["ut-applicable","register-actor"],
        "Preserve the scheme/trustee/appointed-person role disjunction; do not assign every Product Provider this role.",common+
        ["UT 6.8 supplies neither general delegation permission nor a governing ownership priority rule."])
    add("ut68-register-address","Does the proposed UT 6.8 requested-address duty apply?",
        "Advise the Commission of the address where the register is kept.","MUST",
        [("ut",register+" The Commission must be advised on request of the address(es) where the register is kept.")],
        ["ut-applicable","register-actor","register-address-request"],
        "Keep the requested register-address disclosure distinct from continuous register maintenance.",common)
    valuation=between(p("ut"),"6.11C ","Valuation of unquoted securities")
    add("ut611c-selection","Does the proposed mandatory third-party valuation selection and monitoring duty apply?",
        "Exercise reasonable care, skill and diligence in selecting, appointing and monitoring the valuation third party, including the stated knowledge, experience and resources criterion.","MUST",
        [("ut",valuation)],["ut-applicable","management-company","valuation-outsourced"],
        "Conditionally render the first sentence's shall as MUST, preserving its valuation-specific actor and activity.",common+
        ["No general tokenisation adequacy test follows from this valuation provision."])
    add("ut611c-valuation","Does the proposed valuation-outsourcing supervision and review duty apply?",
        "Subject the third party's valuation activities to ongoing supervision and periodic review by the management company.","SHOULD",
        [("ut",valuation)],["ut-applicable","management-company","valuation-outsourced"],
        "The second sentence uses should for supervision and review; keep it separate from the first sentence's shall.",common+
        ["Valuation review periods cannot supply a general tokenisation supervision cadence."])
    issuance=between(p("securities"),"13. Where intermediaries issue","14. In assessing")
    add("securities13-responsibility","Does the proposed issuance responsibility rule apply in this intermediary capacity?",
        "Remain responsible for the overall tokenisation operation notwithstanding outsourcing.","DESCRIPTIVE",
        [("securities",issuance)],["23EC52-applicable","intermediary","issuance-involvement","dealing-advising-intent"],
        "Retain both issuance involvement and intention to deal in or advise on the specified securities.",common+
        ["This role-specific rule does not prove paragraph 10 discharge or general liability."])
    controls=between(p("securities"),"17. Where intermediaries deal","E. Information for clients")
    add("securities18-controls","Does the proposed pre-activity controls assessment duty apply?",
        "Understand and be satisfied with issuer and vendor controls for ownership and technology risks before the related activity.","SHOULD",
        [("securities",controls)],["23EC52-applicable","intermediary","securities-distribution-role","before-activity"],
        "Read paragraph 18 within paragraph 17's dealing, advising and portfolio activities.",common+
        ["The Appendix is non-exhaustive and supplies no automatic sufficiency or cadence threshold."])
    return cat,rules
def source_findings(value,cat):
    t=texts(value)
    specs=[
     ("ut-code-force","intro","This UT Code does not have the force of law.",
      "Code status is not statutory liability; actual authorization conditions and underlying law remain necessary."),
     ("ut-modifications","intro","The Commission may modify or relax the application of a requirement in this UT Code",
      "Power to modify is not proof that this scheme has a modification or waiver."),
     ("ut-transition","intro","Any change or amendment to this UT Code will be made known to the industry and transitional periods for compliance will be allowed where necessary.",
      "No actual commencement, transition date or retrospective cure rule is established."),
     ("ut-liability","ut",between(t[UNITS["ut"]],"6.6 The constitutive","Changes to scheme documentation"),
      "The restriction on exemption/indemnity does not supply the underlying liability test."),
     ("appendix-nonexhaustive","appendix","List of non-exhaustive factors",
      "Relevant considerations cannot be promoted into exhaustive necessary-and-sufficient adequacy criteria."),
     ("appendix-title","appendix","whether the ownership interest of the underlying assets of the Tokenised Securities are legally valid under the applicable governing laws",
      "Title and extrinsic rights still require governing law, constitutive documents and actual transactions."),
     ("appendix-reconciliation","appendix","whether there are regular reconciliations between the records for the extrinsic rights and the records for the distributed ledger tokens",
      "A reconciliation observation alone does not establish proper records or resolve conflicting title."),
     ("appendix-remediation","appendix","any adverse incidents relating to the DLT used and whether they have been resolved",
      "Incident resolution is relevant but does not supply a materiality threshold or retrospective cure."),
     ("appendix-migration","appendix","redeployment plans to migrate DLT-related records to a different blockchain",
      "Migration planning does not allocate responsibility through provider succession or fix retention horizons."),
     ("securities-existing-law","securities","the existing legal and regulatory requirements governing the traditional securities markets continue to apply to Tokenised Securities.",
      "A tokenisation wrapper does not replace underlying law; exact applicable law still needs to be supplied."),
    ]
    return [{"id":identity,"source":span(value,cat,UNITS[unit],quote,identity).model_dump(mode="json"),
        "finding":finding,"status":"SOURCE_ASSERTION_WITH_LIMITS"} for identity,unit,quote,finding in specs]
def obligation_ledger(value,cat,rules):
    original=read(P0/"obligation-map.json")
    joined={r["obligation"]["obligation_id"]:r for r in read(INSPECT/"obligations.json")}
    allowed={r.id for r in rules};out=[]
    for i,row in enumerate(original,1):
        obligation=row["obligation"];oid=obligation["obligation_id"];responses=joined[oid]["responses"]
        if not responses:raise ValueError("Dropped original obligation "+oid)
        evidence=[];needs=[]
        for response in responses:
            for quote in response["response"]["evidence"]:
                s=span(value,cat,quote["unit_id"],quote["quote"],oid).model_dump(mode="json")
                if s not in evidence:evidence.append(s)
            for need in response["response"]["needed_evidence"]:
                if need not in needs:needs.append(need)
        dim=obligation["dimension"]
        related={"time":["p10-responsibility"],"definition":["p10-responsibility","p11-records"],
            "authority":["ut68-register","securities13-responsibility"],
            "output":["p10-responsibility","p11-records"]}[dim]
        if any("request" in n.lower() or "footnote" in n.lower() for n in needs) or i in (4,10,21,42):
            related += ["p14-confirmation","p14-A-demonstration","fn5-B-demonstration","fn5-C-demonstration"]
        if i in (43,45,46):related += ["securities18-controls"]
        if not set(related)<=allowed:raise ValueError("Unknown rule")
        disposition={
          "time":"Continuity is sourced. Full-period applicability, actual assessment boundaries, provider succession and the legal effect of recovery remain missing.",
          "definition":"Separate duties and conduct factors are sourced. They do not select allocation, exercised supervision or achieved adequacy as the paragraph 10 discharge standard.",
          "authority":"Source bytes are retained. Scheme-specific authorization, dated incorporation, actor capacity, underlying law and applicable treatment remain unresolved.",
          "output":"Conditional duties can be computed. Neither the source factors nor computation supplies sufficient legal discharge or actual factual evidence."}[dim]
        out.append({"ordinal":i,"original":deepcopy(row),"original_hash":digest(row),
            "obligation_id":oid,"role_responses":deepcopy(responses),"source_assertions":evidence,
            "relevant_conditional_rules":sorted(set(related)),
            "missing_premises":[{"id":f"{oid}.missing.{n}","statement":s,"status":"UNRESOLVED",
                "origin":"retained operative role response"} for n,s in enumerate(needs,1)],
            "authority_search":"Two official Gatecoin judgments supply limited property/terms/consent context; neither resolves paragraph 10, footnote 5 or the target-specific authority and facts. Complete treatment and Cheung reasons remain unestablished.",
            "case_context":["gatecoin-2023","gatecoin-2025"],
            "disposition":disposition,"status":"OPEN_QUALIFIED","closure_evidence":None})
    if len(out)!=46 or len({r["obligation_id"] for r in out})!=46:raise ValueError("Wrong obligation denominator")
    return out
def example_assessment(known=True):
    return Assessment(scope=Scope(actor="provider-A",product="fund-A",component="register-A",activity="tokenisation",
        interval=Interval(start="2026-04-20" if known else None,end="2026-04-30" if known else None)),
        provider="operator-A",jurisdiction="HK",known_by="2026-05-01" if known else None)
def supplied(rule,assessment):
    return tuple(PremiseEvidence(id=rule.id+".evidence."+str(i),requirement_id=req.id,
        kind=req.kind,positive=True,scope=assessment.scope,provider=assessment.provider,
        jurisdiction=assessment.jurisdiction,known_on="2026-04-30",evidence_hash=digest({"fixture":rule.id,"premise":req.id}),
        basis="Synthetic declared premise for deterministic development; not actual provider evidence.",
        dependencies=(),admission="synthetic") for i,req in enumerate(rule.requirements))
def development_cases(value,cat,rules):
    assessment=example_assessment();cases=[]
    for rule in rules:
        positive=supplied(rule,assessment)
        variants=[("missing-all",()),("all-declared",positive),("missing-interpretation",positive[:-1]),
            ("negative-required-premise",(positive[0].model_copy(update={"positive":False}),)+positive[1:]),
            ("conflicting-premise",positive+(positive[0].model_copy(update={"id":rule.id+".contrary","positive":False}),)),
            ("wrong-provider",tuple(e.model_copy(update={"provider":"operator-B"}) for e in positive)),
            ("partial-period",tuple(e.model_copy(update={"scope":e.scope.model_copy(update={"interval":Interval(start="2026-04-25",end="2026-04-30")})}) for e in positive)),
            ("source-assertion-only",tuple(e.model_copy(update={"kind":"source-assertion"}) for e in positive))]
        for label,evidence in variants:
            result=evaluate((rule,),value,cat,assessment,evidence)
            expected="CONDITIONALLY_DERIVED" if label=="all-declared" else "NOT_DERIVED"
            if result["results"][0]["status"]!=expected:raise ValueError("Development obligation failed")
            cases.append({"id":rule.id+"/"+label,"standards":[rule.id],"assessment":assessment.model_dump(mode="json"),
                "evidence":[e.model_dump(mode="json") for e in evidence],"receipt":result})
    return cases
if __name__=="__main__":
    value=packet();cat,rules=inventory(value)
    ledger=obligation_ledger(value,cat,rules);findings=source_findings(value,cat)
    print(json.dumps({"rules":len(rules),"obligations":len(ledger),"source_findings":len(findings),
        "valuation_quote":next(r.sources[0].quote for r in rules if r.id=="ut611c-valuation")},ensure_ascii=False))
