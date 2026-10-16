"""Optional requirement accounts with prose separate from provision identities.

This contract controls representation only; source warrant is still reviewed.
"""
from copy import deepcopy
import re
from jsonschema import validate as validate_schema
from ..answer_acceptance import MENTION, BRACKET_NUMBER
from ..bounded_context import require

PROFILE = "typed-requirement-account.v1"
REFERENCE_PROTOCOL = "bounded-indexed-assertions.v2"
# Local-only pattern: provider regex dialect support is not assumed. Numbered
# prose is also checked by the existing citation validator.
PROSE_PATTERN = (r"^(?![\s\S]*\b(?:[Pp]\s*\d+|[Pp][Aa][Rr][Aa](?:[Gg][Rr][Aa][Pp][Hh][Ss]?|[Ss]?\.?)\s+\d+|"
    r"[Ff][Nn]\s*\d+|[Ff][Oo][Oo][Tt][Nn][Oo][Tt][Ee]\s+\d+)\b)"
    r"(?![\s\S]*\[\s*\d+(?:\s*[-–,]\s*\d+)*\s*\])[\s\S]+$")
INSTRUCTIONS = (
    "Free prose must contain no numbered paragraph or footnote labels, including hypothetical "
    "and missing-source references. Describe their substantive roles; preserve provision "
    "identities in support, contrary and source_gaps for document-labelled display. Leave "
    "assertion_bindings empty. Preserve every issue. A gap supports no "
    "positive proposition; absence from this window is not absence from the corpus or law.")


def schema():
    from ..bounded_product import NOTE
    value=deepcopy(NOTE)
    prose={"type":"string","minLength":1,"pattern":PROSE_PATTERN}
    value.setdefault("$defs", {})["AccountProse"] = prose
    prose_ref = {"$ref": "#/$defs/AccountProse"}
    value["properties"]["conclusion"]=deepcopy(prose_ref)
    for key in ("assumptions","unresolved"):
        value["properties"][key]["items"]=deepcopy(prose_ref)
    for key in ("condition","consequence"):
        value["properties"]["alternatives"]["items"]["properties"][key]=deepcopy(prose_ref)
    value["properties"]["assertion_bindings"]["maxItems"]=0
    return value


def provider_schema():
    """Keep the historical strict schema local; avoid lookahead on the wire."""
    value = schema()
    value['$defs']['AccountProse'].pop('pattern')
    return value


def select(request, *, input_profile=None, instruction_profile=None, capacity_profile=None, output_profile=None):
    require(request.get("task")=="ASSESS_ORIGINAL_REQUIREMENT", "Account profile outside its declared task")
    value=deepcopy(request)
    value["account_contract"]=PROFILE
    value["response_reference_profile"]=REFERENCE_PROTOCOL
    value["account_instructions"]=INSTRUCTIONS
    if input_profile is not None:
        from .account_input import PROFILE as INPUT_PROFILE
        from .account_encoding import PROFILE as STRUCTURE_PROFILE
        require(input_profile in (INPUT_PROFILE, STRUCTURE_PROFILE), 'Unknown account input profile')
        value['account_input_profile'] = input_profile
    if instruction_profile is not None:
        from .account_instructions import PROFILE as INSTRUCTION_PROFILE
        require(instruction_profile == INSTRUCTION_PROFILE, 'Unknown account instruction profile')
        value['account_instruction_profile'] = instruction_profile
    if capacity_profile is not None:
        from .account_input import validate_capacity
        validate_capacity(value, capacity_profile)
        value['account_capacity_profile'] = capacity_profile
    if output_profile is not None:
        from .account_output import validate_profile
        validate_profile(value, output_profile)
        value['account_output_profile'] = output_profile
    return value


def prose_fields(value):
    yield "/conclusion",value["conclusion"]
    for key in ("assumptions","unresolved"):
        for i,text in enumerate(value[key]):yield "/"+key+"/"+str(i),text
    for i,alternative in enumerate(value["alternatives"]):
        for key in ("condition","consequence"):
            yield "/alternatives/"+str(i)+"/"+key,alternative[key]


def validate(value,product,records):
    validate_schema(value,schema())
    for path,text in prose_fields(value):
        require(not MENTION.search(text) and not BRACKET_NUMBER.search(text),
            "Numbered provision label belongs in typed account evidence: "+path)
    product.citations(value,records)
    require(value["support"] or value["unresolved"],"Unsupported settled account")
    return value


def presentation(value,product,records,*,typed=True):
    """Return exact prose and separately labelled evidence, never inferred law."""
    if typed:
        validate(value,product,records)
    else:
        from ..bounded_product import NOTE
        validate_schema(value, NOTE)
        product.citations(value, records)
    documents={i["index_hash"]:i["source"] for i in product.route.envelope.get("legal_indexes",[])}
    available = {r['id']: r for r in records if r.get('kind') == 'source'}
    labels = []
    for role in ('support', 'contrary'):
        for position, citation in enumerate(value[role]):
            source = available[citation['record_id']]
            owners = []
            for index in product.route.envelope.get('legal_indexes', []):
                if source['unit_id'] not in index['units']:
                    continue
                if citation['locator']:
                    from ..legal_locators import validate_citation
                    from legalmath.errors import LegalMathError
                    try:
                        validate_citation(product.route.envelope['source_packet'], index,
                            unit_id=source['unit_id'], quote=citation['quote'],
                            locator=citation['locator'], root=product.root,
                            expected_index_hash=index['index_hash'])
                    except LegalMathError:
                        continue
                owners.append({'index_hash': index['index_hash'], 'document': deepcopy(index['source'])})
            labels.append({'path': '/' + role + '/' + str(position),
                'source_unit_id': source['unit_id'], 'citation': deepcopy(citation),
                'documents': owners, 'indexed_provision': bool(citation['locator'])})
    return {"profile":PROFILE if typed else "retained-requirement-account.v5",
        "prose":[{"path":p,"text":text} for p,text in prose_fields(value)],
        "support":deepcopy(value["support"]),"contrary":deepcopy(value["contrary"]),
        "evidence_labels":labels,
        "source_gaps":[{**deepcopy(g),"document":deepcopy(documents[g["index_hash"]])} for g in value["source_gaps"]],
        "considered":deepcopy(value["considered"]),"original_account":deepcopy(value),
        "legal_acceptance":False}
