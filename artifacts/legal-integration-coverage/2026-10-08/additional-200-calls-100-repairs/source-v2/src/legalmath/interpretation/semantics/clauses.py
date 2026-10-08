"""Finite source-bound proposals, not an English-to-law decision procedure."""
from .records import Branch, Clause, Interval, Premise, Scope, SourceSpan, Settings
from ...canonical import digest


def span(packet, question, needle, locator):
    units = [u for u in packet["units"] if needle in u["text"]]
    if len(units) != 1:
        raise ValueError("Missing or ambiguous source: " + locator)
    unit = units[0]
    return SourceSpan(source_hash=digest(packet), edition="retained-edition; applicability unresolved",
        unit_id=unit["unit_id"], unit_hash=digest(unit["text"]), locator=locator,
        start=0, end=len(unit["text"]), quote=unit["text"], request_hash=digest(question), role="regulator")


def premise(identity, statement, *dependencies):
    return Premise(id=identity, statement=statement, status="unresolved", dependencies=dependencies)


def propose(packet, question, retained_proposals, policy):
    """Nominate two declared pilot families and preserve every retained proposal.

    This profile intentionally rejects unrelated packets. Nominations are not
    attributed to a model: cited retained readings supply motivation only.
    """
    settings = policy if isinstance(policy, Settings) else Settings.model_validate_json(__import__("json").dumps(policy))
    if not retained_proposals:
        raise ValueError("Retained proposal inventory is required")
    markers = {
        "p10": "ultimately responsible", "fn1": "1 Given that",
        "p14": "confirm and, upon SFC", "fn5": "at a minimum, they comply",
        "p15": "obtain third party audit", "p16": "obtain satisfactory legal opinion",
    }
    sources = {key: span(packet, question, needle, key) for key, needle in markers.items()}
    for key, identity in (("ut6.8", "ut-current.parent"), ("appendix-A", "tokenised-securities.appendix")):
        unit = next((u for u in packet["units"] if u["unit_id"] == identity), None)
        if unit is None:
            raise ValueError("Missing cross-reference: " + identity)
        sources[key] = span(packet, question, unit["text"], key)
    relations = (premise("applicability.ut6.8", "UT 6.8 applicability unresolved", sources["ut6.8"].identity()),
                 premise("applicability.appendix-A", "Appendix Part A applies where applicable; scope unresolved", sources["appendix-A"].identity()))
    attachment = premise("fn5.attachment", "Trigger, object and standard attachment of footnote 5 remains disputed", sources["p14"].identity(), sources["fn5"].identity())
    scope = Scope(actor="Product Provider", activity="tokenisation", product=None, component=None,
                  interval=Interval(start=None, end=None))

    def clause(identity, action, trigger, object_, standard, source_keys, assumptions=(), rel=()):
        return Clause(id=identity, actor="Product Provider", action=action, modality="SHOULD",
            trigger=trigger, object=object_, standard=standard, scope=scope,
            sources=tuple(sources[k] for k in source_keys), relations=rel, assumptions=assumptions,
            warrant="Proposed decomposition of the cited source; quotation integrity does not establish this interpretation.")

    common = (
        clause("confirmation", "confirm", "standing", "management/operational soundness; ownership records; contract integrity",
               "fn5 relation unresolved", ("p14", "fn5"), rel=(attachment,)),
        clause("verification", "obtain third party audit or verification", "sfc_request", "soundness; records; integrity",
               "paragraph 15", ("p15",)),
        clause("opinion", "obtain legal opinion", "sfc_request", "application", "satisfactory", ("p16",)),
    )
    branches = []
    for label, trigger, obj, standard in (
        ("A", "sfc_request", "p14 soundness; ownership records; smart-contract integrity", "SFC satisfaction; fn5 attachment unresolved"),
        ("B", "standing", "fn5 minimum compliance with paragraphs 10–13; no vulnerabilities/security flaws", "high level of confidence; SFC satisfaction relation unresolved"),
        ("C", "sfc_request", "fn5 minimum compliance with paragraphs 10–13; no vulnerabilities/security flaws", "high level of confidence; inherits p14 trigger; SFC satisfaction relation unresolved"),
    ):
        assumption = Premise(id="assume."+label, statement="Conditionally adopt demonstration variant "+label,
                             status="declared", dependencies=(attachment.id,))
        branches.append(Branch(proposal_id="demonstration."+label, source_hash=digest(packet), question_hash=digest(question),
            legacy_reading_hash=None, clauses=common+(clause("demonstration", "demonstrate", trigger, obj, standard,
            ("p14", "fn5"), (assumption,), (attachment,)),), settings=settings, assumptions=(assumption,),
            origin="sourced-development-nomination", unresolved=(attachment,)))
    for name, dimensions in (("allocation", ("allocation",)), ("conduct", ("conduct",)),
                             ("adequacy", ("adequacy",)), ("combined", ("allocation", "conduct", "adequacy"))):
        assumption = Premise(id="assume."+name, statement="Conditionally read responsibility as "+name,
                             status="declared", dependencies=tuple(r.id for r in relations))
        branches.append(Branch(proposal_id="responsibility."+name, source_hash=digest(packet), question_hash=digest(question),
            legacy_reading_hash=None, clauses=tuple(clause(d, d, "standing", "tokenisation arrangement and ownership records",
                "ultimately responsible (p10); fully responsible (fn1); no liability rule supplied",
                ("p10", "fn1", "ut6.8", "appendix-A"), (assumption,), relations) for d in dimensions),
            settings=settings, assumptions=(assumption,), origin="sourced-development-nomination", unresolved=relations))
    retained = []
    for row in retained_proposals:
        reading = row.get("operative", {}).get("original_reading", row)
        citations = reading.get("citations", [])
        matches = sorted({s.locator for s in sources.values() for c in citations if c.get("unit_id") == s.unit_id})
        retained.append({"identity": digest(row), "reading_id": row.get("reading_id", reading.get("local_id")),
                         "motivating_source_relations": matches, "original": row,
                         "disposition": "Retained in full; no exact equivalence to a new nomination asserted"})
    return {"profile": "sfc-two-pilots.v1", "source_hash": digest(packet), "question_hash": digest(question),
            "branches": [b.model_dump(mode="json") for b in branches], "retained": retained,
            "unrepresented_concerns": ["All retained proposals require individual semantic reconciliation",
                "Quantifiers, exceptions, further attachments and additional authority are not exhaustively enumerated",
                "No evaluative standard is derived from a numerical confidence threshold"],
            "complete_english_inventory": False}


def distinguishing_assignments(branches):
    """Small conditional domain; no supplied factual or legal answer labels."""
    rows = []
    for request in (False, True):
        for branch in branches:
            c = next((c for c in branch.clauses if c.id == "demonstration"), None)
            if c:
                rows.append({"branch_id": branch.identity(), "proposal_id": branch.proposal_id,
                    "sfc_request": request, "demonstration_trigger": request if c.trigger == "sfc_request" else True,
                    "object": c.object, "standard": c.standard, "status": "CONDITIONAL"})
    return rows


def controlled_english(branch):
    return "\n".join(f"{c.actor} {c.modality} {c.action} concerning {c.object}; trigger: {c.trigger}; standard: {c.standard}."
                     for c in branch.clauses)
