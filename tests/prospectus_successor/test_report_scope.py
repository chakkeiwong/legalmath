"""Report scope must reach the consumer without changing contractual answers."""
from copy import deepcopy

import pytest

from legalmath.prospectus.successor import report_scope, service
from legalmath.prospectus.successor.contracts import digest
from test_successor import request

REVIEW = {"kind": "DEVELOPMENT", "reviewer": "synthetic-reader", "reason": "Explicit synthetic report"}
TEXT = "\n".join([
    "Independent Limited Assurance Report", "Sustainability information for 2010.",
    "Limited assurance provides a lower level of assurance.", "ISAE 3000 and AA1000APS (2008).",
    "Nothing has come to our attention indicating material misstatement.",
    "To the Executive Board of GBES.", "Solely to GBES and for no other purpose.",
    "We accept no responsibility to other third parties.",
    "Free translation from Portuguese; the Portuguese version prevails.", "Lisbon, 4 March 2011.",
])


def fixture(tmp_path):
    req = request(tmp_path, [TEXT])
    req.pop("assembly")
    req.pop("scope")
    p1 = service.source_product(req, tmp_path)
    graph = p1["payload"]["graph"]
    text = "\n".join(u["raw"] for u in graph["units"])
    spec = {"version": "source-report-readings.v1", "graph_sha256": digest(graph), "review": REVIEW,
            "reports": [{"id": "r", "document": "d", "source_sha256": req["bundle"]["documents"][0]["sha256"],
                         "pages": [{"page": 1, "mode": "raw"}], "text_sha256": digest(text.encode())}]}
    req["source_report_readings"] = spec
    p1 = service.source_product(req, tmp_path)
    p2 = service.construction_product(p1, tmp_path)
    selected = p2["payload"]["source_report_readings"]
    facts = {key: {"status": "UNKNOWN", "reason": "Not established by synthetic report"} for key in report_scope.FACTS}
    names = ["identity", "subject", "assurance_level", "criteria", "conclusion", "addressee",
             "purpose", "reliance_limits", "translation_priority", "report_date"]
    codes = {"identity": "LIMITED_SUSTAINABILITY_ASSURANCE", **report_scope.PROFILES["LIMITED_SUSTAINABILITY_ASSURANCE"]}
    for name, quote in zip(names, TEXT.splitlines()):
        start = text.index(quote)
        facts[name] = {"status": "SUPPLIED", "spans": [{"start": start, "end": start + len(quote), "quote": quote}],
                       **({"value": codes[name]} if name in codes else {})}
    scope = {"version": "source-report-scope.v1", "readings_sha256": digest(selected), "review": REVIEW,
             "reports": [{"id": "r", "reading_sha256": selected["reports"][0]["sha256"], "facts": facts}]}
    return req, p1, p2, scope


def products(p1, p2, scope=None):
    p3 = service.interpretation_product(p1, p2, {"source_report_scope": scope} if scope else None)
    return {"P1": p1, "P2": p2, "P3": p3, "P4": service.law_product(p1, p3),
            "P5": service.financial_product(p1, p2, p3)}


def test_actual_consumer_report_scope_changes_explanation_not_debt_answers(tmp_path):
    req, p1, p2, scope = fixture(tmp_path)
    baseline = deepcopy(req)
    baseline.pop("source_report_readings")
    before = service.assess(baseline, tmp_path)
    after = service.consume(products(p1, p2, scope), tmp_path, include_artifacts=True, mode="current")
    assert before["questions"] == after["questions"]
    assert before["assembly"] == after["assembly"]
    assert before["dependencies"] == after["dependencies"]
    assert "source_reports" not in before
    report, = after["source_reports"]
    assert report["status"] == "CONDITIONAL_SUPPLIED_READING"
    assert report["use_assessment"]["limited_sustainability_assurance"] == "SUPPLIED_SOURCE_SUPPORT"
    assert report["use_assessment"]["financial_statement_audit_opinion"] == "NOT_ESTABLISHED_BY_THIS_READING"
    assert report["use_assessment"]["bond_repayment_or_conversion"] == "NOT_ESTABLISHED_BY_THIS_READING"
    assert report["use_assessment"]["unrestricted_third_party_reliance"] == "EXPRESS_LIMIT_RETAINED"
    assert set(report_scope.EXTERNAL) <= set(report["unresolved"])
    assert after["mode"] == "ASSISTED" and not after["independent_legal_acceptance"]
    req["source_report_scope"] = scope
    assert service.assess(req, tmp_path)["source_reports"] == after["source_reports"]


@pytest.mark.parametrize("field", ["subject", "assurance_level", "conclusion", "purpose", "reliance_limits"])
def test_unknown_qualification_withholds_complete_scope_finding(tmp_path, field):
    _, p1, p2, scope = fixture(tmp_path)
    scope["reports"][0]["facts"][field] = {"status": "UNKNOWN", "reason": "Unavailable qualification"}
    report, = service.consume(products(p1, p2, scope), tmp_path)["source_reports"]
    assert report["status"] == "INCOMPLETE_SOURCE_READING"
    assert report["use_assessment"]["limited_sustainability_assurance"] == "NOT_ESTABLISHED_BY_THIS_READING"
    assert field in report["missing_essential_facts"]


@pytest.mark.parametrize("mutation", ["missing_limit", "subject_swap", "invented_date", "stale_reading",
                                    "stale_selection", "publication_date", "missing_report", "unknown_without_reason",
                                    "duplicate_report", "out_of_range", "invented_normalized_date"])
def test_scope_corruption_rejected_through_public_interpretation(tmp_path, mutation):
    _, p1, p2, scope = fixture(tmp_path)
    row = scope["reports"][0]
    if mutation == "missing_limit":
        del row["facts"]["reliance_limits"]
    elif mutation == "subject_swap":
        row["facts"]["subject"]["value"] = "FINANCIAL_STATEMENTS"
    elif mutation == "invented_date":
        row["facts"]["report_date"]["spans"][0]["quote"] = "Lisbon, 4 March 2009."
    elif mutation == "stale_reading":
        row["reading_sha256"] = "0" * 64
    elif mutation == "stale_selection":
        scope["readings_sha256"] = "0" * 64
    elif mutation == "publication_date":
        row["facts"]["publication_date"] = deepcopy(row["facts"]["report_date"])
    elif mutation == "missing_report":
        scope["reports"] = []
    elif mutation == "unknown_without_reason":
        row["facts"]["edition_authenticity"]["reason"] = ""
    elif mutation == "duplicate_report":
        scope["reports"].append(deepcopy(row))
    elif mutation == "out_of_range":
        row["facts"]["conclusion"]["spans"][0]["end"] = 100000
    elif mutation == "invented_normalized_date":
        row["facts"]["report_date"]["value"] = "2009-03-04"
    with pytest.raises(ValueError):
        service.interpretation_product(p1, p2, {"source_report_scope": scope})


@pytest.mark.parametrize("mutation", ["source_edition", "graph", "text", "duplicate_page", "unavailable_page"])
def test_reading_corruption_rejected_through_public_construction(tmp_path, mutation):
    req, _, _, _ = fixture(tmp_path)
    admission = req["source_report_readings"]
    row = admission["reports"][0]
    if mutation == "source_edition":
        row["source_sha256"] = "0" * 64
    elif mutation == "graph":
        admission["graph_sha256"] = "0" * 64
    elif mutation == "text":
        row["text_sha256"] = "0" * 64
    elif mutation == "duplicate_page":
        row["pages"].append(deepcopy(row["pages"][0]))
    else:
        row["pages"][0]["page"] = 5
    with pytest.raises(ValueError):
        service.construction_product(service.source_product(req, tmp_path), tmp_path)


def layout_graph(req, graph):
    # Synthetic retained layout, with a margin that must remain separately mapped.
    units = graph["units"]
    chunks = []
    for i, unit in enumerate(units):
        chunks.append({"item": f"item-{i}", "page": 1, "text": unit["raw"],
            "characters": [{"output": n, "unit": unit["id"], "source_offset": n, "character": char}
                           for n, char in enumerate(unit["raw"])]})
    if len(chunks) == 1:
        unit = units[0]
        middle = unit["raw"].index("We accept")
        chunks = [{"item": name, "page": 1, "text": unit["raw"][start:end],
                   "characters": [{"output": n-start, "unit": unit["id"], "source_offset": n,
                                   "character": unit["raw"][n]} for n in range(start, end)]}
                  for name, start, end in [("body", 0, middle), ("margin", middle, len(unit["raw"]))]]
    graph["layout"] = {"projections": [{"document": "d", "mappings": chunks, "failures": []}]}
    admission = deepcopy(req["source_report_readings"])
    admission["graph_sha256"] = digest(graph)
    admission["reports"][0]["pages"] = [{"page": 1, "mode": "layout", "items": [c["item"] for c in chunks]}]
    admission["reports"][0]["text_sha256"] = digest("\n".join(c["text"] for c in chunks).encode())
    return admission


@pytest.mark.parametrize("mutation", ["none", "drop_margin", "repeat_item", "reorder", "overlap", "missing_character", "invented_character"])
def test_layout_order_and_complete_character_ownership(tmp_path, mutation):
    req, p1, _, _ = fixture(tmp_path)
    graph = deepcopy(p1["payload"]["graph"])
    admission = layout_graph(req, graph)
    page = admission["reports"][0]["pages"][0]
    mapping = graph["layout"]["projections"][0]["mappings"][0]
    if mutation == "none":
        selected = report_scope.readings(graph, admission)
        assert "third parties" in selected["reports"][0]["text"]
        return
    if mutation == "drop_margin":
        page["items"].pop()
    elif mutation == "repeat_item":
        page["items"].append(page["items"][0])
    elif mutation == "reorder":
        page["items"].reverse()
    elif mutation == "overlap":
        mapping["characters"].append(deepcopy(mapping["characters"][0]))
    elif mutation == "missing_character":
        mapping["characters"].pop(0)
    else:
        mapping["text"] = "X" + mapping["text"][1:]
    # Even an updated graph hash cannot bless a corrupt P1 mapping.
    admission["graph_sha256"] = digest(graph)
    with pytest.raises(ValueError):
        report_scope.readings(graph, admission)


def test_scope_cannot_be_supplied_without_bound_report_reading(tmp_path):
    req, _, _, scope = fixture(tmp_path)
    req.pop("source_report_readings")
    req["source_report_scope"] = scope
    with pytest.raises(ValueError, match="changed or unavailable"):
        service.assess(req, tmp_path)


NCA_DEFINITION = ('Normas de Contabilidade Ajustadas definidas pelo Banco de Portugal, com base nas '
                  'Normas Internacionais de Relato Financeiro, com excepção das matérias do '
                  'Aviso nº 2/2014 e do Aviso nº 8/2016 ("NCA\'s")')
PORTUGUESE_TEXT = '\n'.join([
    'Certificação legal das contas.', 'Demonstrações financeiras individuais.',
    'Segurança aceitável.', NCA_DEFINITION, 'Em nossa opinião, apresentam de forma apropriada.',
    'A decisão anterior foi tomada em 3 de Março de 2017.',
    'Coimbra, 5 de Abril de 2018', 'Sociedade de Revisores Oficiais de Contas, S.A.',
])


def exact_span(text, quote):
    start = text.index(quote)
    return {'start': start, 'end': start + len(quote), 'quote': quote}


def portuguese_fixture(tmp_path, body=PORTUGUESE_TEXT):
    req = request(tmp_path, [body])
    req.pop('assembly')
    req.pop('scope')
    graph = service.source_product(req, tmp_path)['payload']['graph']
    text = '\n'.join(u['raw'] for u in graph['units'])
    req['source_report_readings'] = {'version': 'source-report-readings.v1', 'graph_sha256': digest(graph),
        'review': REVIEW, 'reports': [{'id': 'r', 'document': 'd',
            'source_sha256': req['bundle']['documents'][0]['sha256'], 'pages': [{'page': 1, 'mode': 'raw'}],
            'text_sha256': digest(text.encode())}]}
    p1 = service.source_product(req, tmp_path)
    p2 = service.construction_product(p1, tmp_path)
    selected = p2['payload']['source_report_readings']
    facts = {key: {'status': 'UNKNOWN', 'reason': 'Not established in synthetic report'} for key in report_scope.FACTS}
    quotes = {'identity': 'Certificação legal das contas.', 'subject': 'Demonstrações financeiras individuais.',
              'assurance_level': 'Segurança aceitável.',
              'criteria': next(line for line in body.splitlines() if line.startswith('Normas de Contabilidade')),
              'conclusion': 'Em nossa opinião, apresentam de forma apropriada.',
              'report_date': next(line for line in body.splitlines() if line.startswith('Coimbra,'))}
    codes = {'identity': 'STATUTORY_FINANCIAL_AUDIT', **report_scope.PROFILES['STATUTORY_FINANCIAL_AUDIT']}
    for field, quote in quotes.items():
        facts[field] = {'status': 'SUPPLIED', 'spans': [exact_span(text, quote)],
                        **({'value': codes[field]} if field in codes else {})}
    scope = {'version': 'source-report-scope.v2', 'context_profile': 'portuguese-report-context.v1',
        'readings_sha256': digest(selected), 'review': REVIEW,
        'reports': [{'id': 'r', 'reading_sha256': selected['reports'][0]['sha256'], 'facts': facts}]}
    return p1, p2, scope, text


def test_contextual_report_preserves_positive_support_and_debt_answers(tmp_path):
    p1, p2, scope, _ = portuguese_fixture(tmp_path)
    v1 = {k: v for k, v in scope.items() if k != 'context_profile'}
    v1['version'] = 'source-report-scope.v1'
    old = service.consume(products(p1, p2, v1), tmp_path, include_artifacts=True)
    actual = service.consume(products(p1, p2, scope), tmp_path, include_artifacts=True, mode='current')
    for key in ('questions', 'dependencies', 'assembly'):
        assert actual[key] == old[key]
    report, = actual['source_reports']
    context = report['context_review']
    assert report['status'] == 'CONDITIONAL_SUPPLIED_READING'
    assert not context['unresolved_fields'] and not context['general_semantic_truth_established']
    assert context['checks']['criteria']['status'] == 'FULL_LOCAL_DEFINITION_RETAINED'
    candidate, = context['checks']['report_date']['closing_candidates']
    assert candidate['normalized_date'] == '2018-04-05'
    assert candidate['date']['source_characters'] and candidate['signatory_cue']['source_characters']
    assert not actual['independent_legal_acceptance']
    assert all(report['facts'][key]['status'] == 'UNKNOWN' for key in report_scope.EXTERNAL)


@pytest.mark.parametrize('change', ['event_date', 'ifrs_fragment', 'missing_first_notice', 'missing_apostrophe',
                                   'partial_date', 'mixed_date_roles'])
def test_exact_but_misleading_context_withholds_actual_report_support(tmp_path, change):
    p1, p2, scope, text = portuguese_fixture(tmp_path)
    facts = scope['reports'][0]['facts']
    if change == 'event_date':
        facts['report_date']['spans'] = [exact_span(text, '3 de Março de 2017')]
    elif change == 'ifrs_fragment':
        facts['criteria']['spans'] = [exact_span(text, 'Normas Internacionais de Relato Financeiro')]
    elif change in {'missing_first_notice', 'missing_apostrophe'}:
        span = facts['criteria']['spans'][0]
        omit = '2/2014' if change == 'missing_first_notice' else "'"
        start = text.index(omit, span['start'])
        facts['criteria']['spans'] = [exact_span(text, text[span['start']:start]),
                                     exact_span(text, text[start + len(omit):span['end']])]
    elif change == 'partial_date':
        facts['report_date']['spans'] = [exact_span(text, '5 de Abril')]
    else:
        facts['report_date']['spans'].append(exact_span(text, '3 de Março de 2017'))
    v1 = {k: v for k, v in scope.items() if k != 'context_profile'}
    v1['version'] = 'source-report-scope.v1'
    baseline = service.consume(products(p1, p2, v1), tmp_path)
    actual = service.consume(products(p1, p2, scope), tmp_path)
    before, = baseline['source_reports']
    report, = actual['source_reports']
    assert before['status'] == 'CONDITIONAL_SUPPLIED_READING'
    assert report['status'] == 'INCOMPLETE_SOURCE_READING'
    assert report['use_assessment']['financial_statement_audit_opinion'] == 'NOT_ESTABLISHED_BY_THIS_READING'
    assert report['facts'] == before['facts']
    assert report['context_review']['unresolved_fields']
    assert baseline['questions'] == actual['questions']


def test_same_calendar_date_in_another_occurrence_is_not_closing_date(tmp_path):
    body = PORTUGUESE_TEXT.replace('3 de Março de 2017', '5 de Abril de 2018')
    p1, p2, scope, text = portuguese_fixture(tmp_path, body)
    scope['reports'][0]['facts']['report_date']['spans'] = [exact_span(text, '5 de Abril de 2018')]
    report, = service.consume(products(p1, p2, scope), tmp_path)['source_reports']
    assert report['context_review']['checks']['report_date']['status'] == 'REPORT_DATE_ROLE_MISMATCH'


@pytest.mark.parametrize('change', ['missing_signer', 'ambiguous_closing', 'invalid_calendar_date',
                                   'unsupported_language', 'missing_alias', 'unsupported_exception'])
def test_missing_or_ambiguous_context_stays_incomplete(tmp_path, change):
    body = PORTUGUESE_TEXT
    if change == 'missing_signer':
        body = body.replace('Sociedade de Revisores Oficiais de Contas, S.A.', 'Fim do relatório.')
    elif change == 'ambiguous_closing':
        body += '\nPorto, 6 de Abril de 2018\nSociedade de Revisores Oficiais de Contas, S.A.'
    elif change == 'invalid_calendar_date':
        body = body.replace('5 de Abril de 2018', '31 de Fevereiro de 2018')
    elif change == 'unsupported_language':
        body = body.replace('5 de Abril de 2018', '5 April 2018')
    elif change == 'missing_alias':
        body = body.replace(' ("NCA\'s")', '')
    else:
        body = body.replace('com excepção', 'sob ressalva')
    p1, p2, scope, _ = portuguese_fixture(tmp_path, body)
    report, = service.consume(products(p1, p2, scope), tmp_path)['source_reports']
    assert report['status'] == 'INCOMPLETE_SOURCE_READING'
    assert report['context_review']['unresolved_fields']


def test_complete_fragmented_criteria_coverage_is_valid(tmp_path):
    p1, p2, scope, text = portuguese_fixture(tmp_path)
    fact = scope['reports'][0]['facts']['criteria']
    span = fact['spans'][0]
    midpoint = text.index('com excepção', span['start'])
    fact['spans'] = [exact_span(text, text[span['start']:midpoint]), exact_span(text, text[midpoint:span['end']])]
    report, = service.consume(products(p1, p2, scope), tmp_path)['source_reports']
    assert report['status'] == 'CONDITIONAL_SUPPLIED_READING'


def test_single_statutory_auditor_is_a_supported_signatory_cue(tmp_path):
    body = PORTUGUESE_TEXT.replace('Sociedade de Revisores Oficiais de Contas, S.A.', 'Revisor Oficial de Contas')
    p1, p2, scope, _ = portuguese_fixture(tmp_path, body)
    report, = service.consume(products(p1, p2, scope), tmp_path)['source_reports']
    assert report['status'] == 'CONDITIONAL_SUPPLIED_READING'


@pytest.mark.parametrize('change', ['missing', 'unknown', 'v1_with_profile'])
def test_context_profile_is_explicit_and_versioned(tmp_path, change):
    p1, p2, scope, _ = portuguese_fixture(tmp_path)
    if change == 'missing':
        del scope['context_profile']
    elif change == 'unknown':
        scope['context_profile'] = 'automatic-legal-truth'
    else:
        scope['version'] = 'source-report-scope.v1'
    with pytest.raises(ValueError, match='profile'):
        products(p1, p2, scope)
