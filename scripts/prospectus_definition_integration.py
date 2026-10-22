"""Bounded definition integration; frozen expectations precede implementation."""
from copy import deepcopy
from datetime import datetime, timezone
from functools import lru_cache
import gzip
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'src'), str(ROOT)]
sys.dont_write_bytecode = True
os.environ.update(PYTHONDONTWRITEBYTECODE='1', CUDA_VISIBLE_DEVICES='-1')
os.environ['PYTHONPATH'] = os.pathsep.join((str(ROOT / 'src'), str(ROOT)))
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
PREP = AUTH / 'reviews/definition-integration-287'
HERE = AUTH / 'attempts/basf-references/attempt-028'
SOURCE = AUTH / 'attempts/basf-references/attempt-026'
LEXICAL = AUTH / 'attempts/basf-references/attempt-027'
PRIOR = AUTH / 'attempts/basf-references/attempt-025'
METHOD = 'scripts/prospectus_definition_integration.py'
ORACLE = 'scripts/prospectus_definition_integration_oracle.py'
PLAN = 'docs/plans/prospectus-definition-integration-2026-10-18.md'
DEST = 'src/legalmath/prospectus/successor/'
PROFILE = 'basf-selected-definition-readings.v1'


def read(path):
    data = Path(path).read_bytes()
    return json.loads(gzip.decompress(data) if Path(path).suffix == '.gz' else data)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rel(path):
    return str(Path(path).relative_to(ROOT))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode()
    with path.open('xb') as out:
        out.write(gzip.compress(data, mtime=0) if path.suffix == '.gz' else data)


@lru_cache(maxsize=1)
def baseline():
    from scripts.prospectus_definition_scope_investigation import products
    from scripts.prospectus_internal_consumer_continuation import retained
    from scripts.prospectus_typed_delta import apply
    p = products()
    _, answer021 = retained('candidate-answer')
    row = read(PRIOR / 'candidate-retained-answer.json.gz')
    answer = apply(answer021, row['answer_delta'])
    from legalmath.prospectus.successor.contracts import digest
    assert digest(answer) == row['answer_sha256']
    return p, answer


def source_check():
    for folder in (PRIOR, SOURCE, LEXICAL):
        for name, expected in read(folder / 'outputs.json').items():
            assert sha(folder / name) == expected, 'Sealed source changed: ' + str(folder / name)


def costs(extra=0):
    start = read(PREP / 'accounting-start.json')
    seconds = start['prior_resources']['cumulative026_027_measured_seconds'] + extra
    receipts = [p for d in (PREP, HERE) for pattern in ('stages/*/result.json', 'stages/*/failure.json')
                for p in d.glob(pattern)]
    seconds += sum(read(p)['wall_seconds'] for p in receipts)
    paths = {p for d in (PREP, HERE) for p in d.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT / p for p in (METHOD, ORACLE, PLAN))
    paths.update(p for p in (AUTH / 'history').glob('*.json') if p.name not in start['history_names'])
    paths.add(AUTH / 'revisions/0287.json')
    paths.update(ROOT / p for p in start['production_bytes'])
    additional = 0
    for path in paths:
        if path.exists():
            previous = start['production_bytes'].get(rel(path), 0)
            additional += max(0, path.stat().st_size - previous)
    additional += max(0, (AUTH / 'program.json').stat().st_size - start['program_bytes'])
    size = start['prior_resources']['cumulative026_027_bytes'] + additional
    assert seconds < 1800 and size < 124 * 1024**2, 'Cumulative026–028 reviewed resources exhausted'
    return {'cumulative026_028_measured_seconds': seconds, 'cumulative026_028_bytes': size,
            'seconds_bound': 1800, 'bytes_bound_including_4MiB_reserve': 128 * 1024**2,
            'prior_snapshot_sha256': sha(PREP / 'accounting-start.json'),
            'prior_costs_reset': False, 'new_measured_seconds_allowance': 0,
            'historical_manual_reading_controller_seconds': 'UNKNOWN'}


def prepare():
    """Independent source projection and arithmetic gold; no candidate exists."""
    assert not (PREP / 'candidate').exists()
    assert not (ROOT / (DEST + 'definition_scopes.py')).exists()
    source_check()
    from legalmath.prospectus.successor.contracts import digest
    source = read(SOURCE / 'selected-source.json.gz')
    inventory = read(SOURCE / 'bound-inventory.json.gz')
    lexical = read(LEXICAL / 'actual-selected-source.json.gz')
    text, intervals, interval_index = source['candidate_text'], [], {}

    def interval(value):
        a, b = value['start'], value['end']
        assert text[a:b] == value['quote'] and 0 <= a < b <= len(text)
        key = (a, b)
        if key not in interval_index:
            interval_index[key] = len(intervals)
            indices = [i for i, p in enumerate(source['pieces']) if p['start'] < b and a < p['end']]
            intervals.append({'start': a, 'end': b, 'quote': value['quote'], 'source_piece_indices': indices})
        return interval_index[key]

    records = []
    for original in inventory['records']:
        record = {k: deepcopy(original[k]) for k in ('id', 'kind', 'forms', 'reading', 'declaring_section')}
        record['declarations'] = [interval(v) for v in original['declarations']]
        record['scope_alternatives'] = [{**{k: deepcopy(v[k]) for k in ('scope', 'reason')},
            'extent': [interval(x) for x in v['extent']],
            'source_reasons': [interval(x) for x in v['source_reasons']]} for v in original['scope_alternatives']]
        record['uses'] = [{**{k: deepcopy(v[k]) for k in ('classification', 'declaration_candidates', 'scope_reading')},
                           'interval': interval(v)} for v in original['uses']]
        records.append(record)
    bindings = {k: source[k] for k in ('source_graph_sha256', 'assembly_sha256', 'selected_contract_sha256')}
    bindings['selected_text_sha256'] = hashlib.sha256(text.encode()).hexdigest()
    spec = {'profile': PROFILE, 'bindings': bindings, 'language': 'de',
            'records': records, 'intervals': intervals, 'source_pieces': source['pieces'],
            **{k: deepcopy(inventory[k]) for k in ('preamble_reading', 'section_readings', 'known_misses', 'remaining')},
            'source_inventory_sha256': sha(SOURCE / 'bound-inventory.json.gz'),
            'retained_lexical_sha256': sha(LEXICAL / 'actual-selected-source.json.gz')}
    expected_records = deepcopy(records)
    for record, original in zip(expected_records, inventory['records']):
        for use, old in zip(record['uses'], original['uses']):
            a, b = old['start'], old['end']
            candidates = []
            for number, scope in enumerate(original['scope_alternatives']):
                if any(x['start'] <= a and b <= x['end'] for x in scope['extent']):
                    candidates.append(number)
            exact, overlaps = [], []
            for i, row in enumerate(lexical['uses']):
                if (row['start'], row['end']) == (a, b):
                    exact.append(i)
                elif row['start'] < b and a < row['end']:
                    overlaps.append(i)
            use.update(interval_candidates=candidates, lexical_exact=exact, lexical_overlap_only=overlaps,
                       governing_scope=None, meaning=None)
        record.update(status='UNRESOLVED', scope_admitted=False, meaning_admitted=False)
    report = {'version': 'definition-source-review.v1', 'profile': PROFILE, 'profile_sha256': digest(spec),
              **{k: deepcopy(spec[k]) for k in ('bindings','intervals','source_pieces','preamble_reading',
                                               'section_readings','known_misses','remaining')},
              'records': expected_records, 'lexical': lexical,
              'membership_meaning': 'Arithmetic containment in retained alternative intervals only',
              'scope_admitted': False, 'meaning_admitted': False, 'general_recall_established': False,
              'provenance_gaps_repaired': False}
    # Independently authored arithmetic examples, including union gaps and boundaries.
    cases = [
        {'label':'contained', 'use':[2,4], 'alternatives':[[[0,5]]], 'expected':[0]},
        {'label':'crosses-end', 'use':[4,6], 'alternatives':[[[0,5]]], 'expected':[]},
        {'label':'touches-only', 'use':[5,6], 'alternatives':[[[0,5]]], 'expected':[]},
        {'label':'disjoint-gap', 'use':[4,7], 'alternatives':[[[0,5],[6,9]]], 'expected':[]},
        {'label':'overlapping-alternatives', 'use':[3,4], 'alternatives':[[[0,5]],[[2,8]]], 'expected':[0,1]},
        {'label':'forward-use', 'use':[1,2], 'alternatives':[[[0,10]],[[5,10]]], 'expected':[0]},
        {'label':'empty-candidates', 'use':[1,2], 'alternatives':[], 'expected':[]},
        {'label':'exact-boundaries', 'use':[0,5], 'alternatives':[[[0,5]]], 'expected':[0]},
    ]
    save(PREP / 'expected-spec.json.gz', spec)
    save(PREP / 'expected-report.json.gz', report)
    save(PREP / 'membership-cases.json', cases)
    p, answer = baseline()
    assert digest(p['P1']['payload']['graph']) == bindings['source_graph_sha256']
    assert digest(p['P2']['payload']['assembly']) == bindings['assembly_sha256']
    assert digest(p['P2']['payload']['selected_contract']) == bindings['selected_contract_sha256']
    assert p['P2']['payload']['assembly']['continuous_text'] == text
    save(PREP / 'expected-freeze.json', {'candidate_existed': False, 'production_admit_used': False,
        'bindings': {rel(PREP / n): sha(PREP / n) for n in
                     ('expected-spec.json.gz','expected-report.json.gz','membership-cases.json')},
        'baseline_products_sha256': digest(p), 'baseline_answer_sha256': digest(answer),
        'source_inventory_sha256': spec['source_inventory_sha256'],
        'lexical_original_sha256': spec['retained_lexical_sha256']})
    return {'status':'PASS', 'records':len(records), 'authored_use_associations':sum(len(r['uses']) for r in records),
            'unique_intervals':len(intervals), 'candidate_existed':False, 'ordinary_answers_run':0}


def stage_candidate():
    from legalmath.prospectus.successor.contracts import digest
    assert read(PREP / 'stages/prepare/result.json')['status'] == 'PASS'
    for name, checksum in read(PREP / 'expected-freeze.json')['bindings'].items():
        assert sha(ROOT / name) == checksum
    candidate = PREP / 'candidate'
    text = (candidate / 'definition_scopes.py').read_text()
    assert text.count('REPLACE_WITH_FROZEN_SPEC_DIGEST') == 1
    (candidate / 'definition_scopes.py').write_text(text.replace('REPLACE_WITH_FROZEN_SPEC_DIGEST',
                                                               digest(read(PREP / 'expected-spec.json.gz'))))
    with (candidate / 'definition_scopes_spec.json.gz').open('xb') as out:
        out.write((PREP / 'expected-spec.json.gz').read_bytes())
    with (candidate / 'definition_discovery.py').open('xb') as out:
        out.write((AUTH / 'reviews/definition-discovery-286/candidate.py').read_bytes())
    replacements = {
        'contracts.py': [('"archive_observations", "statutory_references"}',
                          '"archive_observations", "statutory_references", "definition_sources"}')],
        'service.py': [
            ('def dependencies(request, graph, assembly):',
             'def dependencies(request, graph, assembly, selected_contract=None):'),
            ('    result.extend(statutory_references.dependencies(statutory))',
             '    result.extend(statutory_references.dependencies(statutory))\n'
             '    from . import definition_scopes\n'
             '    definition_report = definition_scopes.admit(graph, {"assembly": assembly, "selected_contract": selected_contract}, request)\n'
             '    result.extend(definition_scopes.dependencies(definition_report))'),
            ("expected = dependencies(request, graph, selected['assembly'])",
             "expected = dependencies(request, graph, selected['assembly'], selected['selected_contract'])"),
            ('"incorporation_admission", "statutory_references"})',
             '"incorporation_admission", "statutory_references", "definition_sources"})'),
            ('    assembly = selected["assembly"]\n    from . import statutory_references',
             '    assembly = selected["assembly"]\n    from . import definition_scopes\n'
             '    definition_report = definition_scopes.admit(graph, selected, request)\n    from . import statutory_references'),
            ('    deps = dependencies(request, graph, assembly)',
             '    deps = dependencies(request, graph, assembly, selected["selected_contract"])'),
            ('    if statutory is not None:\n        result["statutory_references"] = statutory',
             '    if definition_report is not None:\n        result["definition_sources"] = definition_report\n'
             '    if statutory is not None:\n        result["statutory_references"] = statutory'),
        ]}
    replacements['service.py'].extend([
        ("    interpretation_input = {**request, **(semantic.get('interpretation_input') or {})}",
         "    interpretation_input = {**request, **(semantic.get('interpretation_input') or {})}\n"
         '    from . import definition_scopes\n'
         '    definition_report = definition_scopes.verify_consumed(graph, selected, interpretation_input, semantic)'),
        ('"mode": "ASSISTED" if statutory is not None or supplied_legal_model',
         '"mode": "ASSISTED" if definition_report is not None or statutory is not None or supplied_legal_model'),
    ])
    for name, edits in replacements.items():
        before = (ROOT / (DEST + name)).read_bytes()
        path = PREP / 'baseline' / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as out:
            out.write(before)
        text = before.decode()
        for old, new in edits:
            expected_count = 2 if old.startswith('    if statutory is not None:') else 1
            assert text.count(old) == expected_count, (name, old, text.count(old))
            text = text.replace(old, new)
        with (candidate / name).open('x') as out:
            out.write(text)
    files = []
    for name in ('service.py','contracts.py','definition_scopes.py','definition_scopes_spec.json.gz','definition_discovery.py'):
        target = ROOT / (DEST + name)
        files.append({'target':DEST+name, 'before_sha256':sha(target) if target.exists() else None,
            'baseline':rel(PREP/'baseline'/name) if target.exists() else None,
            'candidate':rel(candidate/name), 'after_sha256':sha(candidate/name)})
        if name.endswith('.py'):
            compile((candidate/name).read_text(), name, 'exec')
    save(PREP/'installation.json', {'version':'exact-installation.v1','files':files,
        'input_replacements':{r['target']:[r['baseline'],r['candidate']] for r in files if r['baseline']},
        'controller_unchanged':True,'historical_freezes_unchanged':True})
    return {'status':'PASS','compiled_candidate':True,'production_installed':False,'ordinary_answers_run':0,
            'lexical_method_unchanged':sha(candidate/'definition_discovery.py') == sha(AUTH/'reviews/definition-discovery-286/candidate.py')}


def preflight():
    from scripts.prospectus_definition_integration_oracle import preflight as audit
    return audit()


def propose():
    from legalmath.prospectus.execution_authority import Authority, CODE, digest
    program = read(AUTH/'program.json')
    assert program['revision'] == 286
    assert read(PREP/'stages/resource-audit/result.json')['status'] == 'PASS'
    assert (PREP/'PRE-ADMISSION-REVIEW.md').exists()
    events = Authority(ROOT).events()
    attempts = [e['attempt'] for e in events if e['kind']=='ADMIT' and e.get('budget_key')=='basf-references']
    assert len(attempts) == 27
    assert next(e for e in reversed(events) if e.get('attempt')==rel(LEXICAL))['kind']=='RECORD'
    bindings = {rel(p):sha(p) for p in PREP.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    bindings.update({name:sha(ROOT/name) for name in (*CODE,PLAN,METHOD,ORACLE)})
    bindings.update({rel(folder/'outputs.json'):sha(folder/'outputs.json') for folder in (PRIOR,SOURCE,LEXICAL)})
    save(PREP/'freeze.json', {'bindings':bindings})
    proposal = deepcopy(program)
    proposal['revision'] = 287
    task = next(t for t in proposal['tasks'] if t['id']=='basf-references')
    replacements = read(PREP/'installation.json')['input_replacements']
    task['inputs'] = [name for name in task['inputs'] if name not in replacements]
    task['inputs'] = list(dict.fromkeys(task['inputs']+list(bindings)+[rel(PREP/'freeze.json')]))
    task.update(dossier=PLAN, pre_admission_review=rel(PREP/'PRE-ADMISSION-REVIEW.md'),
        reason='Integrate unchanged finite lexical proposals and all retained scope readings into ordinary answers; preserve unresolved governing meaning',
        definition_source_integration={'review':rel(PREP),'installation':rel(PREP/'installation.json'),
            'source':rel(SOURCE),'lexical':rel(LEXICAL),'original_task_complete':False,
            'cumulative026_028_bounds':{'seconds':1800,'bytes_including_4MiB_reserve':128*1024**2},
            'prior_snapshot':rel(PREP/'accounting-start.json'),'no_external_adviser_prerequisite':True})
    proposal['budgets']['basf-references']['maximum_new_attempts'] = 28
    routes = read(ROOT/program['continuation_review']['routes'])
    routes['baseline_revision'] = 287
    for row in routes['tasks']:
        if row['task']=='basf-references':
            row.update(dossier=PLAN,task_sha256=digest(task),
                next_action='Execute exact installation, independent complete ordinary answers and real resealed refusals; then source-reasoned scope repairs',
                stop_condition='28 cumulative admissions;180s stages;cumulative026–028 1800s/128MiB with4MiB reserve;no unchanged retries')
    save(PREP/'routes.json',routes)
    proposal['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    proposal['continuation_review']['bindings'].update({PLAN:sha(ROOT/PLAN),
        rel(PREP/'routes.json'):sha(PREP/'routes.json'),rel(PREP/'freeze.json'):sha(PREP/'freeze.json')})
    review = {'baseline':digest(program),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Frozen026/027 expected projection precedes candidate implementation',
                   'Optional exact-source report participates in P3 dependencies and ordinary consumption',
                   'Retain all original obligations, evidence, costs and unresolved scope/meaning',
                   'Explicit cumulative storage extension64MiB to128MiB; no added measured time'],
        'skeptical_audit':{'verdict':'PASS','review':rel(PREP/'PRE-ADMISSION-REVIEW.md')},
        'evidence_contract':{'primary':'Complete products and ordinary answers against pre-candidate026/027 projection and complete025 baseline',
            'promotion_veto':['Lost source record','Invented governing meaning','Absent-profile regression',
                              'Unexplained complete-answer difference','Accepted resealed forgery'],
            'continuation_veto':['Corrupt frozen evidence','Method drift','Missing required artifact','Cumulative resource exhaustion'],
            'explanatory_only':['Counts','Hashes','Runtime','Focused tests'],
            'not_concluded':['General recall','Independently correct legal readings','Native model execution','Whole-build completion']},
        'budget_revision':{'budget_key':'basf-references','previous_maximum':27,'new_maximum':28,
            'retained_attempts':attempts,'reason':'Sealed027 finite mechanism now has a distinct downstream integration question',
            'next_discriminating_check':'Independent complete ordinary answers plus actual consumer refusals of validly resealed changes',
            'stop_condition':'180s stages;retain cumulative1800s;128MiB including4MiB reserve;no unchanged retries',
            'same_scope_authorization':'User requested refreshed master and continued general build with internal supported-behavior proofs'},
        'storage_revision':{'previous_bytes':64*1024**2,'new_bytes':128*1024**2,'reserve_bytes':4*1024**2,
                            'new_measured_seconds':0,'prior_costs_retained':True},
        'resources_before_admission':costs(),'original_obligations_preserved':True}
    save(PREP/'proposal.json',proposal)
    save(PREP/'review.json',review)
    return {'status':'PASS','revision':287,'resources':costs()}


def frozen(installed=True):
    from legalmath.prospectus.execution_authority import Authority, digest
    admission = read(HERE/'admission.json')
    assert digest(read(AUTH/'program.json')) == admission['program_sha256']
    assert Authority(ROOT).binding(admission['task_spec']) == admission['binding']
    for name, checksum in read(PREP/'freeze.json')['bindings'].items():
        assert sha(ROOT/name) == checksum, name
    for row in read(PREP/'installation.json')['files']:
        path = ROOT/row['target']
        assert (sha(path) if path.exists() else None) == row['after_sha256' if installed else 'before_sha256']


def install():
    frozen(installed=False)
    for row in read(PREP/'installation.json')['files']:
        path = ROOT/row['target']
        temp = path.with_name(path.name+'.definition-install')
        with temp.open('xb') as out:
            out.write((ROOT/row['candidate']).read_bytes())
        temp.replace(path)
    frozen()
    return {'status':'PASS','exact_reviewed_files_installed':5,'controller_unchanged':True}


def retain(label, products, answer=None, *, base_label=None, base_products=None):
    from scripts.prospectus_typed_delta import changes, apply, equal
    from legalmath.prospectus.successor.contracts import digest
    if base_label is None:
        assert base_products is None
        old, old_answer = baseline()
        reference = None
    else:
        assert base_label == 'assisted-products' and answer is None
        assert label.startswith(('control-', 'upstream-'))
        path = HERE/(base_label+'.json.gz')
        base = read(path)
        assert 'base' not in base, 'Retention base must be directly reconstructable from025'
        assert digest(base_products) == base['products_sha256'], 'Retention base identity changed'
        old = base_products
        reference = {'label':base_label, 'file_sha256':sha(path),
                     'products_sha256':base['products_sha256']}
    delta = changes(old,products)
    equal(apply(old,delta),products,'Lossy integration product retention')
    row = {'products_delta':delta,'products_sha256':digest(products)}
    if reference is not None:
        row['base'] = reference
    if answer is not None:
        delta = changes(old_answer,answer)
        equal(apply(old_answer,delta),answer,'Lossy integration answer retention')
        row.update(answer_delta=delta,answer_sha256=digest(answer))
    save(HERE/(label+'.json.gz'),row)


def retained(label):
    from scripts.prospectus_typed_delta import apply
    from legalmath.prospectus.successor.contracts import digest
    row = read(HERE/(label+'.json.gz'))
    if 'base' in row:
        reference = row['base']
        assert reference['label'] == 'assisted-products' and label != 'assisted-products'
        assert 'answer_delta' not in row
        assert sha(HERE/'assisted-products.json.gz') == reference['file_sha256']
        old, old_answer = retained('assisted-products')
        assert digest(old) == reference['products_sha256']
    else:
        old, old_answer = baseline()
    p = apply(old,row['products_delta'])
    assert digest(p)==row['products_sha256']
    answer = apply(old_answer,row['answer_delta']) if 'answer_delta' in row else None
    assert answer is None or digest(answer)==row['answer_sha256']
    return p, answer


def build(label):
    from legalmath.prospectus.successor import service, definition_scopes
    from legalmath.prospectus.successor.contracts import digest
    old, _ = baseline()
    p = dict(old)
    value = deepcopy(old['P3']['payload']['interpretation_input'])
    if label=='assisted':
        value['definition_sources'] = definition_scopes.packet()
    elif label=='request-route':
        request = deepcopy(p['P1']['payload']['request'])
        request['definition_sources'] = definition_scopes.packet()
        service.validate_request(request)
        p['P1'] = service.seal('P1',request['bundle'],{'request':digest(request)},
                               {'request':request,'graph':p['P1']['payload']['graph']})
        p['P2'] = service.seal('P2',request['bundle'],{'P1':p['P1']['sha256']},old['P2']['payload'])
    else:
        assert label=='absent'
    p['P3'] = service.interpretation_product(p['P1'],p['P2'],value)
    retain(label+'-p3',p)
    return {'status':'PASS','label':label,'raw_actual_retained_before_comparison':True}


def downstream(label):
    from legalmath.prospectus.successor import service
    p, _ = retained(label+'-p3')
    old_law, old_finance = p['P4']['payload'],p['P5']['payload']
    p['P4'] = service.law_product(p['P1'],p['P3'],old_law['cases'],old_law['law_input'])
    p['P5'] = service.financial_product(p['P1'],p['P2'],p['P3'],old_finance['cases'],old_finance['scenario_input'])
    retain(label+'-products',p)
    return {'status':'PASS','label':label,'actual_downstream_products_retained':True}


def consume(label):
    from legalmath.prospectus.successor import service
    p, _ = retained(label+'-products')
    answer = service.consume(p,ROOT,mode='frozen')
    retain(label+'-answer',p,answer)
    return {'status':'PASS','label':label,'ordinary_answer_retained_before_comparison':True}


def main():
    assert len(sys.argv) == 2
    stage = sys.argv[1]
    from scripts import prospectus_definition_integration_oracle as oracle
    prerequisites = oracle.prerequisites(stage)
    for required in prerequisites:
        base = PREP if required in oracle.PREPARATION else HERE
        assert read(base/'stages'/required/'result.json')['status'] == 'PASS', required
    if stage == 'prepare' and not (PREP / 'accounting-start.json').exists():
        from scripts.prospectus_definition_discovery_trial import costs as old_costs
        prior = old_costs()
        old_dirs = [AUTH / p for p in ('reviews/definition-scope-285','reviews/definition-discovery-286',
                                       'attempts/basf-references/attempt-026','attempts/basf-references/attempt-027')]
        owned = {rel(p): p.stat().st_size for d in old_dirs for p in d.rglob('*')
                 if p.is_file() and '__pycache__' not in p.parts}
        save(PREP / 'accounting-start.json', {'prior_resources':prior, 'prior_owned_files':owned,
            'history_names':[p.name for p in (AUTH / 'history').glob('*.json')],
            'program_bytes':(AUTH / 'program.json').stat().st_size,
            'production_bytes':{DEST+n:(ROOT/(DEST+n)).stat().st_size if (ROOT/(DEST+n)).exists() else 0
                                for n in ('service.py','contracts.py','definition_scopes.py',
                                          'definition_scopes_spec.json.gz','definition_discovery.py')},
            'storage_revision':{'old_bytes':64*1024**2,'new_bytes':128*1024**2,
                                'reserve_bytes':4*1024**2,'new_measured_seconds':0}})
    preparation = stage in oracle.PREPARATION
    folder = (PREP if preparation else HERE) / 'stages' / stage
    assert not (folder / 'started.json').exists(), 'Unchanged stage retry refused'
    costs()
    save(folder / 'started.json', {'command':['.venv/bin/python','-m','scripts.prospectus_definition_integration',stage],
                                  'started_at':datetime.now(timezone.utc).isoformat(),'stage_seconds':180})
    started = time.monotonic()
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError('Definition integration stage bound')))
    signal.alarm(180)
    try:
        if not preparation:
            frozen(installed=stage!='install')
        if stage.startswith(('build-','downstream-','consume-','verify-')):
            operation, label = stage.split('-',1)
            result = oracle.verify_answer(label) if operation=='verify' else globals()[operation](label)
        elif stage.startswith('controls-'):
            result = oracle.controls(int(stage.removeprefix('controls-')))
        elif stage in ('tests','membership','upstream','reconcile','seal','resource-audit'):
            result = getattr(oracle,stage.replace('-','_'))()
        else:
            result = globals()[stage.replace('-','_')]()
        if not preparation:
            frozen()
        costs(time.monotonic()-started)
        result['wall_seconds'] = time.monotonic()-started
        save(folder / 'result.json', result)
        if stage=='seal':
            save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*')
                                     if p.is_file() and '__pycache__' not in p.parts})
            result['terminal_resources'] = costs()
        print(json.dumps(result,ensure_ascii=False))
    except BaseException as exc:
        save(folder / 'failure.json', {'type':type(exc).__name__,'message':str(exc),
                                     'wall_seconds':time.monotonic()-started})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
