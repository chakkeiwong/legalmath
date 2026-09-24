"""Offline integration of five scoped, unreviewed source-to-Java candidates.

The literal expected scenarios are stored separately from the RuleIR builders.
Neither this harness nor the scripted members claim to interpret English.
"""
from copy import deepcopy
import json
from pathlib import Path
import re

from legalmath.canonical import canonical, digest, raw_digest
from legalmath.conformance import evaluate_case
from legalmath.errors import LegalMathError
from legalmath.interpretation.controller import Controller
from legalmath.interpretation.reports import Reports
from legalmath.interpretation.review import MeaningReview, guard
from legalmath.interpretation.service import Interpretations
from legalmath.ir.trace import verify_result
from legalmath.ir.typecheck import validate_bundle
from legalmath.java.manifest import build_candidate, run_java
from legalmath.review.lifecycle import Lifecycle
from legalmath.review.releases import Releases
from legalmath.sources.anchors import make_span
from legalmath.sources.extract import extract
from legalmath.sources.intake import import_source, resolve_span
from legalmath.storage import Database

REFS = ('23EC49', '24EC16', '24EC50', '24EC57', '26EC23')
START = '2020-01-01T00:00:00.000000Z'
AT = '2026-09-23T00:00:00.000000Z'
END = '2030-01-01T00:00:00.000000Z'
IDENTITIES = {
    'author': {'token': 'multi-author-fixture', 'roles': ['author']},
    'meaning': {'token': 'multi-meaning-fixture', 'roles': ['meaning']},
    'engineer': {'token': 'multi-engineer-fixture', 'roles': ['engineering']},
}


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n')


def load_fixture(root):
    base = Path(root) / 'examples/multi-circular-2026'
    freeze = json.loads((base / 'source-freeze.json').read_bytes())
    raw = (Path(root) / freeze['corpus_path']).read_bytes()
    if raw_digest(raw) != freeze['corpus_sha256']:
        raise AssertionError('Frozen source-written oracle changed')
    corpus = json.loads(raw)
    assert tuple(c['ref_no'] for c in corpus['cases']) == REFS
    return corpus, freeze


def load_sources(db, root, freeze):
    sources = {}
    with db.transaction() as con:
        for item in freeze['sources']:
            raw = (Path(root) / item['raw_path']).read_bytes()
            text = (Path(root) / item['text_path']).read_text()
            assert raw_digest(raw) == item['raw_sha256'], item['source_id']
            assert raw_digest(text.encode()) == item['text_sha256'], item['source_id']
            actual, extractor = extract(raw, item['media_type'])
            assert actual == text and extractor == item['extractor'], item['source_id']
            if item['media_type'] == 'application/json':
                doc = json.loads(raw)
                assert doc['refNo'] == item['source_id'] and doc['lang'] == 'EN'
            imported = import_source(db, con, item['source_id'], raw, item['media_type'],
                item['official_url'], freeze['frozen_at'], retained_text=text,
                extractor=item['extractor'], authority='RETAINED_PUBLIC_SOURCE',
                source_kind='annex' if item['source_id'].endswith('/appendix') else 'circular')
            sources[item['source_id']] = {**item, **imported, 'raw': raw, 'text': text}
    return sources


def inventory(source, *, normative=True):
    """Every non-whitespace derivative character, including headers/footnotes.

    Normative=True is conservative pending human classification. It is not an
    assertion that address lines or headings impose duties.
    """
    units = []
    for match in re.finditer(r'[^\r\n\f]+', source['text']):
        fragment = match.group()
        if not fragment.strip():
            continue
        start = match.start() + len(fragment) - len(fragment.lstrip())
        end = match.end() - len(fragment) + len(fragment.rstrip())
        uid = 's.' + source['source_id'].lower().replace('/', '.') + f'.u{len(units):04d}'
        units.append(dict(unit_id=uid, locator=source['source_id'] + f' chars {start}:{end}',
            text=source['text'][start:end], normative=normative,
            span=make_span(uid, source['source_id'], source['raw'], source['text'], start, end)))
    assert sum(sum(not c.isspace() for c in u['text']) for u in units) == sum(not c.isspace() for c in source['text'])
    assert all(a['span']['end'] <= b['span']['start'] for a, b in zip(units, units[1:]))
    return units


def packet_for(case, sources):
    units = inventory(sources[case['ref_no']])
    if case['ref_no'] == '23EC49':
        units += inventory(sources['23EC49/appendix'])
    selected = []
    for anchor in case['anchors']:
        matches = [u for u in units if anchor in u['text']]
        assert len(matches) == 1, (case['ref_no'], anchor, len(matches))
        if matches[0] not in selected:
            selected.append(matches[0])
    critical = next(u['unit_id'] for u in selected if case['critical_anchor'] in u['text'])
    dependencies = [dict(dependency_id=d['id'], source_hash=sources[d['source_ref']]['source_hash'] if d['source_ref'] else None)
                    for d in case['dependencies']]
    if case['ref_no'] == '23EC49':
        dependencies.append(dict(dependency_id='illustrative-appendix', source_hash=sources['23EC49/appendix']['source_hash']))
    packet = dict(source_key='corpus.' + case['ref_no'].lower(), authority='RETAINED_SOURCE',
        selected_slice=case['selected_slice'], units=units, dependencies=dependencies,
        family_ids=['proposed-slice'] + [x['id'] for x in case['alternatives']])
    return packet, selected, critical


class Nodes:
    """Small RuleIR construction helper; no evaluation or oracle logic."""
    def __init__(self): self.counter = 0
    def node(self, op, **fields):
        self.counter += 1
        return dict(node_id=f'n.{self.counter}', op=op, **fields)
    def fact(self, name): return self.node('fact', name=name)
    def literal(self, value, typ='bool'): return self.node('literal', type=typ, value=value)
    def all(self, *args): return self.node('all', args=list(args))
    def any(self, *args): return self.node('any', args=list(args))
    def compare(self, cmp, left, right): return self.node('compare', cmp=cmp, left=left, right=right)
    def choose(self, condition, yes, no): return self.node('if', condition=condition, then=yes, **{'else':no})


def bundle_for(case, selected, variant=None):
    n = Nodes(); f = n.fact; lit = n.literal; cmp = n.compare; choose = n.choose
    ref = case['ref_no']; typ = 'bool'
    if ref == '23EC49':
        scope = n.all(f('authorised_mmf'), f('annualised_under_year'))
        parts = [f('basis_disclosed'), cmp('gt' if variant == 'strict_six_months' else 'ge', f('track_record_months'), lit('6', 'integer'))]
        if variant != 'omit_seven_day': parts.append(f('seven_day_present'))
        parts.append(choose(n.all(f('additional_return'), cmp('gt', lit('7','integer'), f('additional_days'))),
            choose(f('interactive'), f('updated_daily'), f('daily_figure_link')), lit(True)))
        body = n.all(*parts)
    elif ref == '24EC16':
        market = n.any(cmp('eq', f('market_code'), lit('1','integer')), cmp('eq', f('market_code'), lit('2','integer')))
        scope = market if variant == 'include_fx' else n.all(f('standard_security'), market)
        cutoff = lit('2024-05-28','date') if variant == 'ignore_canada_footnote' else choose(
            cmp('eq', f('market_code'), lit('2','integer')), lit('2024-05-27','date'), lit('2024-05-28','date'))
        before = choose(cmp('eq', f('market_code'), lit('2','integer')),
            f('pre_transition_canada_days'), lit('2','integer'))
        body = choose(cmp('ge', f('trade_date'), cutoff), lit('1','integer'), before); typ = 'integer'
    elif ref == '24EC50':
        scope = f('ipd_submission')
        cutoff = '2024-10-30' if variant == 'old_october_cutover' else '2024-11-30'
        body = choose(cmp('gt' if variant == 'exclude_first_day' else 'ge', f('submission_date'), lit(cutoff,'date')), f('via_eip'), lit(True))
    elif ref == '24EC57':
        actor = f('type9_direct') if variant == 'exclude_incidental' else n.any(f('type9_direct'), f('type9_incidental'))
        scope = n.all(actor, f('has_discretion'), f('uses_esg_product'))
        parts = [f('diligence_done'), f('ongoing_assessment'), f('demonstrable'),
            choose(f('uses_group'), n.all(f('group_comparable'), f('local_responsibility')), lit(True))]
        if variant == 'require_vcoc': parts.append(f('vcoc_member'))
        body = n.all(*parts)
    elif ref == '26EC23':
        scope = n.all(f('connecting_broker'), f('tokenised_secondary'))
        alert = choose(cmp('ge' if variant == 'inclusive_alert_threshold' else 'gt', f('deviation_bps'), f('threshold_bps')), f('alert_displayed'), lit(True))
        body = alert if variant == 'omit_primary_alternative' else n.all(f('primary_reminder'), alert)
    else:
        raise ValueError(ref)
    bid = 'candidate.' + ref.lower() + '.' + (variant or 'proposed')
    statement = case['proposition'] if variant is None else next(a['proposition'] for a in case['alternatives'] if a['id'] == variant)
    spans = [u['span'] for u in selected]
    result = dict(spec_version='0.1', bundle_id=bid, valid_from=START, valid_until=END,
        source_spans=spans, interpretations=[dict(id='meaning.slice', statement=statement,
            basis='reviewer_interpretation', source_span_ids=[s['id'] for s in spans], issue_ids=['pending.meaning'])],
        facts=[dict(name=name, type=x['type'], description=x['meaning']) for name,x in case['facts'].items()],
        rules=[dict(id='selected.control', type=typ, scope=scope, body=body,
            interpretation_id='meaning.slice', source_span_ids=[s['id'] for s in spans])])
    assert not validate_bundle(result), validate_bundle(result)
    return result


def requests_for(case, bundle):
    requests = []
    for scenario in case['scenarios']:
        values = {k: v['default'] for k,v in case['facts'].items()} | scenario['overrides']
        assert set(values) == set(case['facts'])
        facts = {}
        for name, value in values.items():
            typ = case['facts'][name]['type']
            if value == 'UNKNOWN': entry = dict(type=typ, status='unknown', reason='MISSING')
            elif value == 'CONFLICT': entry = dict(type=typ, status='conflict', evidence_ids=['fixture.a', 'fixture.b'])
            else:
                actual = case['facts'][name]['default'] if value in ('STALE','FUTURE') else value
                entry = dict(type=typ, status='known', value=actual, evidence_ids=['fixture.'+name],
                    valid_from=START, valid_until=AT if value == 'STALE' else END,
                    recorded_at='2026-09-23T00:00:01.000000Z' if value == 'FUTURE' else START)
            facts[name] = entry
        requests.append(dict(id=case['ref_no'].lower()+'.'+scenario['id'], bundle=bundle,
            snapshot=dict(subject_id='synthetic.'+case['ref_no'].lower(), facts=facts),
            rule_id='selected.control', valid_at=AT, known_at=AT, mode='draft', expected=scenario['expected']))
    return requests


def matches_expected(result, expected):
    return all(result.get(k) == v for k,v in expected.items())


def assert_parity(request, python, java):
    for result in (python, java):
        assert verify_result(request['bundle'], request['snapshot'], request['rule_id'], result)
    excluded = {'result_hash','engine_version'}
    assert {k:v for k,v in python.items() if k not in excluded} == {k:v for k,v in java.items() if k not in excluded}
    assert python['engine_version'] != java['engine_version']


def must_block(operation, expected='E_RELEASE_BLOCKED'):
    try: operation()
    except LegalMathError as exc:
        assert exc.code == expected, (exc.code, expected)
        return exc.code
    raise AssertionError('Expected rejection did not occur')


def execute_case(root, out, db, svc, sources, case, jdk):
    ref = case['ref_no']; caseout = out / ref
    packet, selected, critical = packet_for(case, sources)
    bundle = bundle_for(case, selected)
    requests = requests_for(case, bundle)
    # Fail cheaply before invoking Java, with an oracle that never calls the builder.
    for request in requests:
        result = evaluate_case(request)
        assert matches_expected(result, request['expected']), (request['id'], request['expected'], result)
    with db.connect() as con:
        for unit in packet['units']: assert resolve_span(db,con,unit['span']) == unit['text']
    write(caseout/'packet.json', packet)
    write(caseout/'bundle.json', bundle)
    write(caseout/'scenarios.json', [{**s, 'request_id':r['id']} for s,r in zip(case['scenarios'],requests)])
    write(caseout/'requests.json', requests)
    state = svc.lc.create('author', ref+'.bundle', bundle)
    built = Releases(db).build('engineer',ref+'.build',state['bundle_hash'],caseout/'java',jdk,requests)
    verified = json.loads((caseout/'java/verification-results.json').read_bytes())
    for request, result in zip(requests, verified):
        assert matches_expected(result['python'], request['expected'])
        assert matches_expected(result['java'], request['expected'])
    variants = []
    for challenge in case['alternatives']:
        mutant = bundle_for(case, selected, challenge['id'])
        mstate = svc.lc.create('author',ref+'.'+challenge['id'],mutant)
        mrequests = requests_for(case,mutant)
        path = caseout/'mutants'/challenge['id']
        build = build_candidate(mutant,path,jdk)
        java = run_java(build['jar'],mrequests,jdk,build['class_name'])
        python = [evaluate_case(r) for r in mrequests]
        for request,p,j in zip(mrequests,python,java): assert_parity(request,p,j)
        pd = [r['id'] for r,p in zip(mrequests,python) if not matches_expected(p,r['expected'])]
        jd = [r['id'] for r,j in zip(mrequests,java) if not matches_expected(j,r['expected'])]
        assert pd and pd == jd, ('Undetected or inconsistent mutation',ref,challenge['id'])
        write(path/'bundle.json',mutant)
        write(path/'results.json',[dict(id=r['id'],expected=r['expected'],python=p,java=j) for r,p,j in zip(mrequests,python,java)])
        variants.append(dict(**challenge,bundle_hash=mstate['bundle_hash'],jar_sha256=build['manifest']['jar_sha256'],detected_by=pd))

    run = svc.create('author',ref+'.investigation',packet)
    all_ids = [u['unit_id'] for u in packet['units']]
    partial_ids = [uid for uid in all_ids if uid != critical]
    def proposal(statement, bh, family, units, reason):
        return dict(source_packet_hash=run['source_packet_hash'],source_unit_ids=units,family_ids=[family],
            subject_unit=case['topic'],controlled_language=statement,bundle_hash=bh,
            assumptions=[dict(assumption_id='pending.interpretation',statement=case['unresolved'][0],
                provenance_refs=[],status='PROVISIONAL')],arguments=[],parent_id=None,revision_reason=reason)
    first = proposal(case['proposition'],state['bundle_hash'],'proposed-slice',partial_ids,'Unreviewed scoped source-written candidate; other inventoried provisions are deferred.')
    members = {'inventory':dict(adapter='scripted',proposals=[]),'normative':dict(adapter='scripted',proposals=[first])}
    for role, variant in zip(('controlled-language','alternatives'),variants):
        members[role]=dict(adapter='scripted',proposals=[proposal(variant['proposition'],variant['bundle_hash'],variant['id'],partial_ids,'Deliberately wrong challenge reading, not a defensible approved alternative.')])
    repairs = [dict(adapter='scripted',proposals=[proposal(case['proposition'],state['bundle_hash'],'proposed-slice',all_ids,
        f'Repair {i+1}: retain the omitted source unit; all unencoded provisions still require review and no new legal authority is supplied.')]) for i in range(3)]
    config = Controller(svc).configure('author',ref+'.config',run['run_id'],members,repairs,[built['verification_report_hash']])
    write(caseout/'configuration.json',config)
    report = Controller(svc).drive(run['run_id'])
    reports = Reports(svc)
    report_hash = reports.verify('meaning',run['run_id'])
    snapshot = svc.read('meaning',run['run_id']); records=snapshot['records']
    assert report['run_status']=='BLOCKED_UNRESOLVED' and report['processing_stop']=='ROUND_LIMIT',report
    assert report['rounds_issued']==3 and report['actions_issued']==7
    assert report['release_eligible'] is False and report['probability_of_legal_correctness'] is None
    assert report['missing_initial_roles']==[] and report['unexplored_family_ids']==[]
    assert report['missing_dependency_ids']==sorted(d['dependency_id'] for d in packet['dependencies'] if d['source_hash'] is None)
    assert 'source-coverage' in report['incomplete_mandatory_checks']  # inventory has no legal review
    assert 'java-check' not in report['incomplete_mandatory_checks']
    assert 'reference-check' not in report['incomplete_mandatory_checks']
    initial = [c for c in records['candidate'] if c['generation_phase']=='BLIND_INITIAL']
    assert len(initial)==3 and len(records['candidate'])==6
    for saved,p in zip(initial,[members[r]['proposals'][0] for r in ('normative','controlled-language','alternatives')]):
        assert all(saved[k]==v for k,v in p.items()), 'Initial candidate was overwritten'
    omissions = [i for i in records['issue'] if i['kind']=='SOURCE_COVERAGE']
    assert len(omissions)==1 and omissions[0]['source_unit_ids']==[critical]
    assert omissions[0]['resolution_state']=='RESOLVED_EVIDENCE'
    structural = [e for e in records['evidence'] if e['kind']=='VALIDATED_REPAIR']
    assert len(structural)==1 and structural[0]['legal_source_commitment_resolved'] is False
    assert not [i for i in records['issue'] if i['kind']=='MEMBER_FAILURE']
    assert all(c['probability_of_legal_correctness'] is None for c in records['candidate'])
    assert records['coverage'][0]['inventory_review_status']=='UNREVIEWED'
    candidate=initial[0]
    approval = must_block(lambda: MeaningReview(svc).decide('meaning',ref+'.unsafe-accept',run['run_id'],
        candidate['candidate_id'],digest(candidate),report_hash,run['source_packet_hash'],'ACCEPT_MEANING',
        'Adversarial test attempts acceptance despite unresolved questions','Engineering tests do not settle meaning',all_ids))
    with db.connect() as con:
        blocked = must_block(lambda: guard(db,con,state['bundle_hash']))
        assert not con.execute('SELECT 1 FROM releases').fetchone()
        assert not con.execute("SELECT 1 FROM interpretation_records WHERE kind='review-decision'").fetchone()
    # Reopening must reproduce report identity without the running controller.
    assert Reports(Interpretations(Database(db.root))).verify('meaning',run['run_id'])==report_hash
    write(caseout/'investigation.json',snapshot)
    write(caseout/'report.json',report)
    write(caseout/'scope-disposition.json',dict(selected_unit_ids=[u['unit_id'] for u in selected],
        retained_for_manual_review=[u['unit_id'] for u in packet['units'] if u not in selected],
        limitation='Citations to all units after repair are not implementation of all clauses.',unresolved=case['unresolved']))
    return dict(ref_no=ref,topic=case['topic'],source_url=sources[ref]['official_url'],scenario_count=len(requests),
        named_cases_passed=len(verified),inventory_units=len(packet['units']),selected_units=len(selected),
        compiled_mutants=variants,full_python_java_parity=True,report_status=report['run_status'],
        report_hash=report_hash,run_id=run['run_id'],bundle_hash=state['bundle_hash'],jar_sha256=built['jar_sha256'],
        actions=report['actions_issued'],rounds=report['rounds_issued'],processing_stop=report['processing_stop'],
        missing_dependencies=report['missing_dependency_ids'],unresolved_issue_count=len(report['material_unresolved_issue_ids']),
        structural_omission_repaired=True,inventory_review='UNREVIEWED',meaning_acceptance_rejected=approval,
        release_guard_rejected=blocked,released=False)


def announcement_control(db,svc,sources,out):
    """Source-written non-rule disposition. This is not automatic NLP detection."""
    source=sources['25EC48'];units=inventory(source,normative=False)
    assert '76%' in source['text'] and 'will commence a new round' in source['text']
    packet=dict(source_key='corpus.25ec48',authority='RETAINED_SOURCE',selected_slice='Announcement only; no new executable transaction threshold derived.',units=units,
        dependencies=[dict(dependency_id='underlying-code-of-conduct',source_hash=None)],family_ids=['announcement','invented-threshold'])
    run=svc.create('author','announcement.create',packet)
    proposition=dict(source_packet_hash=run['source_packet_hash'],source_unit_ids=[u['unit_id'] for u in units],family_ids=['announcement'],
        subject_unit='Review announcement',controlled_language='The 76% statistic describes prior CIS sales growth. No numeric transaction limit is specified by this announcement.',
        bundle_hash=None,assumptions=[],arguments=[],parent_id=None,revision_reason='Source-written negative control; existing suitability duties are not removed.')
    members={r:dict(adapter='scripted',proposals=[] if r=='inventory' else [deepcopy(proposition)]) for r in ('inventory','normative','controlled-language','alternatives')}
    members['alternatives']['adapter']='malformed'
    Controller(svc).configure('author','announcement.config',run['run_id'],members)
    report=Controller(svc).drive(run['run_id']);snapshot=svc.read('meaning',run['run_id'])
    assert report['run_status']=='BLOCKED_UNRESOLVED' and report['missing_initial_roles']==['alternatives']
    assert all(c['bundle_hash'] is None for c in snapshot['records']['candidate'])
    assert any(i['kind']=='MEMBER_FAILURE' for i in snapshot['records']['issue'])
    Reports(svc).verify('meaning',run['run_id'])
    write(out/'announcement-25EC48.json',snapshot)
    return dict(ref_no='25EC48',no_executable_bundle=True,member_failure_retained=True,
        source_classification='MANUALLY_AUTHORED_ANNOUNCEMENT_DISPOSITION',automatic_semantic_detection=False)


def run_suite(root, output_dir, *, jdk=None):
    root=Path(root).resolve();out=Path(output_dir).resolve()
    jdk=Path(jdk) if jdk else root/'.localresources/java-toolchain/jdk-17.0.20.1+1'
    corpus,freeze=load_fixture(root)
    db=Database(out/'work/db');Lifecycle(db).register(IDENTITIES)
    sources=load_sources(db,root,freeze);svc=Interpretations(db)
    runs=[]
    for case in corpus['cases']:
        runs.append(execute_case(root,out,db,svc,sources,case,jdk))
        write(out/'progress.json',dict(completed=[r['ref_no'] for r in runs]))
    negative=announcement_control(db,svc,sources,out)
    assert db.verify()
    return dict(schema_version='multi-circular-integration.v2',selected_refs=list(REFS),runs=runs,
        engineering_verdict='PASS',legal_meaning_verdict='NOT_ESTABLISHED',automatic_translation_tested=False,
        independent_legal_adjudication='PENDING',announcement_negative_control=negative,
        total_scenarios=sum(r['scenario_count'] for r in runs),compiled_mutants_detected=sum(len(r['compiled_mutants']) for r in runs),
        released=False,limitations=['Same author supplied scoped interpretations and literal scenario oracles.',
        'Full retained-text inventory does not prove HTML/PDF extraction completeness or full legal implementation.',
        'Scripted proposals/repairs exercise engineering controls, not live multi-model interpretation accuracy.',
        'Supplied legal/fact classifications, source versions, calendar conventions and threshold policy need independent review.'])
