"""Preserve the predecessor and execute a finite, source-bound repair program."""
import argparse
import fcntl
from pathlib import Path
import shutil
import subprocess
import time

from scripts.legal_gap_program import ROOT, OUT as PRIOR, DOC as PRIOR_DOC
from scripts.legal_gap_program import read, save, ref, check_ref, ledger, remaining, command

OUT = ROOT / 'artifacts/legal-integration-repair/2026-10-08'
DOC = ROOT / 'docs/implementation/legal-integration-repair'
PLAN = ROOT / 'docs/plans/legal-integration-repair-program.md'
ACTIONS = ('check', 'execute', 'status', 'verify')
PREFIX = ['.venv/bin/python', 'scripts/run_legal_integration_repair.py']


def budgets():
    calls = ledger()['calls']
    repairs = read(PRIOR / 'repairs.json')
    return {'used': len(calls), 'maximum': ledger()['maximum'],
            'remaining_seconds': int(remaining()),
            'arm_used': {a: sum(r['arm'] == 'product.' + a for r in calls)
                         for a in ('baseline', 'combined')},
            'arm_maximum': 24, 'repairs_used': len(repairs['repairs']),
            'repairs_maximum': repairs['maximum']}


def inventory():
    gap_path = PRIOR / 'G4/attempt-1/gap-tool-matrix.json'
    reading_path = PRIOR / 'G4/attempt-1/reading-coverage.json'
    gaps, readings = read(gap_path), read(reading_path)
    if len(gaps) != 46 or len(readings) != 35:
        raise ValueError('Original denominator changed')
    lines = ['# All retained legal-product gaps', '',
             '8 October 2026. All 46 original obligations remain open. The 35 original',
             'readings remain retained, including 32 unformalized readings. This is an',
             'identity-preserving inventory, not a newly selected benchmark.', '',
             'Source: `' + str(gap_path.relative_to(ROOT)) + '` and',
             '`' + str(reading_path.relative_to(ROOT)) + '`.', '',
             '## Original obligations', '']
    for r in gaps:
        lines += [f"### {r['ordinal']}. `{r['obligation_id']}`", '',
                  '**Open:** ' + r['first_unresolved_step'], '',
                  'Classes: ' + ', '.join(r['classes']) + '.', '',
                  'Missing premises (original wording):', '']
        for p in r['missing_premises']:
            lines += [f"- `{p['id']}`: {p['statement']} ({p['status']})."]
        lines += ['', 'Tool contribution and remaining evidence:', '']
        for t in r['planned_tool_roles']:
            lines += [f"- {t['tool']}: {t['role']}."]
        lines += ['', 'Closure still requires: ' + r['closure_requires'] + '.', '']
    lines += ['## Every retained reading', '']
    for r in readings:
        lines += [f"### `{r['reading_id']}`", '', r['retained_statement'], '',
                  f"Status: {r['status']}; source equivalence: {r['source_equivalence']}.", '',
                  'Source anchors: ' + ', '.join('`' + c['unit_id'] + '`' for c in r.get('citations', [])) + '.', '']
    lines += ['## Tool and evidence gaps beyond the obligation register', '',
              '- Case law: HK/UK citation recognition remains unsupported in tested eyecite controls; case analogy, consent and target transfer need explicit case records, distinctions and applicability review.',
              '- English interpretation: open texture, modal force, temporal scope, alternative readings and trigger/fulfillment require source-grounded judgments. Logical English parses a restricted controlled language.',
              '- LegalRuleML: selected Boolean/conditional structure only; no demonstrated general deontic, temporal or unformalized-reading conversion.',
              '- Factual premises: actual dated appointments, arrangements, ownership/operational records and assessments are absent; tools cannot invent them.',
              '- Evaluation: four development questions and controlled graphs are not independent labelled target data; no legal-quality ranking or calibration exists.',
              '- Live execution: 420 required pairs remain; neither original product arm completed. A two-pair diagnostic does not reduce that denominator.', '',
              'Tool dispositions retained from the reviewed benchmark:', '']
    for name, r in read(PRIOR_DOC / 'benchmark.json')['not_selected'].items():
        lines += [f"- **{name} — {r['status']}**: {r['reason']}."]
    lines += ['', 'Confirmed integration defects and their repair criteria are I1–I8 in',
              '`docs/plans/legal-integration-repair-program.md`. See `execution-result.md`',
              'for which engineering repairs passed and what remains untested.', '']
    DOC.mkdir(parents=True, exist_ok=True)
    (DOC / 'remaining-gaps.md').write_text('\n'.join(lines))
    return {'obligations': ref(gap_path), 'readings': ref(reading_path),
            'inventory': ref(DOC / 'remaining-gaps.md'),
            'counts': {'obligations': 46, 'readings': 35, 'unformalized': 32}}


def baseline():
    path = OUT / 'baseline.json'
    if path.exists():
        value = read(path)
        for row in value['copies']:
            check_ref(row['copy'])
        return value
    from scripts.legal_gap_program import verify as prior_verify
    checked = prior_verify()
    OUT.mkdir(parents=True, exist_ok=True)
    paths = [p for p in (ROOT / 'src/legalmath').rglob('*') if p.is_file()
             and p.suffix in ('.py', '.json', '.java', '.lean', '.sql')]
    paths += list((ROOT / 'scripts').glob('legal_gap_*.py'))
    paths += [ROOT / 'scripts/run_legal_gap_program.py', PLAN]
    copies = []
    for p in sorted(set(paths)):
        target = OUT / 'baseline' / p.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
        copies.append({'live': ref(p), 'copy': ref(target)})
    # Old evidence stays in place. Hash all immutable retained files; keep
    # snapshots of the two append-only allowance records separately.
    mutable = {'provider-allowance.json', 'repairs.json', 'provider.lock'}
    receipts = [ref(p) for p in sorted(PRIOR.rglob('*')) if p.is_file()
                and str(p.relative_to(PRIOR)) not in mutable and p.name != '.lock']
    for name in ('provider-allowance.json', 'repairs.json'):
        save(OUT / 'baseline' / name, read(PRIOR / name))
    result = {'predecessor_verification': checked, 'captured_at': time.time(),
              'git_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'copies': copies, 'predecessor_evidence': receipts,
              'budgets': budgets(), 'inventory': inventory()}
    save(path, result)
    return result


def check():
    value = baseline()
    return {'status': 'BASELINE_PRESERVED', 'files': len(value['copies']),
            'predecessor_files': len(value['predecessor_evidence']),
            'budgets': budgets(), 'inventory': value['inventory']}


def status():
    return {'state': read(OUT / 'state.json') if (OUT / 'state.json').exists() else 'PREPARED',
            'budgets': budgets()}


def verify():
    value = read(OUT / 'baseline.json')
    for row in value['copies']:
        check_ref(row['copy'])
    for row in value['predecessor_evidence']:
        check_ref(row)
    changes = [r['live']['path'] for r in value['copies'] if ref(ROOT / r['live']['path']) != r['live']]
    for name, field in (('provider-allowance.json','calls'),('repairs.json','repairs')):
        old=read(OUT/'baseline'/name);new=read(PRIOR/name)
        if old['maximum']!=new['maximum'] or new[field][:len(old[field])]!=old[field]:
            raise ValueError('Predecessor allowance history changed')
    new_phases=[]
    if (OUT/'state.json').exists():
        state=read(OUT/'state.json')
        check_ref(state['review'])
        review=read(check_ref(state['review']))
        check_ref(review['plan'])
        for row in review['files']:check_ref(row)
        from legalmath.interpretation.assurance.integrated import implementation_identity
        if implementation_identity()!=review['implementation']:
            raise ValueError('Reviewed product source changed')
        for phase,row in state['phases'].items():
            check_ref(row);new_phases.append(phase)
        if 'R2' in state['phases']:
            from legalmath.interpretation.assurance.complete_investigation import verify as verify_dossier
            r2=read(check_ref(state['phases']['R2']))
            verify_dossier(ROOT,read(check_ref(r2['controlled_product'])))
        if 'R3' in state['phases']:
            from legalmath.interpretation.assurance import fidelity_v2
            from legalmath.interpretation.assurance.scoped_investigation import execution_complete
            from scripts.legal_gap_recovery import retained_inputs,select_pairs
            inputs=retained_inputs('baseline');pairs=select_pairs(inputs)
            r3=read(check_ref(state['phases']['R3']))
            for arm,row in r3['arms'].items():
                if 'result' not in row:continue
                actual=read(check_ref(row['result']))
                if set(map(tuple,actual['required_pairs']))!=set(pairs) or row['full_pair_denominator']!=420:
                    raise ValueError('Live diagnostic denominator changed')
                for batch in actual['batches']:
                    for proposal in batch['proposals']:
                        fidelity_v2.validate(proposal,inputs['packet'],inputs['claims'],inputs['candidates'],
                                             inputs['questions'],batch['required_pairs'])
                if (row['status']=='ASSESSED')!=execution_complete(actual):
                    raise ValueError('Live diagnostic falsely reports assessed coverage')
    artifact_manifest=OUT/'evidence-manifest.json'
    if artifact_manifest.exists():
        for row in read(artifact_manifest)['files']:check_ref(row)
    return {'status': 'HISTORICAL_BASELINE_VERIFIED', 'live_source_changes': changes,
            'old_live_source_verifier': 'STALE_FOR_REPAIRED_SOURCE' if changes else 'UNCHANGED',
            'verified_repair_phases':new_phases,
            'budgets': budgets()}


def execute():
    from legalmath.interpretation.assurance.integrated import implementation_identity
    reviewed = read(DOC/'review.json')
    check_ref(reviewed['plan'])
    if reviewed['implementation'] != implementation_identity():
        raise ValueError('Product implementation changed after review')
    for row in reviewed['files']:
        check_ref(row)
    baseline()
    state_path = OUT/'state.json'
    state = read(state_path) if state_path.exists() else {
        'status': 'EXECUTING', 'phases': {}, 'review': ref(DOC/'review.json'),
        'started': time.time(), 'baseline_budgets': budgets()}
    check_ref(state['review'])
    phases = [('R1', regression), ('R2', offline), ('R3', live)]
    for index, (name, run) in enumerate(phases):
        if name in state['phases']:
            check_ref(state['phases'][name])
            continue
        save(OUT/'next-phase.json', {'phase': name, 'prerequisites': state['phases'],
            'question': {'R1': 'Do regression controls reject the traced defects?',
                         'R2': 'Do actual tools survive a complete controlled product workflow and retained inputs?',
                         'R3': 'Do both perspectives assess the same retained two pairs on the repaired path?'}[name],
            'budgets': budgets(), 'original_pairs': 420, 'original_open_obligations': 46,
            'continuation_veto': 'Stop dependent dispatch on invalid evidence or exhausted budget; retain all failures.'})
        print('EXECUTING '+name, flush=True)
        result = run()
        save(OUT/name/'result.json', result)
        state['phases'][name] = ref(OUT/name/'result.json')
        save(state_path, state)
        if result.get('engineering_pass') is False:
            state['status'] = 'REPAIR_REQUIRED'
            save(state_path, state)
            return state
    state['status'] = 'EXECUTED_WITH_OPEN_LEGAL_GAPS'
    save(OUT/'evidence-manifest.json',{'files':[ref(p) for phase in ('R1','R2','R3')
        for p in sorted((OUT/phase).rglob('*')) if p.is_file()
        and p.name!='.lock' and not p.name.endswith(('-wal','-shm'))]})
    state['verification'] = verify()
    state['final_budgets'] = budgets()
    save(state_path, state)
    save(OUT/'next-phase.json', {'phase': 'COMPLETE', 'original_open_obligations': 46,
        'unformalized_original_readings': 32, 'full_live_product_completion': False,
        'next_evidence': 'Reviewed realistic full-product budget, source/authority and dated factual premises, independent legal-quality evaluation.'})
    return state


TESTS = ['tests/assurance/test_integration_repair.py', 'tests/assurance/test_successor_workflow.py',
         'tests/assurance/test_successor_batch_capacity.py', 'tests/assurance/test_output_semantics.py',
         'tests/assurance/test_integrated_workflow.py', 'tests/assurance/test_fidelity_capacity.py',
         'tests/assurance/test_successor_continuation.py', 'tests/assurance/test_successor_grants.py',
         'tests/assurance/test_executable_references_v2.py', 'tests/assurance/test_arguments.py',
         'tests/assurance/test_integration.py', 'tests/tooling/test_legal_gap_program.py']


def regression():
    folder=OUT/'R1'
    receipt=command([ROOT/'.venv/bin/python','-m','pytest',*TESTS,'-q','--disable-warnings',
                     '--junitxml',folder/'tests.xml'],folder,'regression',timeout=600)
    import xml.etree.ElementTree as ET
    suites=ET.parse(folder/'tests.xml').getroot().findall('testsuite')
    counts={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','errors','failures','skipped')}
    return {'engineering_pass': not counts['failures'] and not counts['errors'],
            'counts': counts, 'execution': receipt, 'evidence': ref(folder/'tests.xml')}


def offline():
    from scripts.legal_integration_tools import ProductToolBackend
    from scripts.legal_gap_recovery import retained_inputs, select_pairs
    from legalmath.interpretation.assurance.optional_tools import ToolSession
    from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation, verify as verify_dossier
    from tests.search.support import FunctionProvider
    from tests.assurance.test_successor_workflow import complete_responder
    from tests.assurance.test_integration import source, settings
    from tests.assurance.test_round16 import JDK, AT
    from tests.assurance.test_arguments import argument, value, premise
    from tests.assurance.support import packet
    folder=OUT/'R2/final';folder.mkdir(parents=True,exist_ok=True)
    backend=ProductToolBackend()
    provider=FunctionProvider(complete_responder)
    runner=CompleteInvestigation(ROOT,folder/'controlled-product',provider,JDK,AT,
        settings=settings(),maximum_scoped_actions=12,scoped_rounds=1,optional_tool_backend=backend)
    dossier=runner.run([source()],'Selected gift control')
    save(folder/'dossier.json',dossier)
    checked=verify_dossier(ROOT,dossier)
    if not checked['execution_complete']:
        raise ValueError('Controlled complete product did not finish')
    before=len(provider.requests)
    # Reconstruct both the runner and provider to test actual process restart
    # semantics, then prove that no new request is needed.
    restarted_provider=FunctionProvider(lambda r: (_ for _ in ()).throw(AssertionError('Completed product redispatched')))
    restarted=CompleteInvestigation(ROOT,folder/'controlled-product',restarted_provider,JDK,AT,
        settings=settings(),maximum_scoped_actions=12,scoped_rounds=1,optional_tool_backend=backend)
    again=restarted.run([source()],'Selected gift control')
    if again!=dossier or restarted_provider.requests:
        raise ValueError('Completed product did not survive restart')
    for task, expected in [('SOURCE_FIDELITY','candidates'),('DEFINE_EXACT_QUESTIONS','criticism'),
                           ('SCOPED_SOURCE_FIDELITY','criticism')]:
        requests=[r for r in provider.requests if r['task']==task]
        if requests and not all(expected in {c['kind'] for c in r['external_tool_context']['checks']} for r in requests):
            raise ValueError('Validated tool feedback lost before '+task)
    inputs=retained_inputs('baseline');pairs=select_pairs(inputs)
    session=ToolSession(backend,folder/'retained-product-tools')
    candidates=session.candidates(inputs['packet'],inputs['candidates'])
    request=session.augment({'task':'RETAINED_PRODUCT_CHECK','source_packet':inputs['packet']})
    save(folder/'retained-inputs.json',{**inputs,'selected_pairs':pairs,'full_pair_denominator':420})
    save(folder/'retained-tool-request.json',request)
    # Actual external engines see inherited defeats and a blocked premise,
    # while a proposed preference is explicitly kept unaccepted.
    p=packet();a,b,c,d=argument(),argument('b','applicable.rule.a',True,'STRICT'),argument('c','child'),argument('d','other')
    c['parents']=['a'];d['premises']=[premise('ORDINARY','QUESTIONED')]
    proposal=value(a,b,c,d)
    proposal['attacks']=[{'attacker':'b','target':'a','kind':'UNDERCUT','target_component':'rule.a','rationale':'Controlled undercut'}]
    proposal['preferences']=[{'preferred':'a','over':'b','evidence':a['evidence'],'rationale':'Unaccepted proposal'}]
    controls=ToolSession(backend,folder/'graph-controls')
    normalized=controls.criticism(p,['candidate'],proposal)
    bound=controls.criticism(p,['candidate'],value(*(argument('node.'+str(i)) for i in range(12))))
    save(folder/'tool-summary.json',{'retained':session.report(),'graph_controls':controls.report()})
    return {'engineering_pass':True,'controlled_product':ref(folder/'dossier.json'),
        'controlled_provider_actions':before,'restarted_provider_actions':len(restarted_provider.requests),
        'controlled_product_verification':checked,'retained_candidates':candidates,
        'effective_graph_control':normalized,'twelve_argument_control':bound,
        'original_pairs':420,'selected_pairs':pairs,
        'live_product_completion':False,'legal_gap_closure':False,
        'limit':'Controlled model proposals test orchestration; actual engines and retained candidates test conditional computation only.'}


def live():
    from scripts.legal_gap_recovery import retained_inputs,select_pairs,ProgramGrant
    from scripts.legal_gap_live import Provider
    from scripts.legal_integration_tools import ProductToolBackend
    from legalmath.interpretation.assurance.optional_tools import ToolSession
    from legalmath.interpretation.assurance import scoped_investigation
    from legalmath.interpretation.assurance.executable_references_v2 import PROTOCOL
    from legalmath.interpretation.search.models import Settings
    inputs=retained_inputs('baseline');pairs=select_pairs(inputs)
    folder=OUT/'R3';folder.mkdir(parents=True,exist_ok=True)
    results={}
    initial=read(OUT/'state.json')['baseline_budgets']['used']
    for arm in ('baseline','combined'):
        target=folder/arm;target.mkdir(parents=True,exist_ok=True)
        final=target/'result.json'
        if final.exists():
            results[arm]=read(final)
            continue
        if (target/'started.json').exists():
            # No unknown provider outcome can be replayed by restarting the CLI.
            results[arm]={'status':'INTERRUPTED_REQUIRES_REVIEW','full_product_completion':False}
            continue
        current=budgets()
        if (current['used']-initial>2 or current['maximum']-current['used']<2
                or 24-current['arm_used'][arm]<2 or current['remaining_seconds']<400):
            results[arm]={'status':'UNTESTED_BUDGET_OR_WINDOW','budgets':current}
            continue
        tools=None
        if arm=='combined':
            tools=ToolSession(ProductToolBackend(),target/'tools')
            tools.candidates(inputs['packet'],inputs['candidates'])
        save(target/'started.json',{'before':current,'pairs':pairs,'full_denominator':420,
            'input_arm':'baseline','maximum_new_reservations':2})
        before=len(ledger()['calls'])
        provider=Provider(allowance=ProgramGrant(arm))
        result=scoped_investigation.investigate(inputs['packet'],inputs['claims'],inputs['candidates'],
            inputs['questions'],provider,target/'scoped',required_pairs=pairs,batch_size=2,maximum_rounds=1,
            maximum_actions=2,deadline_seconds=400,
            settings=Settings(timeout_seconds=180,max_input_bytes=200000,max_output_bytes=200000),
            schedule='round-first',reference_protocol=PROTOCOL,input_profile='readable-tables.v1',optional_tools=tools)
        after=len(ledger()['calls'])
        if after-before>2 or after-initial>4:raise ValueError('Live diagnostic exceeded reviewed four-call limit')
        row={'status':'ASSESSED' if scoped_investigation.execution_complete(result) else 'INCOMPLETE',
            'result':ref(target/'scoped/result.json'),'selected_pairs':pairs,'full_pair_denominator':420,
            'new_provider_reservations':after-before,'internal_matched_reservations':result['live_calls'],
            'tools':tools.report() if tools else None,'full_product_completion':False,'legal_gaps_closed':0}
        save(final,row);results[arm]=row
    return {'arms':results,'original_pairs':420,'legal_gaps_closed':0,
            'ranking':'Not supported: one development diagnostic per perspective, no uncertainty estimate.',
            'original_product_completion':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=ACTIONS)
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = globals()[args.action]()
    import json
    print(json.dumps(result, indent=2))
