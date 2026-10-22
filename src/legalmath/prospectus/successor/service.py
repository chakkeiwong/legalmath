"""Connected phase products, with a separate installed consumer."""
from pathlib import Path
from .contracts import VERSION, QueryResult, digest, read, validate_request, write, bound_path
from . import source_graph, contract_assembly, clause_graph, law_facts, financial_profiles
from .anchors import bind

PRODUCT_VERSION = "prospectus-product.v3"


def seal(stage, bundle, inputs, payload):
    body = {"version": PRODUCT_VERSION, "stage": stage, "bundle_sha256": digest(bundle),
            "inputs": inputs, "payload": payload}
    return {**body, "sha256": digest(body)}


def verify(product, stage, bundle=None, inputs=None):
    if product.get("version") not in {PRODUCT_VERSION, "prospectus-product.v2"} or product.get("stage") != stage:
        raise ValueError("Wrong phase product version/stage")
    if product.get("sha256") != digest({k:v for k,v in product.items() if k != "sha256"}):
        raise ValueError("Phase product content changed")
    if bundle is not None and product["bundle_sha256"] != digest(bundle):
        raise ValueError("Phase product belongs to another question/source bundle")
    if inputs is not None and product["inputs"] != inputs:
        raise ValueError("Phase product parent bindings changed")
    return product["payload"]


def source_product(request, root):
    bundle = validate_request(request)
    graph = source_graph.build(bundle, root)
    if request.get("correction_admission"):
        from .corrections import admit
        graph["corrections"] = admit(graph, request["correction_admission"])
    if request.get("layout_admission"):
        from .admissions import structure
        graph["layout"] = structure(graph, request["layout_admission"])
    return seal("P1", bundle, {"request": digest(request)},
                {"request": request, "graph": graph})


def construction_product(source, root):
    payload = verify(source, "P1")
    request, graph = payload["request"], payload["graph"]
    bundle = validate_request(request)
    verify(source, "P1", bundle, {"request": digest(request)})
    for document in bundle["documents"]:
        if digest(bound_path(root,document["path"]).read_bytes()) != document["sha256"]:
            raise ValueError("Source bytes changed after intake: " + document["id"])
        source_graph.acquisition_status(document, root)
    statement_cells = None
    if 'source_statement_cells' in request:
        from .statement_cells import admit
        statement_cells = admit(graph, request['source_statement_cells'])
    construction = None
    if request.get("construction"):
        from .basf import construct, as_assembly
        spec = request["construction"]
        if spec["profile"] != "basf-option-i":
            raise ValueError("Unsupported construction profile")
        path = bound_path(root, spec["admission_path"])
        if digest(path.read_bytes()) != spec["admission_sha256"]:
            raise ValueError("Construction admission changed")
        construction = construct(graph, read(path))
        assembly = as_assembly(graph, construction, spec.get("scalar_admission"))
    else:
        assembly = contract_assembly.assemble(graph, request.get("assembly"),
                                             predicate_engine=request.get("predicate_engine", "finite"))
    if request.get("reviewed_dispositions"):
        from .admissions import dispositions
        assembly = dispositions(graph, assembly, request["reviewed_dispositions"])
    if 'structural_roles' in request:
        from .structural_roles import apply
        assembly=apply(graph,assembly,request['structural_roles'])
    result = {'assembly': assembly, 'selected_contract': construction}
    if request.get("source_report_readings"):
        from .report_scope import readings
        result["source_report_readings"] = readings(graph, request["source_report_readings"])
    if 'archive_observations' in request:
        from .archive_observations import admit
        result['archive_observations'] = admit(bundle, request['archive_observations'], root)
    if 'contract_source_chain' in request:
        from .shell_source_chain import admit
        result['contract_source_chain'] = admit(graph, bundle, request['contract_source_chain'])
    if statement_cells is not None:
        result['source_statement_cells'] = statement_cells
    return seal("P2", bundle, {"P1": source["sha256"]}, result)


def dependencies(request, graph, assembly, selected_contract=None):
    from .occurrences import _DependencyLookup, target, anchor
    lookup = _DependencyLookup(graph, assembly)
    from . import statutory_references
    statutory = statutory_references.admit(graph, assembly, request)
    result = list(request["bundle"].get("dependencies", []))
    result.extend(statutory_references.dependencies(statutory))
    from . import definition_scopes
    definition_report = definition_scopes.admit(graph, {"assembly": assembly, "selected_contract": selected_contract}, request)
    result.extend(definition_scopes.dependencies(definition_report))
    from .basf_printed_scope import check as printed_scope, missing_dependencies
    from .admissions import governing_dependencies
    result.extend(governing_dependencies(graph, assembly, _lookup=lookup))
    if request.get('governing_admission'):
        from .admissions import structure
        layout = structure(graph, request['governing_admission'])
        reviewed = governing_dependencies({**graph, 'layout': layout}, assembly, _lookup=lookup)
        if {d['id'] for d in result}.intersection(d['id'] for d in reviewed):
            raise ValueError('Duplicate governing relationship across admissions')
        result.extend(reviewed)
    result.extend(missing_dependencies(printed_scope(graph, assembly, request.get('governing_admission'))))
    operative = {u["unit"]: u for u in assembly["units"] if u["role"] in {"OPERATIVE", "UNKNOWN"}}
    documents = {u["source"]["document"] for u in operative.values()}
    raw_units = {u["id"]: u for u in graph["units"]}
    unavailable_questions = {}
    for item in assembly.get("unavailable_sources", []):
        unit = raw_units.get(item["unit"])
        if (unit is None or unit.get("visible", False) or unit["document"] != item["document"]
                or item["intended_role"] not in {"OPERATIVE", "UNKNOWN"}):
            raise ValueError("Unavailable source scope differs from source graph")
        unavailable_questions.setdefault(item["document"], set()).update(item["questions"])
    if set(unavailable_questions) - {issue["document"] for issue in graph["unresolved"]}:
        raise ValueError("Unavailable source lacks a recorded availability issue")
    for issue in graph["unresolved"]:
        questions = set(["Q1", "Q2"] if issue["document"] in documents else [])
        questions.update(unavailable_questions.get(issue["document"], ()))
        if questions:
            result.append({"id": issue["document"] + ":" + issue["reason"],
                           "questions": sorted(questions), "status": "UNRESOLVED"})
    supplied = request.get("reference_dispositions", {})
    if set(supplied) - {r["id"] for r in graph["references"]}:
        raise ValueError("Unknown reference disposition")
    edges = []
    reviewed = []
    from .basf_call_references import check as call_references, missing_dependencies as missing_calls
    result.extend(missing_calls(call_references(graph, assembly, request.get('reference_admission'))))
    from .basf_payment_references import check as payment_references, missing_dependencies as missing_payments
    result.extend(missing_payments(payment_references(graph, assembly, request.get('reference_admission'))))
    from .basf_legacy_references import check as legacy_references, missing_dependencies as missing_legacy
    result.extend(missing_legacy(legacy_references(graph, assembly, request.get('reference_admission'))))
    from .basf_governance_references import check as governance_references, missing_dependencies as missing_governance
    result.extend(missing_governance(governance_references(graph, assembly, request.get('reference_admission'))))
    from .basf_default_references import check as default_references, missing_dependencies as missing_defaults
    result.extend(missing_defaults(default_references(graph, assembly, request.get('reference_admission'))))
    from .basf_substitution_references import check as substitution_references, missing_dependencies as missing_substitutions
    result.extend(missing_substitutions(substitution_references(graph, assembly, request.get('reference_admission'))))
    from .basf_financial_references import check as financial_references, missing_dependencies as missing_financial
    result.extend(missing_financial(financial_references(graph, assembly, request.get('reference_admission'))))
    from .basf_internal_references import check as internal_references, missing_dependencies as missing_internal
    result.extend(missing_internal(internal_references(graph, assembly, request.get('reference_admission'))))
    if request.get('reference_admission'):
        from .reviewed_references import admit
        reviewed, reviewed_edges = admit(graph, assembly, request['reference_admission'], _lookup=lookup)
        result.extend(reviewed)
        edges.extend(reviewed_edges)
    replaced = {}
    for row in reviewed:
        for key in row['discovery_ids']:
            replaced.setdefault((key, row['source_use']['unit']), set()).update(row['questions'])
    if any(not raw_units[ref["unit"]].get("visible", False) for ref in graph["references"]):
        # Unavailable documents may remain in the inventory without supplying
        # operative references. First verify that construction did not copy
        # any unavailable source into a selected occurrence.
        from .occurrences import segments
        for unit in operative.values():
            original = raw_units.get(unit["unit"])
            if original is not None and not original.get("visible", False):
                raise ValueError("Source occurrence unavailable")
            segments(graph, unit, _raw=raw_units)
    for ref in graph["references"]:
        source = anchor(raw_units[ref["unit"]], ref["start"], ref["end"])
        if not raw_units[ref["unit"]].get("visible", False):
            if ref["id"] in supplied:
                bind(graph, source)  # An explicit unavailable-source decision must still reject.
            continue
        referencing = lookup.uses(graph, assembly, source, roles=("OPERATIVE", "UNKNOWN"))
        if not referencing:
            legacy = operative.get(ref["unit"])
            if legacy and "character_map" not in legacy and legacy["text"] != raw_units[ref["unit"]]["raw"]:
                result.append({"id": "unmapped:" + ref["id"], "questions": legacy["questions"], "status": "UNRESOLVED"})
            continue
        decision = supplied.get(ref["id"])
        targets = []
        if decision:
            if not isinstance(decision, dict) or not decision.get("reason") or decision.get("source_sha256") != ref["source_sha256"]:
                raise ValueError("Reference disposition must bind occurrence edition and reason")
            if not decision.get("targets"):
                raise ValueError("Reference targets must be available operative source units")
            targets = [target(graph, assembly, value, _lookup=lookup) for value in decision["targets"]]
            if len(referencing) > 1 and decision.get("from_use") not in {m["unit"] for m in referencing}:
                raise ValueError("Repeated reference occurrence requires an explicit from_use")
        kind = decision.get("kind", "reference") if decision else "reference"
        from .reference_closure import KINDS
        if kind not in KINDS:
            raise ValueError("Unsupported reference kind")
        authority = decision.get("authority") if decision else None
        if authority is not None:
            bind(graph, authority)
        for use in referencing:
            questions = sorted(set(operative[use["unit"]]["questions"]) - replaced.get((ref["id"], use["unit"]), set()))
            if not questions:
                continue
            applies = bool(targets) and (not decision.get("from_use") or decision["from_use"] == use["unit"])
            result.append({"id": ref["id"] + "@" + use["unit"], "questions": questions,
                           "status": "RESOLVED" if applies else "UNRESOLVED",
                           "source_use": use, "targets": targets if applies else []})
            for destination in targets if applies else [None]:
                edges.append({"id": ref["id"] + "@" + use["unit"], "from": use["unit"],
                              "to": destination["unit"] if destination else None, "kind": kind,
                              "resolved": applies, "authority": authority, "questions": questions})
    from .reference_closure import close
    for question in ("Q1", "Q2"):
        roots = {u for u, row in operative.items() if question in row["questions"]}
        closure = close(operative, [edge for edge in edges if question in edge['questions']], roots)
        if closure["unresolved"]:
            result.append({"id": "reference-closure:" + question, "questions": [question],
                           "status": "UNRESOLVED", **closure})
    return result


def _verify_consumed_dependencies(graph, selected, request, semantic):
    """Reconstruct source closure; a valid phase hash cannot establish it."""
    expected = dependencies(request, graph, selected['assembly'], selected['selected_contract'])
    if request.get('incorporation_admission'):
        from . import basf_incorporation
        incorporation = basf_incorporation.admit(
            graph, selected['selected_contract'], request['incorporation_admission'])
        extra = basf_incorporation.dependency(incorporation)
        if any(d['id'] == extra['id'] for d in expected):
            raise ValueError('Duplicate incorporation dependency')
        expected.append(extra)
    actual = semantic['dependencies']
    expected_closures = [d for d in expected if d['id'].startswith('reference-closure:')]
    actual_closures = [d for d in actual if d['id'].startswith('reference-closure:')]
    if digest(sorted(actual_closures, key=lambda d: d['id'])) != digest(
            sorted(expected_closures, key=lambda d: d['id'])):
        raise ValueError('Consumed reference closure differs from source reconstruction')
    if digest(sorted(actual, key=lambda d: d['id'])) != digest(sorted(expected, key=lambda d: d['id'])):
        raise ValueError('Consumed dependencies differ from source reconstruction')
    owned = {d['id'] for d in expected}
    for question in ('Q1', 'Q2'):
        required = {d['id'] for d in expected if question in d['questions'] and d['status'] != 'RESOLVED'}
        parent = semantic['questions'][question]
        for answer in [parent, *parent.get('subquestions', {}).values()]:
            observed = [key for key in answer['unresolved'] if key in owned]
            if set(observed) != required or len(observed) != len(required):
                raise ValueError('Consumed question hides or invents dependency uncertainty')
            if required and (answer['status'] not in ('UNKNOWN', 'CONFLICT') or answer['value'] is not None):
                raise ValueError('Consumed question resolves source dependency uncertainty')
    # Stored Q3 is part of P3 even though final Q3 is rebuilt by consume.
    completeness = {q: {'complete': not semantic['questions'][q]['unresolved'],
                         'unresolved': semantic['questions'][q]['unresolved']} for q in ('Q1', 'Q2')}
    q3 = semantic['questions']['Q3']
    status = 'COMPLETE' if all(row['complete'] for row in completeness.values()) else 'PARTIAL'
    if q3['value'] != completeness or q3['status'] != status:
        raise ValueError('Consumed semantic completeness differs from question uncertainty')


def _verify_consumed_questions(graph, selected, request, semantic):
    """Check all stored question fields against the declared inference inputs."""
    if digest(semantic['scope']) != digest(request.get('scope', {})):
        raise ValueError('Consumed question scope differs from declared input')
    expected = clause_graph.evaluate(
        semantic['clauses'], selected['assembly'], semantic['scope'],
        semantic['dependencies'], request.get('observations'),
        predicate_engine=request.get('predicate_engine', 'finite'),
        predicate_constraints=request.get('predicate_constraints', ()), source_graph=graph)
    if digest(semantic['questions']) != digest(expected):
        raise ValueError('Consumed question results differ from declared inference')


def _bound_report_readings(graph, request, selected):
    """Reconstruct selected pages; a phase hash alone cannot establish provenance."""
    if request.get("source_report_readings"):
        from .report_scope import readings
        expected = readings(graph, request["source_report_readings"])
        if selected.get("source_report_readings") != expected:
            raise ValueError("Report readings differ from supplied source evidence")
        return expected
    if "source_report_readings" in selected:
        raise ValueError("Report readings lack supplied source evidence")
    return None


def interpretation_product(source, construction, interpretation=None):
    payload = verify(source, "P1")
    request, graph = payload["request"], payload["graph"]
    bundle = request["bundle"]
    if interpretation is not None:
        from .anchors import fields
        fields(interpretation, {"clauses", "scope", "observations", "reference_dispositions", "reference_admission", "predicate_engine", "predicate_constraints", "annotation_admission", "priority_admission", "source_report_scope", "source_discrepancies", "source_cash_flow", "governing_admission", "incorporation_admission", "statutory_references", "definition_sources"})
        request = {**request, **interpretation}
    selected = verify(construction, "P2", bundle, {"P1": source["sha256"]})
    report_readings = _bound_report_readings(graph, request, selected)
    assembly = selected['assembly']
    from .structural_roles import verify as verify_roles
    verify_roles(graph,assembly,request.get('structural_roles'))
    from . import definition_scopes
    definition_report = definition_scopes.admit(graph, selected, request)
    from . import statutory_references
    statutory = statutory_references.admit(graph, assembly, request)
    from .basf_call_references import check as check_call_references
    check_call_references(graph, assembly, request.get('reference_admission'))
    from .basf_payment_references import check as check_payment_references
    check_payment_references(graph, assembly, request.get('reference_admission'))
    from .basf_legacy_references import check as check_legacy_references
    check_legacy_references(graph, assembly, request.get('reference_admission'))
    from .basf_governance_references import check as check_governance_references
    check_governance_references(graph, assembly, request.get('reference_admission'))
    from .basf_default_references import check as check_default_references
    check_default_references(graph, assembly, request.get('reference_admission'))
    from .basf_substitution_references import check as check_substitution_references
    check_substitution_references(graph, assembly, request.get('reference_admission'))
    from .basf_financial_references import check as check_financial_references
    check_financial_references(graph, assembly, request.get('reference_admission'))
    from .basf_internal_references import check as check_internal_references
    check_internal_references(graph, assembly, request.get('reference_admission'))
    from .basf_printed_scope import check as check_printed_scope
    check_printed_scope(graph, assembly, request.get('governing_admission'))
    supplied = request.get("clauses")
    if request.get("annotation_admission"):
        if supplied is not None:
            raise ValueError("Choose authored evidence or directly supplied clauses")
        from .admissions import annotation_clauses
        supplied = annotation_clauses(graph, assembly, request["annotation_admission"])
    clauses = clause_graph.build(assembly, supplied)
    if request.get("priority_admission"):
        from .priorities import admit
        clauses = admit(graph, assembly, clauses, request["priority_admission"])
    deps = dependencies(request, graph, assembly, selected["selected_contract"])
    incorporation = None
    if request.get('incorporation_admission'):
        from . import basf_incorporation
        incorporation = basf_incorporation.admit(graph, selected['selected_contract'], request['incorporation_admission'])
        dependency = basf_incorporation.dependency(incorporation)
        if any(d['id'] == dependency['id'] for d in deps):
            raise ValueError('Duplicate incorporation dependency')
        deps.append(dependency)
    questions = clause_graph.evaluate(clauses, assembly, request.get("scope", {}), deps, request.get("observations"),
        predicate_engine=request.get("predicate_engine", "finite"), predicate_constraints=request.get("predicate_constraints", ()), source_graph=graph)
    terms = None
    if request.get("term_interpretations"):
        from .contract_terms import admit
        terms = admit(graph, assembly, request["term_interpretations"])
    result = {"clauses": clauses, "dependencies": deps, "questions": questions,
              "interpretation_input": interpretation, "scope": request.get("scope", {}), "contract_terms": terms}
    if 'source_statement_cells' in request:
        from .statement_cells import admit
        cells = admit(graph, request['source_statement_cells'])
        if selected.get('source_statement_cells') != cells:
            raise ValueError('Statement cell construction differs from supplied source reading')
        result['source_statement_cells_sha256'] = cells['sha256']
    elif 'source_statement_cells' in selected:
        raise ValueError('Statement cells lack supplied source evidence')
    if request.get("source_report_scope"):
        from .report_scope import admit
        result["source_report_scope"] = admit(report_readings, request["source_report_scope"])
    if 'source_discrepancies' in request:
        from .source_discrepancies import admit
        result['source_discrepancies'] = admit(graph, report_readings, request['source_discrepancies'])
    if 'source_cash_flow' in request:
        from .bes_cash_flow import admit
        result['source_cash_flow'] = admit(graph, request['source_cash_flow'])
    if request.get('governing_admission'):
        result['governing_admission_sha256'] = digest(request['governing_admission'])
    if definition_report is not None:
        result["definition_sources"] = definition_report
    if statutory is not None:
        result["statutory_references"] = statutory
    if incorporation is not None:
        result['incorporation_review'] = incorporation
    return seal("P3", bundle, {"P1": source["sha256"], "P2": construction["sha256"]}, result)


def law_product(source, interpretation, cases=None, law_input=None):
    payload = verify(source, "P1")
    request = payload["request"]
    verify(interpretation, "P3", request["bundle"])
    if law_input is not None:
        from .anchors import fields
        fields(law_input, {"law_bases", "facts", "law_relation", "ratio_facts", "calendar_facts", "law_explanation"}, {"law_bases", "facts"})
        request = {**request, **law_input}
    if 'law_explanation' in request:
        from .explanations import validate_option
        validate_option(request['law_explanation'])
    if "ratio_facts" in request and not isinstance(request["ratio_facts"], list):
        raise ValueError("Ratio facts must be a list")
    if "calendar_facts" in request and not isinstance(request["calendar_facts"], list):
        raise ValueError("Calendar facts must be a list")
    question = law_facts.assess(request["bundle"], request.get("law_bases", []), request.get("facts", []),
                               payload["graph"], request.get("law_relation"),
                               predicate_engine=request.get("predicate_engine", "finite"),
                               ratio_facts=request.get("ratio_facts"),
                               calendar_facts=request.get("calendar_facts"),
                               law_explanation=request.get('law_explanation'))
    from . import statutory_references
    statutory = interpretation["payload"].get("statutory_references")
    result = {"question": statutory_references.law_question(question, statutory),
              "cases": cases or [], "law_input": law_input}
    if statutory is not None:
        result.update(conditional_question=question, statutory_references=statutory)
    return seal("P4", request["bundle"], {"P1": source["sha256"], "P3": interpretation["sha256"]}, result)


def financial_product(source, construction, interpretation, cases=None, scenario=None):
    request = verify(source, "P1")["request"]
    verify(construction, "P2", request["bundle"], {"P1": source["sha256"]})
    verify(interpretation, "P3", request["bundle"], {"P1": source["sha256"], "P2": construction["sha256"]})
    supplied = scenario if scenario is not None else request.get("financial_scenario")
    if request.get("contract_calculation"):
        if supplied is not None:
            raise ValueError("Choose selected-contract calculation or separate financial scenario")
        from .contract_terms import scenario as from_terms
        semantic = verify(interpretation, "P3")
        if semantic.get("contract_terms") is None:
            raise ValueError("Reviewed selected contract terms required")
        calculated = from_terms(semantic["contract_terms"], request["contract_calculation"],
                                verify(source, "P1")["graph"], verify(construction, "P2")["assembly"])
        question = QueryResult("Q5", "CONDITIONAL", value=calculated).json()
    else:
        question = financial_profiles.assess(request["bundle"], supplied, verify(source, "P1")["graph"])
    return seal("P5", request["bundle"], {"P2": construction["sha256"], "P3": interpretation["sha256"]},
                {"question": question, "cases": cases or [], "scenario_input": supplied})


def consume(products, root, bank=None, include_artifacts=False, *, mode="frozen",
            comparative_profile=None, expected_comparative_profile_sha256=None,
            default_f_profile=None, expected_default_f_profile_sha256=None,
            majority_profile=None, expected_majority_profile_sha256=None,
            amount_profile=None, expected_amount_profile_sha256=None,
            duration_profile=None, expected_duration_profile_sha256=None,
            cutoff_profile=None, expected_cutoff_profile_sha256=None,
            payment_profile=None, expected_payment_profile_sha256=None,
            rating_profile=None, expected_rating_profile_sha256=None,
            votes_profile=None, expected_votes_profile_sha256=None,
            concert_profile=None, expected_concert_profile_sha256=None,
            coverage_profile=None, expected_coverage_profile_sha256=None,
            agent_notice_profile=None, expected_agent_notice_profile_sha256=None,
            notice_delivery_profile=None, expected_notice_delivery_profile_sha256=None,
            affiliate_profile=None, expected_affiliate_profile_sha256=None,
            publication_profile=None, expected_publication_profile_sha256=None,
            labels_profile=None, expected_labels_profile_sha256=None,
            payment_categories_profile=None, expected_payment_categories_profile_sha256=None,
            layout_labels_profile=None, expected_layout_labels_profile_sha256=None,
            reference_roles_profile=None, expected_reference_roles_profile_sha256=None,
            definition_roles_profile=None, expected_definition_roles_profile_sha256=None,
            definition_bindings_profile=None, expected_definition_bindings_profile_sha256=None,
            definition_contexts_profile=None, expected_definition_contexts_profile_sha256=None,
            definition_referents_profile=None, expected_definition_referents_profile_sha256=None,
            definition_remainders_profile=None, expected_definition_remainders_profile_sha256=None,
            definition_dependencies_profile=None, expected_definition_dependencies_profile_sha256=None,
            rating_labels_profile=None, expected_rating_labels_profile_sha256=None,
            cycle_dispositions_profile=None, expected_cycle_dispositions_profile_sha256=None,
            paragraph_references_profile=None, expected_paragraph_references_profile_sha256=None,
            reference_scope_profile=None, expected_reference_scope_profile_sha256=None,
            reference_addresses_profile=None, expected_reference_addresses_profile_sha256=None,
            standalone_sections_profile=None, expected_standalone_sections_profile_sha256=None,
            unquoted_definitions_profile=None, expected_unquoted_definitions_profile_sha256=None,
            purpose_uses_profile=None, expected_purpose_uses_profile_sha256=None,
            bgb_onward_profile=None, expected_bgb_onward_profile_sha256=None,
            holder_authority_profile=None, expected_holder_authority_profile_sha256=None,
            issuer_qualification_profile=None, expected_issuer_qualification_profile_sha256=None,
            office_change_profile=None, expected_office_change_profile_sha256=None,
            election_profile=None, expected_election_profile_sha256=None,
            home_routes_profile=None, expected_home_routes_profile_sha256=None):
    if mode not in {"frozen", "current"}:
        raise ValueError("Choose frozen replay or current assessment")
    source, construction, interpretation, law, financial = [products[p] for p in ("P1", "P2", "P3", "P4", "P5")]
    data = verify(source, "P1")
    request, graph = data["request"], data["graph"]
    bundle = validate_request(request)
    verify(source, "P1", bundle, {"request": digest(request)})
    if graph["bundle_sha256"] != digest(bundle):
        raise ValueError("Source graph bundle changed")
    if mode == "current":
        if any(p.get("version") != PRODUCT_VERSION for p in products.values()):
            raise ValueError("Legacy products require fresh assessment before current validation")
        fresh = source_product(request, root)
        if fresh["payload"]["graph"] != graph:
            raise ValueError("Source derivative or extraction runtime changed; reassessment required")
        rebuilt = construction_product(fresh, root)
        if rebuilt["payload"] != verify(construction, "P2"):
            raise ValueError("Construction admission changed; reassessment required")
        fresh_semantic = interpretation_product(fresh, rebuilt, verify(interpretation, "P3").get("interpretation_input"))
        law_payload, financial_payload = verify(law, "P4"), verify(financial, "P5")
        fresh_law = law_product(fresh, fresh_semantic, law_payload.get("cases"), law_payload.get("law_input"))
        fresh_financial = financial_product(fresh, rebuilt, fresh_semantic,
                                             financial_payload.get("cases"), financial_payload.get("scenario_input"))
        for old, new in ((interpretation, fresh_semantic), (law, fresh_law), (financial, fresh_financial)):
            if old["payload"] != new["payload"]:
                raise ValueError("Current interpretation/calculation differs; reassessment required")
    for document in bundle["documents"]:
        if digest(bound_path(root,document["path"]).read_bytes()) != document["sha256"]:
            raise ValueError("Source bytes changed after intake: " + document["id"])
        source_graph.acquisition_status(document, root)
    selected = verify(construction, "P2", bundle, {"P1": source["sha256"]})
    from .shell_source_chain import verify as verify_source_chain
    source_chain = verify_source_chain(graph, bundle, request, selected)
    report_readings = _bound_report_readings(graph, request, selected)
    if 'archive_observations' in request:
        from .archive_observations import admit
        if selected.get('archive_observations') != admit(bundle, request['archive_observations'], root):
            raise ValueError('Archive observation differs from current bound evidence')
    elif 'archive_observations' in selected:
        raise ValueError('Archive observation has no request evidence')
    semantic = verify(interpretation, "P3", bundle, {"P1": source["sha256"], "P2": construction["sha256"]})
    if 'source_statement_cells' in request:
        from .statement_cells import admit
        cells = admit(graph, request['source_statement_cells'])
        if (selected.get('source_statement_cells') != cells
                or semantic.get('source_statement_cells_sha256') != cells['sha256']):
            raise ValueError('Consumed statement cells differ from supplied source evidence')
    elif 'source_statement_cells' in selected or 'source_statement_cells_sha256' in semantic:
        raise ValueError('Consumed statement cells lack supplied source evidence')
    from .structural_roles import verify as verify_roles
    verify_roles(graph,selected['assembly'],request.get('structural_roles'))
    interpretation_input = {**request, **(semantic.get('interpretation_input') or {})}
    _verify_consumed_questions(graph, selected, interpretation_input, semantic)
    from . import definition_scopes
    definition_report = definition_scopes.verify_consumed(graph, selected, interpretation_input, semantic)
    from . import statutory_references
    statutory = statutory_references.verify_consumed(graph, selected["assembly"], interpretation_input, semantic)
    statutory_references.verify_law(verify(law, "P4", bundle, {"P1": source["sha256"], "P3": interpretation["sha256"]}), request, graph, statutory)
    from .reviewed_references import verify_consumed_families
    reference_families = verify_consumed_families(graph, selected['assembly'], interpretation_input, semantic)
    call_references = reference_families['call']
    payment_references = reference_families['payment']
    legacy_references = reference_families['legacy']
    governance_references = reference_families['governance']
    default_references = reference_families['default']
    substitution_references = reference_families['substitution']
    financial_references = reference_families['financial']
    internal_references = reference_families['internal']
    _verify_consumed_dependencies(graph, selected, interpretation_input, semantic)
    from .basf_printed_scope import verify_consumed as verify_printed_scope
    printed_scope = verify_printed_scope(graph, selected['assembly'], interpretation_input, semantic)
    if interpretation_input.get("source_report_scope"):
        from .report_scope import admit
        expected_scope = admit(report_readings, interpretation_input["source_report_scope"])
        if semantic.get("source_report_scope") != expected_scope:
            raise ValueError("Consumed report scope differs from supplied source evidence")
    elif "source_report_scope" in semantic:
        raise ValueError("Consumed report scope lacks supplied source evidence")
    if 'source_discrepancies' in interpretation_input:
        from .source_discrepancies import admit
        if semantic.get('source_discrepancies') != admit(graph, report_readings, interpretation_input['source_discrepancies']):
            raise ValueError('Source discrepancy differs from its bound evidence')
    elif 'source_discrepancies' in semantic:
        raise ValueError('Source discrepancy lacks supplied evidence')
    if 'source_cash_flow' in interpretation_input:
        from .bes_cash_flow import admit, validate_images
        expected_cash_flow = admit(graph, interpretation_input['source_cash_flow'])
        if digest(semantic.get('source_cash_flow')) != digest(expected_cash_flow):
            raise ValueError('Cash-flow reconciliation differs from its bound evidence')
        validate_images(expected_cash_flow, root)
    elif 'source_cash_flow' in semantic:
        raise ValueError('Cash-flow reconciliation lacks supplied evidence')
    if semantic["clauses"]["assembly_sha256"] != digest(selected["assembly"]):
        raise ValueError("Interpreted assembly differs from selected contract")
    legal = verify(law, "P4", bundle, {"P1": source["sha256"], "P3": interpretation["sha256"]})
    amounts = verify(financial, "P5", bundle, {"P2": construction["sha256"], "P3": interpretation["sha256"]})
    questions = {**semantic["questions"], "Q4": legal["question"], "Q5": amounts["question"]}
    if bank is None and request.get("bank"):
        from ...transaction.evidence import Store
        bank = {**request["bank"], "store": Store(bound_path(root, request["bank"]["store"]))}
    if bank:
        from .integration import investigate
        questions["Q6"] = investigate(bundle, bank, graph)
    else:
        questions["Q6"] = QueryResult("Q6", "UNKNOWN", unresolved=["Bank context/evidence store not supplied"]).json()
    scope = semantic["scope"]
    declared = [q for q in scope if q in {"Q1", "Q2", "Q4", "Q5", "Q6"}] or ["Q1", "Q2"]
    completeness = {q: {"complete": bool(scope.get(q, {}).get("complete")) and
                              not questions[q]["unresolved"] and questions[q]["status"] not in {"UNKNOWN", "UNSUPPORTED"},
                        "unresolved": questions[q]["unresolved"]} for q in declared}
    questions["Q3"] = QueryResult("Q3", "COMPLETE" if all(v["complete"] for v in completeness.values()) else "PARTIAL",
                                  completeness, quantifier="Declared questions: " + ", ".join(declared)).json()
    effective_law = {**request, **(legal.get("law_input") or {})}
    supplied_legal_model = any(effective_law.get(k) for k in
                              ("law_bases", "facts", "ratio_facts", "calendar_facts"))
    result = {"version": VERSION, "instrument_id": bundle["instrument_id"], "request_sha256": digest(request),
              "source_graph_sha256": digest(graph),
              "assessment_mode": mode,
              "validation_profile": "closure-admission.v1" if all(p.get("version") == PRODUCT_VERSION for p in products.values()) else "LEGACY_FROZEN_REPLAY",
              "questions": questions, "consumed_products": {p: products[p]["sha256"] for p in products},
              "law_cases": legal["cases"], "financial_cases": amounts["cases"],
              "mode": "ASSISTED" if definition_report is not None or statutory is not None or supplied_legal_model or semantic["clauses"]["origin"] == "assisted-proposal" or any(request.get(k) for k in
                  ('term_interpretations', 'annotation_admission', 'priority_admission', 'reviewed_dispositions',
                   'correction_admission', 'layout_admission', 'reference_admission', 'governing_admission',
                   'source_report_readings', 'source_report_scope', 'source_discrepancies', 'source_statement_cells', 'source_cash_flow', 'incorporation_admission', 'archive_observations')) or semantic.get('source_report_scope') or semantic.get('source_discrepancies') or semantic.get('source_cash_flow') or semantic.get('governing_admission_sha256') or semantic.get('incorporation_review') else "AUTOMATIC_BOUNDED",
              "independent_legal_acceptance": False, "may_execute_transaction": False}
    if source_chain is not None:
        result['contract_source_chain'] = source_chain
        result['mode'] = 'ASSISTED'
    if semantic.get("source_report_scope"):
        from .report_scope import explain
        result["source_reports"] = explain(semantic["source_report_scope"])
    if semantic.get('source_discrepancies'):
        from .source_discrepancies import explain
        result['source_discrepancies'] = explain(semantic['source_discrepancies'])
    if semantic.get('source_cash_flow'):
        from copy import deepcopy
        result['source_cash_flow_reconciliation'] = deepcopy(semantic['source_cash_flow'])
    if 'source_statement_cells' in selected:
        from .statement_cells import explain
        result['source_statement_cells'] = explain(selected['source_statement_cells'])
    if 'archive_observations' in selected:
        from copy import deepcopy
        result['source_archive_observations'] = deepcopy(selected['archive_observations'])
        for report in result.get('source_reports', []):
            report['archive_observations'] = [deepcopy(r) for r in selected['archive_observations']['observations']
                                              if r['document'] == report['document']]
    if semantic.get('incorporation_review'):
        from .basf_incorporation import explain
        result['incorporation'] = explain(semantic['incorporation_review'])
    if any(n['effect'] == 'representative_governance' for n in semantic['clauses']['nodes']):
        from .representative_governance import explain
        result['representative_governance'] = explain(semantic['clauses'], graph, selected['assembly'])
    if any(n['effect'] == 'basf_note_lifecycle' for n in semantic['clauses']['nodes']):
        from .basf_note_lifecycle import explain
        result['basf_note_lifecycle'] = explain(semantic['clauses'], graph, selected['assembly'])
    if any(n['effect'] == 'basf_meeting_procedure' for n in semantic['clauses']['nodes']):
        from .basf_meeting_procedure import explain
        result['basf_meeting_procedure'] = explain(semantic['clauses'], graph, selected['assembly'])
    if any(n['effect'] == 'basf_payment_terms' for n in semantic['clauses']['nodes']):
        from .basf_payment_terms import explain
        result['basf_payment_terms'] = explain(semantic['clauses'], graph, selected['assembly'])
    if any(n['effect'] == 'basf_governance_terms' for n in semantic['clauses']['nodes']):
        from .basf_governance_terms import explain
        result['basf_governance_terms'] = explain(semantic['clauses'], graph, selected['assembly'])
    if any(n['id'].startswith('basf-agents:') or 'agent_reading' in n or 'capacity_reading' in n
           for n in semantic['clauses']['nodes']):
        from .basf_agent_report import explain
        result['basf_agents'] = explain(semantic['clauses'], graph, selected['assembly'],
                                       semantic['dependencies'])
    if request.get('relation_discovery'):
        from .relation_discovery import discover
        result['relation_candidates'] = discover(graph, request['relation_discovery'])
    if selected.get('selected_contract') and selected['selected_contract'].get('unit_accounting'):
        from .meaning_coverage import explain
        result['meaning_coverage'] = explain(graph, selected['selected_contract'],
                                             selected['assembly'], semantic['clauses'])
    if printed_scope is not None:
        from .basf_printed_scope import explain
        result['printed_margin_review'] = explain(printed_scope, result, semantic)
    if call_references is not None:
        result['relative_call_notices'] = call_references
    if payment_references is not None:
        result['payment_method_references'] = payment_references
    if legacy_references is not None:
        result['original_reference_review'] = legacy_references
    if governance_references is not None:
        result['governance_references'] = governance_references
    if default_references is not None:
        result['default_references'] = default_references
    if substitution_references is not None:
        result['substitution_references'] = substitution_references
    if financial_references is not None:
        result['financial_references'] = financial_references
    if internal_references is not None:
        result['internal_references'] = internal_references
    if definition_report is not None:
        result["definition_sources"] = definition_report
    if statutory is not None:
        result["statutory_references"] = statutory
    from .source_graph import native_text_gaps
    gaps = native_text_gaps(graph)
    if gaps:
        result['native_text_gaps'] = {
            'scope': 'Source inventory diagnostic; no operative scope or completeness inferred',
            'pages': gaps}
    if include_artifacts:
        result.update(source_map=graph, assembly=selected["assembly"], selected_contract=selected["selected_contract"],
                      clause_graph=semantic["clauses"], dependencies=semantic["dependencies"])
    if comparative_profile is not None:
        from ..bes_comparative_basis import evaluate, explain
        baseline = {**result, "report_sha256": digest(result)}
        review = evaluate(graph, baseline, comparative_profile, root,
                          expected_profile_sha256=expected_comparative_profile_sha256)
        result['comparative_accounting_review'] = review
        result['comparative_accounting_explanation'] = explain(review)
    elif expected_comparative_profile_sha256 is not None:
        raise ValueError('Comparative profile pin supplied without a profile')
    if default_f_profile is not None:
        from ..basf_default_f_current import evaluate
        # Bind the complete actual answer after any preceding optional review.
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, default_f_profile, root,
                               expected_profile_sha256=expected_default_f_profile_sha256))
    elif expected_default_f_profile_sha256 is not None:
        raise ValueError('Default(f) profile pin supplied without a profile')
    if majority_profile is not None:
        from ..schvg_majority import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['schvg_majority_review'] = evaluate(products, baseline, majority_profile, root,
            expected_profile_sha256=expected_majority_profile_sha256)
    elif expected_majority_profile_sha256 is not None:
        raise ValueError('Majority profile pin supplied without a profile')
    if amount_profile is not None:
        from ..cross_default_amount import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['cross_default_amount_review'] = evaluate(products, baseline, amount_profile, root,
            expected_profile_sha256=expected_amount_profile_sha256)
    elif expected_amount_profile_sha256 is not None:
        raise ValueError('Amount profile pin supplied without a profile')
    if duration_profile is not None:
        from ..strict_duration import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['strict_duration_review'] = evaluate(products, baseline, duration_profile, root,
            expected_profile_sha256=expected_duration_profile_sha256)
    elif expected_duration_profile_sha256 is not None:
        raise ValueError('Duration profile pin supplied without a profile')
    if cutoff_profile is not None:
        from ..frankfurt_cutoff import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['frankfurt_cutoff_review'] = evaluate(products, baseline, cutoff_profile, root,
            expected_profile_sha256=expected_cutoff_profile_sha256)
    elif expected_cutoff_profile_sha256 is not None:
        raise ValueError('Cutoff profile pin supplied without a profile')
    if payment_profile is not None:
        from ..payment_deadline import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['payment_deadline_review'] = evaluate(products, baseline, payment_profile, root,
            expected_profile_sha256=expected_payment_profile_sha256)
    elif expected_payment_profile_sha256 is not None:
        raise ValueError('Payment profile pin supplied without a profile')
    if rating_profile is not None:
        from ..causal_rating import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['causal_rating_review'] = evaluate(products, baseline, rating_profile, root,
            expected_profile_sha256=expected_rating_profile_sha256)
    elif expected_rating_profile_sha256 is not None:
        raise ValueError('Rating profile pin supplied without a profile')
    if votes_profile is not None:
        from ..control_votes import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['control_votes_review'] = evaluate(products, baseline, votes_profile, root,
            expected_profile_sha256=expected_votes_profile_sha256)
    elif expected_votes_profile_sha256 is not None:
        raise ValueError('Voting profile pin supplied without a profile')
    if concert_profile is not None:
        from ..concert_application import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['concert_necessary_review'] = evaluate(products, baseline, concert_profile, root,
            expected_profile_sha256=expected_concert_profile_sha256)
    elif expected_concert_profile_sha256 is not None:
        raise ValueError('Concert profile pin supplied without a profile')
    if coverage_profile is not None:
        from ..residual_coverage import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['residual_coverage_review'] = evaluate(products, baseline, coverage_profile, root,
            expected_profile_sha256=expected_coverage_profile_sha256)
    elif expected_coverage_profile_sha256 is not None:
        raise ValueError('Coverage profile pin supplied without a profile')
    if agent_notice_profile is not None:
        from ..agent_notice_application import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['agent_notice_review'] = evaluate(products, baseline, agent_notice_profile, root,
            expected_profile_sha256=expected_agent_notice_profile_sha256)
    elif expected_agent_notice_profile_sha256 is not None:
        raise ValueError('Agent notice profile pin supplied without a profile')
    if notice_delivery_profile is not None:
        from ..notice_delivery import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['notice_delivery_review'] = evaluate(products, baseline, notice_delivery_profile, root,
            expected_profile_sha256=expected_notice_delivery_profile_sha256)
    elif expected_notice_delivery_profile_sha256 is not None:
        raise ValueError('Notice delivery profile pin supplied without a profile')
    if affiliate_profile is not None:
        from ..affiliate_substitution import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['affiliate_substitution_review'] = evaluate(products, baseline, affiliate_profile, root,
            expected_profile_sha256=expected_affiliate_profile_sha256)
    elif expected_affiliate_profile_sha256 is not None:
        raise ValueError('Affiliate profile pin supplied without a profile')
    if publication_profile is not None:
        from ..publication_routes import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['publication_routes_review'] = evaluate(products, baseline, publication_profile, root,
            expected_profile_sha256=expected_publication_profile_sha256)
    elif expected_publication_profile_sha256 is not None:
        raise ValueError('Publication profile pin supplied without a profile')
    if labels_profile is not None:
        from .unicode_labels import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['unicode_label_review'] = evaluate(products, baseline, labels_profile, root,
            expected_profile_sha256=expected_labels_profile_sha256)
    elif expected_labels_profile_sha256 is not None:
        raise ValueError('Label profile pin supplied without a profile')
    if payment_categories_profile is not None:
        from ..payment_categories import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['payment_category_review'] = evaluate(products, baseline, payment_categories_profile, root,
            expected_profile_sha256=expected_payment_categories_profile_sha256)
    elif expected_payment_categories_profile_sha256 is not None:
        raise ValueError('Payment category profile pin supplied without a profile')
    if layout_labels_profile is not None:
        from .layout_labels import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['layout_label_review'] = evaluate(products, baseline, layout_labels_profile, root,
            expected_profile_sha256=expected_layout_labels_profile_sha256)
    elif expected_layout_labels_profile_sha256 is not None:
        raise ValueError('Layout label profile pin supplied without a profile')
    if reference_roles_profile is not None:
        from .reference_roles import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result['reference_role_review'] = evaluate(products, baseline, reference_roles_profile, root,
            expected_profile_sha256=expected_reference_roles_profile_sha256)
    elif expected_reference_roles_profile_sha256 is not None:
        raise ValueError('Reference-role profile pin supplied without a profile')
    if definition_roles_profile is not None:
        from .definition_roles import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, definition_roles_profile, root,
            expected_profile_sha256=expected_definition_roles_profile_sha256))
    elif expected_definition_roles_profile_sha256 is not None:
        raise ValueError('Definition-role profile pin supplied without a profile')
    if definition_bindings_profile is not None:
        from .definition_bindings import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, definition_bindings_profile, root,
            expected_profile_sha256=expected_definition_bindings_profile_sha256))
    elif expected_definition_bindings_profile_sha256 is not None:
        raise ValueError('Definition-binding profile pin supplied without a profile')
    if definition_contexts_profile is not None:
        from .definition_contexts import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, definition_contexts_profile, root,
            expected_profile_sha256=expected_definition_contexts_profile_sha256))
    elif expected_definition_contexts_profile_sha256 is not None:
        raise ValueError('Definition-context profile pin supplied without a profile')
    if definition_referents_profile is not None:
        from .definition_referents import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, definition_referents_profile, root,
            expected_profile_sha256=expected_definition_referents_profile_sha256))
    elif expected_definition_referents_profile_sha256 is not None:
        raise ValueError('Definition-referent profile pin supplied without a profile')
    if definition_remainders_profile is not None:
        from .definition_remainders import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, definition_remainders_profile, root,
            expected_profile_sha256=expected_definition_remainders_profile_sha256))
    elif expected_definition_remainders_profile_sha256 is not None:
        raise ValueError('Definition-remainder profile pin supplied without a profile')
    if definition_dependencies_profile is not None:
        from .definition_dependencies import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, definition_dependencies_profile, root,
            expected_profile_sha256=expected_definition_dependencies_profile_sha256))
    elif expected_definition_dependencies_profile_sha256 is not None:
        raise ValueError('Definition-dependency profile pin supplied without a profile')
    if rating_labels_profile is not None:
        from .rating_labels import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, rating_labels_profile, root,
            expected_profile_sha256=expected_rating_labels_profile_sha256))
    elif expected_rating_labels_profile_sha256 is not None:
        raise ValueError('Rating-label profile pin supplied without a profile')
    if cycle_dispositions_profile is not None:
        from .cycle_dispositions import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, cycle_dispositions_profile, root,
            expected_profile_sha256=expected_cycle_dispositions_profile_sha256))
    elif expected_cycle_dispositions_profile_sha256 is not None:
        raise ValueError('Cycle-disposition profile pin supplied without a profile')
    if paragraph_references_profile is not None:
        from .paragraph_references import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, paragraph_references_profile, root,
            expected_profile_sha256=expected_paragraph_references_profile_sha256))
    elif expected_paragraph_references_profile_sha256 is not None:
        raise ValueError('Paragraph-reference profile pin supplied without a profile')
    if reference_scope_profile is not None:
        from .reference_scope import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, reference_scope_profile, root,
            expected_profile_sha256=expected_reference_scope_profile_sha256))
    elif expected_reference_scope_profile_sha256 is not None:
        raise ValueError('Reference-scope profile pin supplied without a profile')
    if reference_addresses_profile is not None:
        from .reference_addresses import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, reference_addresses_profile, root,
            expected_profile_sha256=expected_reference_addresses_profile_sha256))
    elif expected_reference_addresses_profile_sha256 is not None:
        raise ValueError('Reference-address profile pin supplied without a profile')
    if standalone_sections_profile is not None:
        from .standalone_sections import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, standalone_sections_profile, root,
            expected_profile_sha256=expected_standalone_sections_profile_sha256))
    elif expected_standalone_sections_profile_sha256 is not None:
        raise ValueError('Standalone-section profile pin supplied without a profile')
    if unquoted_definitions_profile is not None:
        from .unquoted_definitions import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, unquoted_definitions_profile, root,
            expected_profile_sha256=expected_unquoted_definitions_profile_sha256))
    elif expected_unquoted_definitions_profile_sha256 is not None:
        raise ValueError('Unquoted-definition profile pin supplied without a profile')
    if purpose_uses_profile is not None:
        from .purpose_uses import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, purpose_uses_profile, root,
            expected_profile_sha256=expected_purpose_uses_profile_sha256))
    elif expected_purpose_uses_profile_sha256 is not None:
        raise ValueError('Purpose-use profile pin supplied without a profile')
    if bgb_onward_profile is not None:
        from .bgb_onward import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, bgb_onward_profile, root,
            expected_profile_sha256=expected_bgb_onward_profile_sha256))
    elif expected_bgb_onward_profile_sha256 is not None:
        raise ValueError('BGB onward profile pin supplied without a profile')
    if holder_authority_profile is not None:
        from .default_holder import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, holder_authority_profile, root,
            expected_profile_sha256=expected_holder_authority_profile_sha256))
    elif expected_holder_authority_profile_sha256 is not None:
        raise ValueError('Holder-authority profile pin supplied without a profile')
    if issuer_qualification_profile is not None:
        from .issuer_qualification import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, issuer_qualification_profile, root,
            expected_profile_sha256=expected_issuer_qualification_profile_sha256))
    elif expected_issuer_qualification_profile_sha256 is not None:
        raise ValueError('Issuer-qualification profile pin supplied without a profile')
    if office_change_profile is not None:
        from .office_change import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, office_change_profile, root,
            expected_profile_sha256=expected_office_change_profile_sha256))
    elif expected_office_change_profile_sha256 is not None:
        raise ValueError('Office-change profile pin supplied without a profile')
    if election_profile is not None:
        from .election import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, election_profile, root,
            expected_profile_sha256=expected_election_profile_sha256))
    elif expected_election_profile_sha256 is not None:
        raise ValueError('Election profile pin supplied without a profile')
    if home_routes_profile is not None:
        from .home_routes import evaluate
        baseline = {**result, 'report_sha256': digest(result)}
        result.update(evaluate(products, baseline, home_routes_profile, root,
            expected_profile_sha256=expected_home_routes_profile_sha256))
    elif expected_home_routes_profile_sha256 is not None:
        raise ValueError('Home-route profile pin supplied without a profile')
    return {**result, "report_sha256": digest(result)}


def assess(request, root, bank=None):
    p1 = source_product(request, root)
    p2 = construction_product(p1, root)
    p3 = interpretation_product(p1, p2)
    result = consume({"P1": p1, "P2": p2, "P3": p3, "P4": law_product(p1, p3),
                    "P5": financial_product(p1, p2, p3)}, root, bank, include_artifacts=True)
    result["assessment_mode"] = "fresh"
    result["report_sha256"] = digest({k:v for k,v in result.items() if k != "report_sha256"})
    return result


def configure(parser):
    commands = parser.add_subparsers(dest="prospectus_command", required=True)
    from .preparation import configure as configure_preparation
    configure_preparation(commands)
    scope_evidence = commands.add_parser("discover-definition-scope")
    scope_evidence.add_argument("--request", required=True)
    scope_evidence.add_argument("--output", required=True)
    declarations = commands.add_parser("discover-definition-declarations")
    declarations.add_argument("--request", required=True)
    declarations.add_argument("--output", required=True)
    declaration_review = commands.add_parser("reconcile-definition-declarations")
    declaration_review.add_argument("--request", required=True)
    declaration_review.add_argument("--discovery", required=True)
    declaration_review.add_argument("--lineage", required=True)
    declaration_review.add_argument("--output", required=True)
    discovery = commands.add_parser("discover-references")
    discovery.add_argument("--request", required=True)
    discovery.add_argument("--output", required=True)
    resolution = commands.add_parser("resolve-references")
    resolution.add_argument("--request", required=True)
    resolution.add_argument("--output", required=True)
    reconciliation = commands.add_parser("reconcile-references")
    reconciliation.add_argument("--request", required=True)
    reconciliation.add_argument("--resolution", required=True)
    reconciliation.add_argument("--reviewed-graph", required=True)
    reconciliation.add_argument("--output", required=True)
    for name, arg in (("assess", "--request"), ("consume", "--products")):
        p = commands.add_parser(name)
        p.add_argument(arg, required=True)
        p.add_argument("--repository", default=".")
        p.add_argument("--output", required=True)
        if name == "consume":
            p.add_argument("--mode", choices=("frozen", "current"), default="frozen")
            p.add_argument("--conditional-profiles", help="Repository-relative pinned profile manifest")
            p.add_argument("--conditional-profiles-sha256", help="SHA256 of the conditional manifest bytes")


def dispatch(args):
    if args.prospectus_command == "discover-definition-scope":
        from .definition_scope_evidence import discover
        report = discover(read(args.request))
        write(args.output, report)
        return {"report": args.output, "report_sha256": report["report_sha256"]}
    if args.prospectus_command in ("discover-definition-declarations", "reconcile-definition-declarations"):
        from .definition_declarations import discover, reconcile
        request = read(args.request)
        report = (discover(request) if args.prospectus_command == "discover-definition-declarations" else
                  reconcile(request, read(args.discovery), read(args.lineage)))
        write(args.output, report)
        return {"report": args.output, "report_sha256": report["report_sha256"]}
    if args.prospectus_command in ("resolve-references", "reconcile-references"):
        from .reference_resolution import resolve, reconcile
        request = read(args.request)
        report = (resolve(request) if args.prospectus_command == "resolve-references" else
                  reconcile(request, read(args.resolution), read(args.reviewed_graph)))
        write(args.output, report)
        return {"report": args.output, "report_sha256": report["report_sha256"]}
    if args.prospectus_command == "discover-references":
        from .reference_mentions import discover
        report = discover(read(args.request))
        write(args.output, report)
        return {"report": args.output, "report_sha256": report["report_sha256"],
                "mentions": len(report["mentions"]), "issues": len(report["issues"])}
    if args.prospectus_command == "prepare":
        from .preparation import dispatch as prepare_dispatch
        return prepare_dispatch(args)
    root = Path(args.repository)
    if args.prospectus_command == "consume":
        from .conditional_profiles import load
        profile_options = load(root, getattr(args, "conditional_profiles", None),
                               getattr(args, "conditional_profiles_sha256", None))
        manifest = read(args.products)
        products = {}
        for stage, row in manifest["products"].items():
            path = bound_path(root, row["path"])
            if digest(path.read_bytes()) != row["sha256"]:
                raise ValueError("Stored product bytes changed: " + stage)
            products[stage] = read(path)
        bank = manifest.get("bank")
        if bank:
            from ...transaction.evidence import Store
            bank = {**bank, "store": Store(bound_path(root, bank["store"]))}
        result = consume(products, root, bank, mode=getattr(args, "mode", "frozen"), **profile_options)
    else:
        result = assess(read(args.request), root)
    write(args.output, result)
    return {"report": args.output, "report_sha256": result["report_sha256"],
            "questions": {q: r["status"] for q, r in result["questions"].items()}, "may_execute_transaction": False}
