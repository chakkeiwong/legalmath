"""Explicit source-reviewed references beyond the bounded heading recognizer."""
from .admissions import review
from .anchors import fields, bind
from .contracts import digest
from .occurrences import uses, target


def admit(graph, assembly, packet, *, _lookup=None):
    if _lookup is not None:
        _lookup._check(graph, assembly)
    locate = uses if _lookup is None else _lookup.uses
    required={'version','assembly_sha256','review','references'}
    structural=set()
    if packet['version']=='reviewed-references.v4':
        required.add('structural_role_review')
        from .structural_roles import reference_context
        structural=reference_context(graph,assembly,packet)
    fields(packet,required,required)
    if packet['version'] not in {'reviewed-references.v1', 'reviewed-references.v2', 'reviewed-references.v3', 'reviewed-references.v4'} or packet['assembly_sha256'] != digest(assembly):
        raise ValueError('Reviewed reference assembly changed')
    review(packet['review'])
    from .basf_call_references import check as check_call_references
    check_call_references(graph, assembly, packet)
    from .basf_payment_references import check as check_payment_references
    check_payment_references(graph, assembly, packet)
    from .basf_legacy_references import check as check_legacy_references
    check_legacy_references(graph, assembly, packet)
    from .basf_governance_references import check as check_governance_references
    check_governance_references(graph, assembly, packet)
    from .basf_default_references import check as check_default_references
    check_default_references(graph, assembly, packet)
    from .basf_substitution_references import check as check_substitution_references
    check_substitution_references(graph, assembly, packet)
    from .basf_financial_references import check as check_financial_references
    check_financial_references(graph, assembly, packet)
    from .basf_internal_references import check as check_internal_references
    check_internal_references(graph, assembly, packet)
    selected = {u['unit']:u for u in assembly['units']}
    raw = {u['id']:u for u in graph['units']}
    discovered = {r['id']:r for r in graph.get('references', [])}
    claimed = set()
    ids, dependencies, edges = set(), [], []
    for row in packet['references']:
        required = {'id','form','source','from_use','language','targets','authority','questions','reason'}
        if packet['version'] in {'reviewed-references.v2', 'reviewed-references.v3', 'reviewed-references.v4'}:
            required.add('discovery_ids')
        fields(row, required, required)
        if (not row['id'] or row['id'] in ids or row['form'] not in {'named','relative','external','amendment'} or
                not row['reason'] or not row['questions'] or set(row['questions']) - {'Q1','Q2'}):
            raise ValueError('Invalid reviewed reference')
        ids.add(row['id'])
        bind(graph,row['source'])
        if raw[row['source']['unit']]['language'] != row['language']:
            raise ValueError('Reference language differs from source')
        from .bes_statement_scope import check as check_statement_scope
        statement_scope = check_statement_scope(graph, assembly, row)
        discovery_ids = row.get('discovery_ids', [])
        if (not isinstance(discovery_ids, list) or any(not isinstance(key,str) for key in discovery_ids)
                or len(set(discovery_ids)) != len(discovery_ids)):
            raise ValueError('Distinct discovery identities required')
        for key in discovery_ids:
            proposal = discovered.get(key)
            source = row['source']
            if (proposal is None or proposal['unit'] != source['unit'] or
                    proposal['document'] != source['document'] or proposal['source_sha256'] != source['source_sha256'] or
                    not source['start'] <= proposal['start'] < proposal['end'] <= source['end'] or
                    raw[source['unit']]['raw'][proposal['start']:proposal['end']] != proposal['text']):
                raise ValueError('Reviewed reference does not cover its discovered source')
            for question in row['questions']:
                identity = (key, row['from_use'], question)
                if identity in claimed:
                    raise ValueError('Discovered reference has multiple reviewed replacements')
                claimed.add(identity)
        if not row['targets']:
            raise ValueError('Reviewed reference needs exact targets')
        destinations = []
        contexts = []
        seen_targets = set()
        unknown_targets = []
        for value in row['targets']:
            fields(value, {'source','use','language'}, {'source','use','language'})
            key=digest(value)
            if packet['version']=='reviewed-references.v4' and key in seen_targets:
                raise ValueError('Duplicate reviewed target')
            seen_targets.add(key)
            context=value['use'] in structural
            if context:
                matches=locate(graph,assembly,value['source'],roles=('HEADER',))
                matches=[m for m in matches if m['unit']==value['use']]
                if len(matches)!=1:
                    raise ValueError('Structural context is not an exact source occurrence')
                found=matches[0]
            else:
                found = target(graph, assembly, {k:value[k] for k in ('source','use')}, _lookup=_lookup)
            if (raw[value['source']['unit']]['language'] != value['language'] or
                    selected[found['unit']]['role'] not in (('HEADER',) if context else (('OPERATIVE', 'UNKNOWN') if packet['version'] in {'reviewed-references.v3','reviewed-references.v4'} else ('OPERATIVE',))) or
                    not set(row['questions']) <= set(selected[found['unit']]['questions'])):
                raise ValueError('Reference target is not operative in the declared language/question')
            if row['form']=='external' and value['source']['document']==row['source']['document']:
                raise ValueError('External reference requires another document')
            (contexts if context else destinations).append(found)
            if selected[found['unit']]['role'] == 'UNKNOWN':
                unknown_targets.append(found['unit'])
        if not destinations:
            raise ValueError('Reviewed reference requires a substantive target')
        for question in row['questions']:
            referring = [m for m in locate(graph,assembly,row['source'],question=question) if m['unit']==row['from_use']]
            if len(referring)!=1 or len(locate(graph,assembly,row['authority'],question=question))!=1:
                raise ValueError('Reference source/authority is not an unambiguous selected occurrence')
        identity = 'reviewed-reference:'+row['id']
        dependencies.append({'id':identity,'questions':row['questions'],'status':'UNRESOLVED' if unknown_targets else 'RESOLVED',
            'source_use':referring[0],'targets':destinations,'form':row['form'],
            'discovery_ids':discovery_ids,
            **({'structural_targets':contexts,'structural_role_review':packet['structural_role_review']} if contexts else {}),
            'authority':row['authority'],'review':packet['review'],'automatic_discovery':False,
            **({'source_binding':'RESOLVED','unknown_target_uses':sorted(set(unknown_targets))} if unknown_targets else {}),
            **({'statement_scope_check':statement_scope} if statement_scope else {})})
        for destination in destinations:
            edges.append({'id':identity,'from':row['from_use'],'to':destination['unit'],
                'kind':'reference','resolved':not unknown_targets,'authority':row['authority'], 'questions':row['questions']})
    return dependencies, edges


def verify_consumed(graph, assembly, request, semantic):
    _verify_consumed(graph, assembly, request, semantic)


def _verify_consumed(graph, assembly, request, semantic):
    """A resealed product must still contain the admitted source dependencies.

    Generic admission proves occurrence consistency. Source-specific validators
    invoked by admit provide only their explicitly reviewed interpretation.
    Neither a hash nor this replay supplies an unreviewed target meaning.
    """
    packet = request.get('reference_admission')
    expected = []
    if packet is not None:
        from .occurrences import _DependencyLookup
        expected, _ = admit(graph, assembly, packet, _lookup=_DependencyLookup(graph, assembly))
    actual = [d for d in semantic['dependencies'] if d['id'].startswith('reviewed-reference:')]
    if digest(sorted(actual, key=lambda d: d['id'])) != digest(sorted(expected, key=lambda d: d['id'])):
        raise ValueError('Consumed reviewed-reference dependencies differ from source admission')
    if packet is not None and packet['version'] in {'reviewed-references.v3','reviewed-references.v4'}:
        for question in ('Q1', 'Q2'):
            required = {d['id'] for d in expected if d['status'] == 'UNRESOLVED' and question in d['questions']}
            closures = [d for d in semantic['dependencies'] if d['id'] == 'reference-closure:' + question]
            closure_required = {'Unresolved reference: ' + key for key in required}
            if required and len(closures) != 1:
                raise ValueError('Consumed reviewed reference lacks unresolved closure')
            if closures:
                closure_actual = {key for key in closures[0].get('unresolved', [])
                                  if key.startswith('Unresolved reference: reviewed-reference:')}
                if closure_actual != closure_required:
                    raise ValueError('Consumed reviewed reference closure hides or invents target uncertainty')
            for answer in [semantic['questions'][question], *semantic['questions'][question].get('subquestions', {}).values()]:
                actual_unknown = {key for key in answer['unresolved'] if key.startswith('reviewed-reference:')}
                if actual_unknown != required:
                    raise ValueError('Consumed reviewed reference hides or invents unresolved target meaning')
                if required and 'reference-closure:' + question not in answer['unresolved']:
                    raise ValueError('Consumed reviewed reference hides unresolved closure in question')
    return expected


def verify_consumed_families(graph, assembly, request, semantic):
    """Validate once, then check every family's reports and uncertainty.

    All reusable dependencies are created inside this call, after full admission
    and comparison to the consumed product. They never survive the call. The
    family checks still validate their source selections and missing links;
    standalone family APIs continue to perform their own admission.
    """
    from . import (basf_call_references, basf_payment_references,
                   basf_legacy_references, basf_governance_references,
                   basf_default_references, basf_substitution_references,
                   basf_financial_references, basf_internal_references)

    resolved = _verify_consumed(graph, assembly, request, semantic)
    families = (
        ('call', basf_call_references), ('payment', basf_payment_references),
        ('legacy', basf_legacy_references), ('governance', basf_governance_references),
        ('default', basf_default_references), ('substitution', basf_substitution_references),
        ('financial', basf_financial_references), ('internal', basf_internal_references),
    )
    reports = {}
    for name, family in families:
        if name == 'legacy':
            reports[name] = family.verify_consumed(graph, assembly, request, semantic)
        else:
            reports[name] = family._verify_consumed(
                graph, assembly, request, semantic, _resolved=resolved)
    return reports
