"""Offline S3 development inputs and retained-text CompleteInvestigation exercise."""
from copy import deepcopy
from pathlib import Path
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
from legalmath.canonical import canonical, digest, loads, raw_digest
from legalmath.interpretation.semantics.records import SourceSpan, Interval, Premise
from legalmath.interpretation.semantics.standards import Requirement, Standard, PremiseEvidence
from legalmath.interpretation.semantics.scoped_standards import (
    Inputs, Document, Event, Attachment, recorded_requirement, compute)
from scripts.legal_interpretation_s2_data import packet, inventory, example_assessment

ROOT = Path(__file__).resolve().parents[1]
SLICE = "Retained SFC excerpts: conditional duties and unresolved standards"
DATE = "2026-04-30"
AT = "2026-04-30T00:00:00.000000Z"
BRANCH_RULES = {"A": "p14-A-demonstration", "B": "fn5-B-demonstration", "C": "fn5-C-demonstration"}


def diagnostic_rules(base):
    """Source-informed development hypotheses, expressly not new legal holdings."""
    source_rule = base[0]
    specs = (
        ("supervision", ("supervision",), "A supervision event supplies adequate supervision"),
        ("remediation", ("remediation",), "A remediation event cures the earlier incident"),
        ("reconciliation", ("reconciliation",), "A reconciliation event establishes proper records"),
        ("ledger-access", ("ledger-entry", "customer-access"), "A ledger entry establishes customer access"),
        ("terms-acceptance", ("terms-change", "terms-acceptance"), "Changed terms have been accepted"),
        ("relationship", ("trust-relationship",), "A recorded relationship establishes the assessed duty"),
    )
    result = []
    authority = next(r for r in source_rule.requirements if r.kind == "authority-premise")
    for name, kinds, claim in specs:
        question = "Does this expressly assumed diagnostic implication follow: " + claim + "?"
        sources = tuple(s.model_copy(update={"request_hash": digest(question)}) for s in source_rule.sources)
        result.append(Standard(id="diagnostic." + name, question=question,
            consequence="Conditional diagnostic hypothesis only: " + claim, modality="DESCRIPTIVE",
            sources=sources, requirements=(authority,
                Requirement(id="diagnostic." + name + ".sufficiency", kind="inference-premise",
                    statement="Assume a separately justified sufficient rule for this scope: " + claim)) +
                tuple(recorded_requirement(k) for k in kinds),
            warrant="Synthetic challenge motivated by S2 source distinctions; the quoted legal text does not establish this implication.",
            limits=("Not an admitted legal interpretation or a sufficient discharge test.",
                    "Source-to-rule sufficiency and actual evidence truth remain unresolved.")))
    return result


def inputs_for(source, cat, rules, attachments=()):
    assessment = example_assessment()
    docs = {}
    def document(text):
        doc = Document(text=text, sha256=raw_digest(text.encode()))
        docs[doc.sha256] = doc
        return doc.sha256
    definitions = {r.id: r for s in rules for r in s.requirements}
    evidence = []
    for name, req in definitions.items():
        if name.startswith(("recorded.", "diagnostic.")) or name == "p16-request":
            continue
        positive = name != "p14-request"
        evidence.append(PremiseEvidence(id="declared." + name, requirement_id=name, kind=req.kind,
            positive=positive, scope=assessment.scope, provider=assessment.provider,
            jurisdiction=assessment.jurisdiction, known_on=DATE,
            evidence_hash=document("SYNTHETIC declaration (" + str(positive) + "): " + req.statement),
            basis="Declared development premise, not client evidence or an answer label.",
            dependencies=(), admission="synthetic"))
    p10 = next(e for e in evidence if e.requirement_id == "p10-responsibility.interpretation")
    evidence.append(p10.model_copy(update={"id": "contrary.p10", "positive": False,
        "evidence_hash": document("SYNTHETIC contrary to paragraph 10 interpretation.")}))
    p16 = definitions["p16-request"]
    evidence.append(PremiseEvidence(id="wrong-party.p16", requirement_id=p16.id, kind=p16.kind,
        positive=True, scope=assessment.scope.model_copy(update={"actor": "provider-C"}),
        provider=assessment.provider, jurisdiction=assessment.jurisdiction, known_on=DATE,
        evidence_hash=document("SYNTHETIC paragraph 16 request for provider-C."),
        basis="Different actor; must be excluded.", dependencies=(), admission="synthetic"))
    observations = []
    for name, kind in (("supervision", "supervision"), ("remediation", "remediation"),
            ("reconciliation", "reconciliation"), ("ledger", "ledger-entry"),
            ("changed-terms", "terms-change"), ("other-relationship", "trust-relationship")):
        event = Event(id=name, kind=kind, positive=True, scope=assessment.scope,
            provider=assessment.provider, jurisdiction=assessment.jurisdiction,
            event=Interval(start="2026-04-25", end="2026-04-25"), known_on=DATE,
            evidence_hash=document("SYNTHETIC recorded event: " + name), admission="synthetic")
        if name == "remediation":
            event = event.model_copy(update={"known_on": "2026-05-02"})
        elif name == "reconciliation":
            event = event.model_copy(update={"scope": event.scope.model_copy(update={
                "interval": Interval(start="2026-04-25", end=DATE)})})
        elif name == "other-relationship":
            event = event.model_copy(update={"scope": event.scope.model_copy(update={"actor": "provider-C"})})
        observations.append(event)
    negative = observations[0].model_copy(update={"id": "negative-without-completeness", "positive": False})
    observations.append(negative)
    return Inputs(packet_hash=digest(source), catalogue=cat, standards=tuple(rules),
        assessment=assessment, documents=tuple(docs.values()), observations=tuple(observations),
        premises=tuple(evidence), attachments=tuple(attachments)).model_dump(mode="json")


def retained_inputs():
    source = packet()
    cat, base = inventory(source)
    rules = base + diagnostic_rules(base)
    return source, inputs_for(source, cat, rules)


def projection():
    """Exact quote projection; this is not represented as an original HTTP body."""
    from legalmath.interpretation.assurance.sources import acquire_context, packet_from_context
    original = packet()
    catalogue, rules = inventory(original)
    unique = list(dict.fromkeys(s.quote for rule in rules for s in rule.sources))
    if any("\n" in q for q in unique):
        raise ValueError("Projection requires indivisible retained paragraphs")
    document = {"url": "https://www.sfc.hk/test/s3-retained-excerpts",
        "media_type": "text/plain", "data": "\n".join(unique).encode()}
    actual = packet_from_context(acquire_context([document]), SLICE)
    newcat = {}
    rebound = []
    provenance = []
    for rule in rules:
        spans = []
        for old in rule.sources:
            unit = next(u for u in actual["units"] if u["text"] == old.quote)
            newcat[unit["unit_id"]] = deepcopy(catalogue[old.unit_id])
            span = SourceSpan(source_hash=digest(actual), edition=old.edition,
                unit_id=unit["unit_id"], unit_hash=digest(unit["text"]),
                locator=unit["locator"], start=0, end=len(unit["text"]), quote=unit["text"],
                request_hash=digest(rule.question), role=old.role)
            spans.append(span)
            provenance.append({"rule_id": rule.id, "original": old.model_dump(mode="json"),
                "projected": span.model_dump(mode="json"), "relation": "EXACT_QUOTED_TEXT; locally assembled projection"})
        rebound.append(rule.model_copy(update={"sources": tuple(spans)}))
    return document, actual, newcat, rebound, provenance


def reading(source, letter):
    ids = {u["text"]: u["unit_id"] for u in source["units"]}
    _, original = inventory(packet())
    rule = next(r for r in original if r.id == BRANCH_RULES[letter])
    citations = [{"unit_id": ids[s.quote], "quote": s.quote} for s in rule.sources]
    return {"local_id": "demonstration." + letter.lower(), "family": "scope",
        "subject": "Proposed demonstration reading " + letter,
        "statement": "[TRUE_IS_SATISFIED] " + rule.question,
        "distinction": rule.warrant, "citations": citations,
        "assumptions": ["Source-to-rule interpretation, applicability and factual classification remain unresolved."],
        "questions": ["What source-grounded premise establishes this attachment and sufficient standard?"],
        "formalization": {"facts": [{"name": "requested", "type": "bool",
            "meaning": "An applicable paragraph 14 demonstration request is supplied",
            "unit": "truth value", "source_unit_ids": [citations[0]["unit_id"]], "requires_judgment": True}],
            "scope": "true", "result": "true" if letter == "B" else "requested", "result_type": "bool"}}


def question(source, letter):
    r = reading(source, letter)
    return {"control_id": "demonstration." + letter.lower(), "question": r["statement"],
        "unit_of_assessment": "specified product, provider, activity and assessment interval",
        "actor": "Product Provider", "temporal_basis": "declared development assessment",
        "result_kind": "DUTY_TRIGGER", "true_means": "the proposed demonstration trigger follows conditionally",
        "false_means": "the supplied trigger does not follow; no opposite legal conclusion",
        "source_evidence": r["citations"]}


def responder(request):
    """Deterministic transport fixture; no quality judgment is established."""
    from legalmath.interpretation.search.models import DIMENSIONS
    task = request.get("original_task", request["task"])
    source = request["source_packet"]
    quotes = reading(source, "A")["citations"]
    if task == "SOURCE_INVENTORY":
        return {"claims": [{"claim_id": "demonstration", "kind": "OBLIGATION",
            "actor": "Product Provider", "action": "demonstrate", "modality": "SHOULD",
            "conditions": ["request attachment unresolved"], "exceptions": [], "temporal": [],
            "statement": "Paragraph 14 and footnote 5 leave the proposed trigger/object readings for investigation.",
            "relevance": "CONTROL", "evidence": quotes, "uncertainty": ["A/B/C are proposals."]}],
            "units": [{"unit_id": u["unit_id"], "disposition": "CLAIMS" if u["unit_id"] in {q["unit_id"] for q in quotes} else "CONTEXT",
                "claim_ids": ["demonstration"] if u["unit_id"] in {q["unit_id"] for q in quotes} else [],
                "rationale": "Retained exact excerpt; completeness of source coverage is not established."} for u in source["units"]],
            "authorities": [], "uncertainties": ["Actual authority and sufficient standards are missing."]}
    if task in ("GENERATE", "SEMANTIC_REPAIR", "REFINE"):
        return {"readings": [reading(source, l) for l in BRANCH_RULES],
            "dimensions": [{"dimension": d, "status": "AMBIGUOUS",
                "source_unit_ids": [q["unit_id"] for q in quotes], "explanation": "Declared alternatives only."} for d in DIMENSIONS],
            "coverage": [{"unit_id": u["unit_id"], "status": "CONTEXT", "reason": "Retained scoped development source."} for u in source["units"]],
            "questions": ["Applicability and source interpretation remain unresolved."]}
    if task == "DEFINE_EXACT_QUESTIONS":
        return {"assignments": [{"candidate_id": cid, "assignment_status": "PROPOSED",
            "question": question(source, r["local_id"][-1].upper())} for cid, r in request["candidates"].items()]}
    if task == "SOURCE_FIDELITY":
        return {"checks": [{"claim_id": c["claim_id"], "candidate_id": r["candidate_id"],
            "label": "NOT_ESTABLISHED", "source_evidence": quotes, "representation_quotes": [r["representation"]],
            "rationale": "Declared transport fixture; legal meaning is unproved.",
            "failing_stage": "INTERPRETATION", "question": "Which attachment is supported?"}
            for c in request["claims"] for r in request["candidates"]
            if request.get("required_pairs") is None or {"claim_id": c["claim_id"], "candidate_id": r["candidate_id"]} in request["required_pairs"]],
            "additional_concerns": []}
    if task == "STRUCTURED_CRITICISM":
        return {"arguments": [{"argument_id": "argument." + str(i), "candidate_id": cid,
            "premises": [], "parents": [], "inference_id": "rule." + str(i), "inference_kind": "DEFEASIBLE",
            "inference": "Proposed source reading; authority remains unresolved.",
            "conclusion": {"atom": "proposed." + str(i), "negative": False}, "evidence": quotes}
            for i, cid in enumerate(request["candidates"])],
            "attacks": [], "preferences": [], "cases": [], "case_queries": [], "questions": []}
    if task == "SCOPED_SOURCE_FIDELITY":
        # Reuse only the fixture's validated response shape, retaining explicit uncertainty.
        from tests.assurance.test_successor_workflow import complete_responder
        result = complete_responder(request)
        for row in result["checks"]:
            row["source_support"]["rationale"] = "Synthetic transport assertion; not legal quality evidence."
            row["question_relation"]["rationale"] = "Declared question association."
            row["executable_correspondence"]["rationale"] = "Declared trigger only; object/standard interpretation unresolved."
            row["followup_questions"] = ["Establish the source-to-rule and attachment premises."]
        return result
    raise AssertionError(task)


def product_inputs():
    document, source, cat, base, provenance = projection()
    rules = base + diagnostic_rules(base)
    common = tuple(r.id for r in rules if r.id not in BRANCH_RULES.values())
    attached = tuple(Attachment(id="attachment." + l, reading_hash=digest(reading(source, l)),
        question_hash=digest(question(source, l)), rule_ids=common + (BRANCH_RULES[l],),
        warrant="Proposed comparison preserving the distinct A/B/C objects and standards; no equivalence to Java trigger asserted.")
        for l in BRANCH_RULES)
    return document, source, inputs_for(source, cat, rules, attached), provenance


def runner_for(directory):
    from tests.search.support import FunctionProvider
    from tests.assurance.test_integration import settings
    from tests.catala.backend_support import TOOLCHAIN
    from scripts.legal_interpretation_demo import options
    from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation
    selected = options(2)
    selected["profile"] = "legalmath.semantic-investigation.v3"
    return CompleteInvestigation(ROOT, directory, FunctionProvider(responder),
        ROOT / ".localresources/java-toolchain/jdk-17.0.20.1+1", AT,
        settings=settings(), maximum_scoped_actions=12, scoped_rounds=1,
        machine_qualification=True, catala=TOOLCHAIN, semantic_options=selected)


def execute_product(directory):
    document, source, inputs, provenance = product_inputs()
    runner = runner_for(directory)
    return runner, runner.run([document], SLICE, semantic_inputs=inputs), provenance
