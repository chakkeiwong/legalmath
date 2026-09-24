"""Source-bound alternative groups and vector composition of independent controls."""
from copy import deepcopy
from itertools import islice, product
from math import prod
from pathlib import Path
from typing import Literal
from pydantic import Field
from ...canonical import canonical, digest, loads, raw_digest
from ...errors import LegalMathError
from ...ir.typecheck import validate_bundle
from ...java.manifest import build_candidate, verify_candidate
from ..contracts import Strict, Id, Hash, Text, Packet, parse
from ..search.models import Reading
from ..search.formal import bundle, snapshots
from .semantics import AtomicClaim, check_quotes, validate_fidelity_aggregate


class Component(Strict):
    component_id: Id
    question: Text
    claim_ids: list[Id] = Field(min_length=1, max_length=100)
    candidate_ids: list[Id] = Field(min_length=1, max_length=64)
    output_meaning: Literal['TRUE_IS_PROHIBITED', 'TRUE_IS_COMPLIANT', 'VALUE']
    assignment_basis: Text


class Exclusion(Strict):
    candidate_id: Id
    reason: Text


class CompositionSpec(Strict):
    version: Literal['composition.v1']
    source_packet_hash: Hash
    claims_hash: Hash
    candidates_hash: Hash
    components: list[Component] = Field(min_length=1, max_length=16)
    excluded_candidates: list[Exclusion] = Field(max_length=128)
    max_combinations: int = Field(default=16, ge=1, le=128)


def unique(values):
    if len(values) != len(set(values)):
        raise LegalMathError('E_DUPLICATE_ID')


def check_spec(value, packet, claims, candidates, fidelity):
    spec = parse(CompositionSpec, value); parse(Packet, packet)
    if (spec['source_packet_hash'] != digest(packet) or spec['claims_hash'] != digest(claims)
            or spec['candidates_hash'] != digest(candidates)):
        raise LegalMathError('E_STALE_REVIEW', details='Composition inputs changed')
    if not candidates or len(candidates) > 128 or len(claims) > 1000:
        raise LegalMathError('E_RESOURCE_LIMIT')
    by_claim = {}
    for claim in claims:
        checked = parse(AtomicClaim, {k: v for k, v in claim.items() if k != 'readers'})
        # Inventory merger adds provenance; retain the complete original below.
        check_quotes(checked['evidence'], packet)
        if checked['claim_id'] in by_claim: raise LegalMathError('E_DUPLICATE_ID')
        by_claim[checked['claim_id']] = claim
    for reading in candidates.values():
        parse(Reading, reading); check_quotes(reading['citations'], packet)
        if reading['formalization']:
            for fact in reading['formalization']['facts']:
                if not set(fact['source_unit_ids']) <= {u['unit_id'] for u in packet['units']}:
                    raise LegalMathError('E_REFERENCE')
    if fidelity is not None:
        validate_fidelity_aggregate(fidelity, packet, claims, candidates)
    unique([c['component_id'] for c in spec['components']])
    assigned = []; covered = []
    for component in spec['components']:
        unique(component['claim_ids']); unique(component['candidate_ids'])
        if not set(component['claim_ids']) <= set(by_claim) or not set(component['candidate_ids']) <= set(candidates):
            raise LegalMathError('E_REFERENCE')
        if any(by_claim[c]['relevance'] == 'CONTEXT' for c in component['claim_ids']):
            raise LegalMathError('E_REFERENCE', details='Context alone cannot count as a covered control')
        for cid in component['candidate_ids']:
            r = candidates[cid]; formal = r['formalization']
            if formal and ((formal['result_type'] == 'bool') != (component['output_meaning'] != 'VALUE')):
                raise LegalMathError('E_TYPE', details='Output convention and result type disagree')
            if not r['statement'].startswith('[' + component['output_meaning'] + ']'):
                raise LegalMathError('E_SCHEMA', details='Component output convention must be explicit in each reading')
        assigned.extend(component['candidate_ids']); covered.extend(component['claim_ids'])
    # A claim may belong to several interacting controls, but a candidate cannot
    # be re-labelled as several independent controls to fabricate coverage.
    unique(assigned)
    excluded = [e['candidate_id'] for e in spec['excluded_candidates']]; unique(excluded)
    if set(excluded) & set(assigned) or not set(excluded) <= set(candidates):
        raise LegalMathError('E_REFERENCE')
    findings = []
    for cid in sorted(set(candidates) - set(assigned) - set(excluded)):
        findings.append({'kind': 'UNASSIGNED_CANDIDATE', 'candidate_id': cid})
    for cid in sorted(c['claim_id'] for c in claims if c['relevance'] != 'CONTEXT' and c['claim_id'] not in covered):
        findings.append({'kind': 'UNCOVERED_SOURCE_CLAIM', 'claim_id': cid})
    return spec, by_claim, findings


def combine(components, chosen, candidates, packet, at):
    """Disjoint rule/fact namespaces preserve each component's actual expression."""
    result = None; bindings = []; spans = {}
    for index, (component, cid) in enumerate(zip(components, chosen)):
        original = bundle(candidates[cid], packet, at); local = deepcopy(original)
        prefix = 'c' + str(index) + '.'
        mapping = {f['name']: prefix + f['name'] for f in original['facts']}
        def visit(node):
            if isinstance(node, dict):
                if 'node_id' in node: node['node_id'] = prefix + node['node_id']
                if node.get('op') == 'fact': node['name'] = mapping[node['name']]
                for item in node.values(): visit(item)
            elif isinstance(node, list):
                for item in node: visit(item)
        visit(local['rules'])
        for f in local['facts']: f['name'] = mapping[f['name']]
        for r in local['rules']:
            r['id'] = prefix + r['id']; r['interpretation_id'] = prefix + r['interpretation_id']
        for i in local['interpretations']: i['id'] = prefix + i['id']
        for span in original['source_spans']:
            if span['id'] in spans and spans[span['id']] != span: raise LegalMathError('E_INTEGRITY')
            spans[span['id']] = span
        if result is None:
            result = {**local, 'facts': [], 'rules': [], 'interpretations': []}
        for field in ('facts', 'rules', 'interpretations'): result[field].extend(local[field])
        bindings.append({'component_id': component['component_id'], 'candidate_id': cid,
                         'rule_id': local['rules'][0]['id'], 'fact_mapping': mapping,
                         'output_meaning': component['output_meaning'], 'original_bundle': original})
    result['source_spans'] = list(spans.values())
    result['bundle_id'] = 'composition.' + digest({'components': components, 'chosen': list(chosen), 'at': at})[:24]
    errors = validate_bundle(result)
    if errors: raise LegalMathError(errors[0]['code'], details=errors)
    return result, bindings


def compose(value, packet, claims, candidates, fidelity, at, *, jdk=None, out=None, upstream_findings=()):
    spec, by_claim, findings = check_spec(value, packet, claims, candidates, fidelity)
    inherited = deepcopy(list(upstream_findings))
    if inherited: findings.append({'kind':'UPSTREAM_UNCERTAINTY','count':len(inherited)})
    concerns = deepcopy((fidelity or {}).get('additional_concerns', []))
    if concerns: findings.append({'kind':'ADDITIONAL_SOURCE_CONCERNS','count':len(concerns)})
    if (jdk is None) != (out is None): raise LegalMathError('E_SCHEMA')
    if out is not None:
        out = Path(out)
        if out.exists(): raise LegalMathError('E_IDEMPOTENCY', details='Use a fresh composition directory')
        out.mkdir(parents=True)
        (out/'inputs.json').write_bytes(canonical({'spec':spec,'packet':packet,'claims':claims,
                                                  'candidates':candidates,'fidelity':fidelity,'at':at,
                                                  'upstream_findings':inherited}))
    rows = {(c['claim_id'], c['candidate_id']): c for c in (fidelity or {}).get('checks', [])}
    support = []
    for component in spec['components']:
        for cid in component['candidate_ids']:
            checks = [rows.get((claim, cid)) for claim in component['claim_ids']]
            supported = all(check is not None and check['label'] == 'ENTAILED' for check in checks)
            support.append({'component_id':component['component_id'],'candidate_id':cid,
                            'model_support_complete':supported,'checks':checks})
            if not supported: findings.append({'kind':'COMPONENT_SUPPORT_UNRESOLVED',
                'component_id':component['component_id'],'candidate_id':cid})
    total = prod(len(c['candidate_ids']) for c in spec['components']); combinations = []
    for chosen in islice(product(*(c['candidate_ids'] for c in spec['components'])), spec['max_combinations']):
        record = {'selection':dict(zip((c['component_id'] for c in spec['components']),chosen))}
        if any(candidates[cid]['formalization'] is None for cid in chosen):
            record['status'] = 'UNSUPPORTED_COMPONENT'; combinations.append(record); continue
        try: compiled, bindings = combine(spec['components'],chosen,candidates,packet,at)
        except LegalMathError as exc:
            record.update(status='UNSUPPORTED_COMPONENT',error=exc.code,details=exc.details)
            combinations.append(record); continue
        record.update(status='COMPOSED_UNVERIFIED', bundle=compiled, bindings=bindings,
                      bundle_hash=digest(compiled), verification=None, build=None)
        if out is not None:
            directory = out/('alternative.'+digest(record['selection'])[:24])
            build = build_candidate(compiled,directory,jdk); cases = []
            for binding in bindings:
                original = binding['original_bundle']
                probes = list(snapshots([original],at,maximum=24))
                # Exercise conflicts explicitly; generic search probes are T/F/U.
                for fact in original['facts']:
                    conflict = deepcopy(probes[0]); conflict['facts'][fact['name']] = {
                        'type':fact['type'],'status':'conflict','evidence_ids':['conflicting.one','conflicting.two']}
                    probes.append(conflict)
                for index, snapshot in enumerate(probes):
                    from ...ir.evaluate import evaluate
                    expected = evaluate(original,snapshot,'selected.control',at,at)
                    facts = {f['name']:{'type':f['type'],'status':'unknown','reason':'MISSING'} for f in compiled['facts']}
                    facts.update({binding['fact_mapping'][k]:v for k,v in snapshot['facts'].items()})
                    mapped = {**snapshot,'facts':facts}
                    cases.append({'id':binding['component_id']+'.'+str(index),'bundle':compiled,
                        'snapshot':mapped,'rule_id':binding['rule_id'],'valid_at':at,'known_at':at,
                        'expected':{k:expected[k] for k in ('status','type','value') if k in expected}})
            verification = verify_candidate(build,cases,jdk)
            (directory/'bundle.json').write_bytes(canonical(compiled))
            (directory/'cases.json').write_bytes(canonical(cases))
            record.update(status='JAVA_VECTOR_CONFORMANCE',build=build,verification=verification)
        combinations.append(record)
    deferred = total-len(combinations)
    if deferred: findings.append({'kind':'COMBINATION_LIMIT','deferred':deferred})
    if any(c['status']=='UNSUPPORTED_COMPONENT' for c in combinations):
        findings.append({'kind':'UNSUPPORTED_COMPONENT'})
    result = {'version':'composition.v1','spec_hash':digest(spec),'source_packet_hash':digest(packet),
        'status':'INCOMPLETE' if findings else 'DECLARED_COVERAGE_ACCOUNTED', 'findings':findings,
        'components':[{**c,'source_claims':[by_claim[x] for x in c['claim_ids']]} for c in spec['components']],
        'excluded_candidates':spec['excluded_candidates'],'support':support,'total_combinations':total,
        'upstream_findings':inherited,'additional_source_concerns':concerns,
        'deferred_combinations':deferred,'combinations':combinations,
        'assignment_authority':'PROPOSED_EXPLICIT_GROUPING','legal_source_commitment_resolved':False,
        'release_eligible':False,'component_compatibility_proved':False,
        'limits':['Vector of scoped controls; no aggregate compliance verdict',
                  'Support judgments and grouping are defeasible; coverage of inventoried claims only',
                  'Namespaced facts require explicit host bindings; shared facts are not silently unified']}
    if out is not None:
        (out/'report.json').write_bytes(canonical(result))
        (out/'manifest.json').write_bytes(canonical({'files':{str(p.relative_to(out)):raw_digest(p.read_bytes())
            for p in sorted(out.rglob('*')) if p.is_file()}}))
    return result


def execute(args):
    directory = Path(args.investigation).resolve()
    manifest = loads((directory/'manifest.json').read_bytes())
    for name, expected in manifest['files'].items():
        path = (directory/name).resolve()
        if not path.is_relative_to(directory) or raw_digest(path.read_bytes()) != expected:
            raise LegalMathError('E_INTEGRITY')
    for name in ('packet.json','claims.json','search-state.json','report.json','request.json'):
        if name not in manifest['files']: raise LegalMathError('E_INTEGRITY')
    report = loads((directory/'report.json').read_bytes())
    if report.get('status') == 'FAILED_INTEGRITY': raise LegalMathError('E_INTEGRITY')
    state = loads((directory/'search-state.json').read_bytes())
    # The final candidate file includes repairs/deferred readings absent from the
    # original search snapshot. Never omit those alternatives when composing.
    candidates_path = directory/'candidates.json'
    candidates = loads(candidates_path.read_bytes()) if 'candidates.json' in manifest['files'] else {
        n['node_id']:n['reading'] for n in state['nodes']}
    if set(candidates) != set(report['candidate_ids']):
        raise LegalMathError('E_REFERENCE', details='Retained final candidate universe is incomplete')
    request = loads((directory/'request.json').read_bytes())
    return compose(loads(Path(args.spec).read_bytes()),loads((directory/'packet.json').read_bytes()),
        loads((directory/'claims.json').read_bytes()),candidates,report['fidelity'],request['at'],
        jdk=args.jdk,out=args.out,upstream_findings=report.get('findings', []))
