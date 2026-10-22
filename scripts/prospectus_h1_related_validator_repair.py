"""Bounded original related-party disclosure delivery."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import prospectus_h1_trading_balances as prior
from scripts import prospectus_h1_related_parties as failed
from scripts import prospectus_h1_statement_consumer as common

read, save, sha, digest = prior.read, prior.save, prior.sha, prior.digest
compact_digest, same, require, rel = prior.compact_digest, prior.same, prior.require, prior.rel
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
BASE = AUTH / 'attempts/source-bes-dep-05'
PREP = AUTH / 'reviews/h1-related-validator-repair-402'
HERE = BASE / 'attempt-039'
SELF = 'scripts/prospectus_h1_related_validator_repair.py'
PLAN = 'docs/plans/prospectus-h1-related-validator-repair-2026-10-21.md'
PRODUCTION = prior.PRODUCTION
PROFILE = 'bes-h1-2010-statements-related-parties.v17'
DOCUMENT, PDF = prior.DOCUMENT, prior.PDF
PAGES = (154,155,156,157)
TESTS = prior.TESTS
DEPENDENCIES = {'render': [], 'source': ['render'], 'implement': ['source'],
    'tests': ['implement'], 'ordinary': ['tests'], 'controls': ['ordinary'],
    'package': ['controls'], 'installed': ['package'], 'coverage': []}


def authority():
    sys.path[:0] = [str(ROOT/'src'), str(ROOT)]
    from legalmath.prospectus.execution_authority import Authority
    return Authority(ROOT)


def costs(reserve=0):
    start = read(PREP/'accounting-start.json')
    paths = {p for d in (PREP, HERE) if d.exists() for p in d.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts}
    paths.update(ROOT/n for n in (PLAN, SELF, PRODUCTION))
    paths.add(AUTH/'revisions/0402.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH/'program.json').stat().st_size-start['program_bytes'])
    seconds = sum(read(p)['wall_seconds'] for d in (PREP, HERE) for p in d.glob('commands/*.json'))
    return {'new_bytes': size, 'new_measured_seconds': seconds, 'new_control_seconds': 60,
        'prior_known_bytes': start['prior_known_bytes'], 'prior_known_seconds': start['prior_known_seconds'],
        'known_cumulative_bytes': start['prior_known_bytes']+size,
        'known_cumulative_seconds': start['prior_known_seconds']+seconds+60,
        'earlier_manual_and_unmeasured_costs': 'UNKNOWN; history retained',
        'execution_allowed': size+reserve < 110*1024**2 and seconds < 960}


def prepare():
    tick=time.monotonic(); auth=authority(); old=read(AUTH/'program.json')
    require(old['revision']==401 and not PREP.exists() and not HERE.exists(),'Fresh401 required')
    events=auth.events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e['budget_key']=='source-bes-dep-05']
    require(len(attempts)==old['budgets']['source-bes-dep-05']['maximum_new_attempts']==38,'Retain38attempts')
    require(read(prior.HERE/'result.json')['status']=='PASS','037 must pass')
    protected={}
    for n in (7,15,16,17,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38):
        folder=BASE/f'attempt-{n:03d}'; manifest=folder/'outputs.json'
        records=[e for e in events if e.get('attempt')==rel(folder) and 'outputs_sha256' in e]
        require(records and sha(manifest)==records[-1]['outputs_sha256'],'Unauthenticated original')
        protected[rel(manifest)]=sha(manifest)
        for name,h in read(manifest).items(): require(sha(folder/name)==h,'Changed original '+name)
    previous=failed.costs()
    save(PREP/'accounting-start.json',{'prior_known_bytes':previous['known_cumulative_bytes'],
        'prior_known_seconds':previous['known_cumulative_seconds'],'prior_cost_receipt':previous,
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size})
    preflight=read(Path('/tmp/prospectus-related-repair-preflight.json'))
    require(preflight['status']=='PASS' and preflight['manual_image_review'], 'Mapping preflight required')
    save(PREP/'mapping-preflight.json',preflight)
    save(PREP/'commands/mapping-preflight.json',{'wall_seconds':preflight['seconds'],
        'command':'Full corrected source check plus source-corruption negative controls; retained summary in mapping-preflight.json'})
    (PREP/'baseline').mkdir(); shutil.copyfile(ROOT/PRODUCTION,PREP/'baseline/statement_cells.py')
    production=common.production();save(PREP/'baseline/production.json',production)
    protected.update({n:h for n,h in read(failed.PREP/'freeze.json')['bindings'].items() if n!=PRODUCTION})
    names=[PLAN,SELF,prior.SELF,failed.SELF,rel(failed.HERE/'image-transcript.json'),rel(failed.HERE/'SOURCE-REVIEW.md'),rel(failed.HERE/'images.json'),rel(failed.HERE/'FAILURE-REVIEW.md'),'pyproject.toml',*TESTS,rel(PREP/'mapping-preflight.json'),rel(PREP/'baseline/statement_cells.py'),
        rel(PREP/'baseline/production.json'),rel(prior.HERE/'ordinary.json.gz'),
        rel(prior.HERE/'source-units.json'),rel(prior.HERE/'reading.json'),
        rel(prior.HERE/'image-transcript.json'),rel(BASE/'attempt-028/COVERAGE-CORRECTION.md'),
        rel(prior.HERE/'images.json'),rel(prior.HERE/'registry-entry.json'),rel(BASE/'attempt-028/retained-risk-coverage-correction.json')]
    protected.update({n:sha(ROOT/n) for n in names})
    protected.update({n:h for n,h in production.items() if n!=PRODUCTION})
    require(all(sha(ROOT/n)==h for n,h in protected.items()),'Stale inherited binding')
    save(PREP/'freeze.json',{'bindings':protected,'baseline_sha256':sha(ROOT/PRODUCTION),
        'mutable_file':PRODUCTION,'implementation_window':'Once after reviewed source and candidate freeze'})
    config=read(prior.PREP/'config.json'); require(sha(config['package_python'])==config['python_sha256'],'Build interpreter changed')
    save(PREP/'config.json',config)
    new=deepcopy(old);new['revision']=402
    task=next(t for t in new['tasks'] if t['id']=='source-bes-dep-05')
    task.update(dossier=PLAN,pre_admission_review=PLAN,build_criteria_scope=[],
        reason='Repair 038 source validator and two transcript entries; deliver Note 41 preserving complete 037')
    task['inputs']=sorted((set(task['inputs'])-{PRODUCTION})|set(protected)|{rel(PREP/'freeze.json'),rel(PREP/'config.json')})
    bounds={'measured_seconds':960,'control_seconds':60,'new_bytes':112*1024**2,'failure_reserve':2*1024**2,
        'previous_known_bytes':previous['known_cumulative_bytes'],'previous_known_seconds':previous['known_cumulative_seconds'],'unchanged_retries':0}
    task['related_parties_evidence']={'version':PROFILE,'freeze':rel(PREP/'freeze.json'),'bounds':bounds,
        'success_dependencies':DEPENDENCIES,'original_task_acceptance':False}
    new['budgets']['source-bes-dep-05']['maximum_new_attempts']=39
    routes=read(ROOT/old['continuation_review']['routes']); routes['baseline_revision']=402
    for row in routes['tasks']:
        if row['task']==task['id']:
            row.update(task_sha256=compact_digest(task),dossier=PLAN,phase=0,
                remaining='037 trading balances retained; Note 41, Note 1 and wider source/authority remain.',
                next_action='Repair 038 and execute 039 Note 41 source/normal/installed delivery; retain 037 and reconcile remaining original dependencies.',
                stop_condition='Retain 38 admissions and permit attempt 39; 960+60 seconds and 112 MiB new; no unchanged retry; retain cumulative costs/failures.')
    save(PREP/'routes.json',routes)
    new['continuation_review'].update(plan=PLAN,routes=rel(PREP/'routes.json'))
    new['continuation_review']['bindings'].pop(PRODUCTION,None)
    new['continuation_review']['bindings'].update({n:sha(ROOT/n) for n in
        (PLAN,rel(PREP/'routes.json'),rel(PREP/'freeze.json'),rel(PREP/'baseline/statement_cells.py'))})
    require(old['obligations']==new['obligations'] and old['build_contract']==new['build_contract'],'Scope changed')
    raw=(json.dumps(new,ensure_ascii=False,indent=2)+'\n').encode()
    source_bytes=sum(p.stat().st_size for p in (ROOT/'src/legalmath').rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    forecast=costs()['new_bytes']+2*len(raw)+3*source_bytes+10*1024**2
    require(forecast<110*1024**2,'Forecast exceeds reservation')
    with (PREP/'proposal.json').open('xb') as stream:stream.write(raw)
    from legalmath.prospectus.execution_authority import digest as adigest
    save(PREP/'review.json',{'baseline':adigest(old),'scope_unchanged':True,'budget_unchanged':False,
        'changes':['Deliver Note 41; preserve complete 037','Preserve verified original composition including OCR risk tables','Retain 38 admissions and all original obligations'],
        'skeptical_audit':{'verdict':'PASS','plan':PLAN,'forecast_new_bytes':forecast,
            'no_proxy_promotion':'Original date/column geometry,conditional clauses and actual consumers;hashes and arithmetic do not prove legal or financial truth'},
        'evidence_contract':{'question':'Do related-party directories, dated balances and conditional report assertions reach the answer with source limits intact?',
            'primary':'Independent image transcript, original geometry/quotes, prior preservation and normal/installed corruption refusals',
            'promotion_veto':['Wrong date/amount/unit','Omitted clause','Lost prior answer','Conflicting duplicate','Wrong import','Accepted corruption'],
            'continuation_veto':['Invalid authority','Corrupt shared originals','Spent resources'],
            'not_concluded':['Automatic extraction','Verified valuation','Holder recovery','Current law','Whole build']},
        'budget_revision':{'budget_key':'source-bes-dep-05','previous_maximum':38,'new_maximum':39,
            'retained_attempts':attempts,'reason':'Changed repair of 038 validator and manual transcription; retain all prior failures and costs',
            'next_discriminating_check':'Related-party entity grouping, dated columns, source assertions and printed discrepancy without inferred zero',
            'stop_condition':bounds,'same_scope_authorization':'Recover and continue original build'}})
    save(PREP/'commands/preparation.json',{'wall_seconds':time.monotonic()-tick,
        'command':[sys.executable,'-B','-m','scripts.prospectus_h1_related_validator_repair','prepare']})
    return {'status':'PREPARED','revision':402,'forecast_new_bytes':forecast,'resources':costs()}


def frozen():
    auth = authority(); admission = read(HERE/'admission.json')
    from legalmath.prospectus.execution_authority import digest as adigest
    require(adigest(read(AUTH/'program.json'))==admission['program_sha256'] and
            auth.binding(admission['task_spec'])==admission['binding'], 'Unchanged admission required')
    f = read(PREP/'freeze.json')
    require(all(sha(ROOT/n)==h for n, h in f['bindings'].items()), 'Frozen input changed')
    expected = read(HERE/'candidate-production.json')[PRODUCTION] if (HERE/'candidate-production.json').exists() else f['baseline_sha256']
    require(sha(ROOT/PRODUCTION)==expected, 'Registry outside implementation window')


def command(name, argv, timeout=300):
    require(costs(1024**2)['execution_allowed'], 'Resource reservation exhausted')
    target = HERE/'commands'; target.mkdir(exist_ok=True); tick = time.monotonic(); result = None; error = None
    try:
        with (target/(name+'.log')).open('x') as stream:
            result = subprocess.run(argv, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout,
                env={**os.environ, 'CUDA_VISIBLE_DEVICES': '-1', 'PYTHONDONTWRITEBYTECODE': '1',
                     'PYTHONNOUSERSITE': '1', 'PYTHONPATH': str(ROOT/'src')+os.pathsep+str(ROOT),
                     'PIP_NO_INDEX': '1', 'PIP_DISABLE_PIP_VERSION_CHECK': '1'})
        require(result.returncode==0, 'Inspect retained '+name+'.log')
    except Exception as exc: error = {'type': type(exc).__name__, 'reason': str(exc)}
    save(target/(name+'.json'), {'command': argv, 'wall_seconds': time.monotonic()-tick,
        'exit_code': None if result is None else result.returncode, 'error': error})
    require(error is None, 'Command failed: '+name+': '+str(error))
    require(costs()['execution_allowed'], 'Post-command resource limit')


def corrected_transcript():
    transcript=deepcopy(read(failed.HERE/'image-transcript.json'))
    require(transcript['tables'][1]['rows'][8][1][6]==170 and
            transcript['tables'][2]['rows'][10][1][7]==5323,'Unexpected original transcript')
    transcript['tables'][1]['rows'][8][1][6]=70
    transcript['tables'][2]['rows'][10][1][7]=3523
    transcript['corrections']=[
        {'table':'holding-2010','row':'ESCOM','column':'Liabilities','from':170,'to':70},
        {'table':'holding-2009','row':'ES BANK PANAMA','column':'Income','from':5323,'to':3523}]
    transcript['correction_basis']='Original-resolution page 156 image independently re-read after failed 038; old transcript retained'
    return transcript


def render_worker():
    require(sha(BASE/'attempt-001/interim.pdf')==PDF,'Wrong original PDF')
    require(read(failed.HERE/'result.json')['status']=='FAIL','Retain failed 038')
    images=read(failed.HERE/'images.json')
    for item in images: require(sha(ROOT/item['path'])==item['sha256'],'Retained image changed')
    save(HERE/'images.json',images)
    save(HERE/'image-transcript.json',corrected_transcript())
    (HERE/'SOURCE-REVIEW.md').write_text((failed.HERE/'SOURCE-REVIEW.md').read_text()+
        '\n\n## Corrected transcript review\n\n'
        'Original-resolution page 156 was displayed again after the 038 failure. '
        'The 2010 ESCOM liability is 70, and 2009 ES BANK PANAMA income is 3,523, '
        'both in thousands of euro. The prior manual entries 170 and 5,323 were wrong. '
        'Only these two transcript cells are corrected, with explicit provenance. '
        'The complete source check and adverse cases pass before admission; '
        'the original failed transcript and source review remain immutable.\n')
    save(HERE/'source-reuse.json',{'source_attempt':rel(failed.HERE),'images':images,
        'original_transcript_sha256':sha(failed.HERE/'image-transcript.json'),
        'corrected_transcript_sha256':sha(HERE/'image-transcript.json'),'new_rendering':False})


def original_units():
    products = read(BASE/'attempt-007/products.json.gz')
    return sorted([u for u in products['P1']['payload']['graph']['units']
        if u['document'] == DOCUMENT and u['page'] in PAGES],
        key=lambda u: (u['page'], u['order'], u['id']))


def combined_units(units):
    old = prior.combined_units(read(prior.HERE/'source-units.json'))
    require(len(old) == 4006, 'Wrong 037 baseline')
    by_id = {u['id']: u for u in old}
    require(not set(by_id).intersection(u['id'] for u in units), 'Unexpected overlap')
    by_id.update({u['id']: u for u in units})
    require(len(by_id) == 5026, 'Wrong combined occurrences')
    return sorted(by_id.values(), key=lambda u: (u['page'], u['order'], u['id']))


def related_reading(units):
    lookup = {(u['page'], u['order']): u for u in units}
    def q(p, i):
        u = lookup[p, i]; return {'id': u['id'], 'quote': u['raw']}
    def qs(p, a, b): return [q(p, i) for i in range(a, b+1)]
    def cell(p, i):
        x = q(p, i); token = ''.join(x['quote'].split())
        v = None if token == '-' else int(token)
        return {**x, 'value': v, 'unit': 'EUR thousands',
                'status': 'UNKNOWN' if v is None else 'SOURCE_NUMBER'}
    def row(p, label, indices, inferred=None):
        return {'label_sources': [] if label is None else [q(p, label)],
                'label': inferred, 'cells': [cell(p, i) for i in indices]}
    fields = ['Assets', 'Liabilities', 'Guarantees', 'Income', 'Expenses']
    asset_fields = ['Loans and advances to banks', 'Loans', 'Securities', 'Other',
                    'Total assets', 'Guarantees', 'Liabilities', 'Income', 'Expenses']
    associates = {'key': 'associates', 'page': 155,
        'columns': [date+'/'+field for date in ('2010-06-30', '2009-12-31') for field in fields],
        'column_sources': [[q(155, i)] for i in (155,156,158,159,160,266,288,290,291,292)],
        'date_sources': [q(155,157),q(155,289)], 'unit_source': q(155,133),
        'rows': [row(155,135+i if i<20 else None,
            [a+i for a in (161,182,203,224,245,267,293,314,335,356)],
            'TOTAL (unlabelled)' if i==20 else None) for i in range(21)]}
    holding_2010 = {'key': 'holding-2010', 'page': 156,
        'columns': ['2010-06-30/'+field for field in asset_fields],
        'column_sources': [qs(156,14,16)]+[[q(156,i)] for i in range(17,25)],
        'date_sources': [q(156,12)], 'unit_source': q(156,11),
        'rows': [row(156,25+i,[a+i for a in (42,59,76,93,110,127,144,161,178)]) for i in range(17)]
            + [row(156,195,list(range(196,205)))]}
    holding_2009 = {'key': 'holding-2009', 'page': 156,
        'columns': ['2009-12-31/'+field for field in asset_fields],
        'column_sources': [qs(156,226,228)]+[[q(156,i)] for i in (247,266,285,304,323,324,361,380)],
        'date_sources': [q(156,206)], 'unit_source': q(156,205),
        'rows': [row(156,208+i,[a+i for a in (229,248,267,286,305,325,343,362,381)]) for i in range(18)]}
    directory = [
        {'category': 'Associates', 'headers': [q(154,4)], 'companies': qs(154,6,60)},
        {'category': 'ESFG subsidiaries, associates and related entities',
         'headers': [q(154,61)], 'companies': qs(154,63,101)},
        {'category': 'ESFG subsidiaries, associates and related entities',
         'headers': [q(154,102)], 'companies': qs(154,104,201)},
        {'category': 'ESFG subsidiaries, associates and related entities',
         'headers': [q(155,1),q(155,2)], 'companies': qs(155,5,130)}]
    specs = [('related-definition',154,2,3),('dated-balances',155,131,132),
        ('transaction-nature',156,1,2),('bes-vida-guarantee',156,3,8),
        ('holding-context',156,9,10),('key-management-loans',156,399,402),
        ('esfg-board-loans',157,1,3),('arms-length-assertion',157,4,4),
        ('company-law-assertion',157,5,6),('banking-law-and-reporting',157,7,12),
        ('executive-restrictions-and-exceptions',157,13,16),
        ('nonexecutive-approvals',157,17,19),('pricing-and-abstention',157,20,21),
        ('compliance-assertion',157,22,22),('individual-versus-portfolio-impairment',157,23,27),
        ('pension-fund-transactions',157,28,29)]
    return {'version': 'bes-related-parties-reading.v1',
        'source_groups': [{'page':p,'sources':[q(p,u['order']) for u in units if u['page']==p]} for p in PAGES],
        'directory': directory, 'tables': [associates, holding_2010, holding_2009],
        'clauses': [{'key':k,'sources':qs(p,a,b)} for k,p,a,b in specs],
        'narrative_amounts': [
            {'key':'guarantee-cost','values':['2.3',0],'unit':'EUR million',
             'dates':['2010-06-30','2009-12-31'],'nil_is_explicit':True,'sources':qs(156,3,8)},
            {'key':'key-management-loans','values':[28012,30313],'unit':'EUR thousands',
             'dates':['2010-06-30','2009-12-31'],'sources':qs(156,399,402)},
            {'key':'esfg-board-loans','values':[5661,5698],'unit':'EUR thousands',
             'dates':['2010-06-30','2009-12-31'],'sources':qs(157,1,3)}],
        'reported_conditions': {
            'guarantee_recognition':'Expected asset return below minimum guaranteed policyholder return',
            'executive_exceptions':'Source alternatives retained: social purpose, company policies, or comparable credit-card conditions',
            'nonexecutive_approvals':'At least two thirds of remaining board members AND Fiscal Board approval',
            'decision':'Market prices; involved board member cannot participate',
            'impairment':'No reported individual impairment; portfolio assessment remains',
            'legal_status':'HISTORICAL_REPORT_ASSERTIONS_NOT_VERIFIED_RULES'},
        'distinctions': {k:False for k in (
            'source_compliance_verified','arms_length_verified','current_law_verified',
            'related_means_consolidated','directory_establishes_identity','guarantee_is_unconditional',
            'individual_nonimpairment_means_no_credit_risk','dash_means_zero',
            'income_periods_assumed_equal','printed_total_replaced_by_sum')},
        'dependency_resolution': {'note1_group_structure_resolved':False,
            'source_authority_or_incorporation_resolved':False},
        'arithmetic_discrepancy': {
            'role':'EXPLANATORY_ONLY', 'table':'holding-2009',
            'other_row_known_component_sum':49611,'other_row_reported_total':31637,
            'known_subtotal_minus_reported_total':17974,
            'other_row_full_sum':'UNKNOWN: bank-advances cell is a printed dash',
            'aggregate_component_sum':923979,'aggregate_reported_total':906005,
            'aggregate_sum_minus_reported_total':17974,
            'source_cause':'NOT_ESTABLISHED','source_figures_preserved':True}}


def source_check(reading, units, transcript):
    require(len(units)==len({u['id'] for u in units})==1020, 'Complete 1020 occurrences required')
    lookup={u['id']:u for u in units}; s=reading['related_parties_evidence']
    norm=lambda x: ''.join(x.split())
    require(all(u['visible'] and u['source_sha256']==PDF and u['page'] in PAGES for u in units),'Changed source')
    def quotes(value):
        ids=[]
        if isinstance(value,dict):
            if 'id' in value and 'quote' in value:
                require(value['id'] in lookup and value['quote']==lookup[value['id']]['raw'],'Changed quote')
                ids.append(value['id'])
            for k,v in value.items():
                if k not in ('id','quote'): ids+=quotes(v)
        elif isinstance(value,list):
            for v in value: ids+=quotes(v)
        return ids
    quotes(s); require(set(quotes(s['source_groups']))==set(lookup),'Incomplete full pages')
    expected={u['id'] for u in units if
        (u['page']==154 and 2<=u['order']<=3) or
        (u['page']==155 and 131<=u['order']<=132) or
        (u['page']==156 and (1<=u['order']<=10 or 399<=u['order']<=402)) or
        (u['page']==157 and 1<=u['order']<=29)}
    refs=quotes(s['clauses'])
    require(set(refs)==expected and len(refs)==len(expected)==47,'Incomplete substantive clauses')
    directory_ids=[]
    require(len(s['directory'])==len(transcript['directory'])==4,'Missing directory block')
    for block,typed in zip(s['directory'],transcript['directory']):
        same(block['category'],typed['category'],'Wrong directory category')
        require(len(block['companies'])==typed['count'],'Missing company occurrence')
        same(block['companies'][0]['quote'],typed['first'],'Wrong directory start')
        same(block['companies'][-1]['quote'],typed['last'],'Wrong directory end')
        same([norm(x['quote']) for x in block['headers']], [norm(x) for x in typed['headers']], 'Wrong group headings')
        directory_ids+=quotes(block['companies'])
    expected_directory={u['id'] for u in units if
        (u['page']==154 and (6<=u['order']<=60 or 63<=u['order']<=101 or 104<=u['order']<=201)) or
        (u['page']==155 and 5<=u['order']<=130)}
    require(len(directory_ids)==len(set(directory_ids))==318 and set(directory_ids)==expected_directory,
            'Directory omitted, duplicated or silently merged')
    cells=[]
    require(len(s['tables'])==len(transcript['tables'])==3,'Three tables required')
    for table,typed in zip(s['tables'],transcript['tables']):
        same(table['key'],typed['key'],'Wrong table');same(table['columns'],typed['columns'],'Wrong date/field columns')
        same([norm(' '.join(x['quote'] for x in group)) for group in table['column_sources']],
             [norm(x) for x in typed['header_quotes']],'Wrong headings')
        same([norm(x['quote']) for x in table['date_sources']], [norm(x) for x in typed['date_quotes']], 'Wrong dates')
        same(norm(table['unit_source']['quote']),norm('(in thousands of euro)'),'Wrong table unit')
        require(len(table['rows'])==len(typed['rows']),'Missing rows')
        for row,manual in zip(table['rows'],typed['rows']):
            label=' '.join(x['quote'] for x in row['label_sources']) if row['label_sources'] else row['label']
            same(norm(label),norm(manual[0]),'Wrong row label')
            require(len(row['cells'])==len(manual[1])==len(table['columns']),'Wrong row width')
            for c,v in zip(row['cells'],manual[1]):
                token=norm(c['quote']); n=None if token=='-' else int(token)
                require(c['value']==v==n and c['unit']=='EUR thousands' and
                    c['status']==('UNKNOWN' if n is None else 'SOURCE_NUMBER'),'Wrong value/status/unit')
                cells.append(c)
            boxes=[lookup[c['id']]['bbox'] for c in row['cells']]
            require(all(a[2]<b[0] for a,b in zip(boxes,boxes[1:])) and
                max(b[1] for b in boxes)-min(b[1] for b in boxes)<3,'Wrong row geometry')
            for q in row['label_sources']:
                box=lookup[q['id']]['bbox']
                require(box[2]<boxes[0][0] and abs(box[1]-boxes[0][1])<3,'Wrong label geometry')
    numeric_ids={u['id'] for u in units if
        (u['page']==155 and (161<=u['order']<=265 or 267<=u['order']<=287 or 293<=u['order']<=376)) or
        (u['page']==156 and (42<=u['order']<=194 or 196<=u['order']<=204 or
            any(a<=u['order']<=b for a,b in ((229,246),(248,265),(267,284),(286,303),
                (305,322),(325,360),(362,379),(381,398)))))}
    require(len(cells)==len({c['id'] for c in cells})==534 and {c['id'] for c in cells}==numeric_ids,
            'Numeric positions omitted or duplicated')
    same(transcript['pages_reviewed'],list(PAGES),'Incomplete image review')
    for key in ('reported_conditions','distinctions','arithmetic_discrepancy'):
        same(s[key],transcript[key],'Wrong interpretation: '+key)
    same([{k:v for k,v in a.items() if k!='sources'} for a in s['narrative_amounts']],
         transcript['narrative_amounts'],'Wrong narrative amounts or units')
    require({a['key'] for a in transcript['anchors']}=={c['key'] for c in s['clauses']},'Missing source anchors')
    for a in transcript['anchors']:
        body=' '.join(q['quote'] for c in s['clauses'] if c['key']==a['key'] for q in c['sources'])
        require(' '.join(a['quote'].split()) in ' '.join(body.split()),'Wrong manual clause anchor')
    other=s['tables'][2]['rows'][-2]['cells']; total=s['tables'][2]['rows'][-1]['cells']
    d=s['arithmetic_discrepancy']
    require(other[0]['value'] is None and sum(c['value'] for c in other[1:4])==d['other_row_known_component_sum']
        and other[4]['value']==d['other_row_reported_total'],'Wrong OTHER diagnostic')
    require(sum(c['value'] for c in total[:4])==d['aggregate_component_sum'] and
            total[4]['value']==d['aggregate_reported_total'],'Wrong aggregate diagnostic')
    require(d['other_row_known_component_sum']-d['other_row_reported_total']==d['known_subtotal_minus_reported_total']
        and d['aggregate_component_sum']-d['aggregate_reported_total']==d['aggregate_sum_minus_reported_total'],
        'Wrong diagnostic differences')
    old=read(prior.HERE/'reading.json')
    same({k:v for k,v in reading.items() if k!='related_parties_evidence'},old,'037 reading changed')
    prior.source_check(old,read(prior.HERE/'source-units.json'),read(prior.HERE/'image-transcript.json'))
    return {'local_occurrences':1020,'combined_occurrences':len(combined_units(units)),
        'company_occurrences':318,'rows':57,'numeric_or_unknown_positions':534,
        'unknown_dashes':sum(c['value'] is None for c in cells),'clause_groups':16,
        'substantive_occurrences':47,'complete_prior_fields_preserved':True,
        'source_arithmetic_discrepancy':d,'financial_truth_or_current_law_verified':False}


def full_graph_preflight(candidate, reading, graph):
    namespace={'__name__':'legalmath.prospectus.successor._related_candidate',
               '__package__':'legalmath.prospectus.successor'}
    exec(compile(candidate,'candidate-statement_cells.py','exec'),namespace)
    packet={'version':'source-statement-cells.v1','profile':PROFILE,'document':DOCUMENT,
        'graph_sha256':digest(graph),'review':{'kind':'DEVELOPMENT',
        'reviewer':'Original images, source clauses and table transcription','reason':'Actual full-graph preflight'},'reading':reading}
    admitted=namespace['admit'](graph,packet)
    bad=deepcopy(graph);bad['units']=[u for u in bad['units'] if u['id']!='bes-interim-h1-2010:p154:l0']
    negative=deepcopy(packet);negative['graph_sha256']=digest(bad)
    try:namespace['admit'](bad,negative)
    except ValueError as exc:require('original pages or geometry' in str(exc),'Wrong context refusal')
    else:raise ValueError('Missing source context accepted')
    return {'status':'PASS','actual_graph_admitted':True,'context_loss_refused':True,'admitted_sha256':admitted['sha256']}


def source_worker():
    units=original_units();transcript=read(HERE/'image-transcript.json');review=HERE/'SOURCE-REVIEW.md'
    require(review.is_file() and len(review.read_text())>1000,'Substantive source review required')
    for item in read(HERE/'images.json'):require(sha(ROOT/item['path'])==item['sha256'],'Source image changed')
    reading=deepcopy(read(prior.HERE/'reading.json'));reading['related_parties_evidence']=related_reading(units)
    checked=source_check(reading,units,transcript);all_units=combined_units(units)
    save(HERE/'source-units.json',units);save(HERE/'reading.json',reading)
    entry={'document':DOCUMENT,'source':PDF,'reading':compact_digest(reading),'pages_digest':compact_digest(all_units),
        'pages':sorted({u['page'] for u in all_units}),'occurrences':len(all_units),
        'reading_fields':list(read(prior.HERE/'registry-entry.json')['reading_fields'])+['related_parties_evidence']}
    original=(PREP/'baseline/statement_cells.py').read_text()
    require(PROFILE not in original and original.count('PROFILES = {')==1,'Baseline registry changed')
    candidate=original.replace('PROFILES = {\n','PROFILES = {\n    '+repr(PROFILE)+': '+repr(entry)+',\n',1)
    actual_graph=read(BASE/'attempt-007/products.json.gz')['P1']['payload']['graph']
    save(HERE/'full-graph-preflight.json',full_graph_preflight(candidate,reading,actual_graph))
    (HERE/'candidate-statement_cells.py').write_text(candidate);save(HERE/'registry-entry.json',entry)
    names=['reading.json','source-units.json','registry-entry.json','candidate-statement_cells.py',
        'image-transcript.json','SOURCE-REVIEW.md','images.json','full-graph-preflight.json']
    save(HERE/'candidate-freeze.json',{'bindings':{n:sha(HERE/n) for n in names},'candidate_sha256':digest(candidate.encode())})
    from legalmath.prospectus.successor import statement_cells as cells
    try:cells.admit({'units':all_units},supplied({'units':all_units}))
    except ValueError as exc:require('Unsupported source statement' in str(exc),'Unexpected baseline refusal')
    else:raise ValueError('New profile already supported')
    save(HERE/'source-check.json',{'status':'PASS',**checked,'baseline_gap':'Note 41 profile unsupported','source_review':common.ref(review)})

def candidate_frozen():
    f=read(HERE/'candidate-freeze.json')
    require(all(sha(HERE/n)==h for n,h in f['bindings'].items()),'Candidate interpretation changed')
    return f


def implement_worker():
    f=candidate_frozen(); require(sha(ROOT/PRODUCTION)==read(PREP/'freeze.json')['baseline_sha256'],'Baseline changed')
    shutil.copyfile(HERE/'candidate-statement_cells.py',ROOT/PRODUCTION)
    require(sha(ROOT/PRODUCTION)==f['candidate_sha256'],'Registry write failed')
    save(HERE/'candidate-production.json',common.production())


def supplied(graph):
    return {'version':'source-statement-cells.v1','profile':PROFILE,'document':DOCUMENT,'graph_sha256':digest(graph),
        'review':{'kind':'DEVELOPMENT','reviewer':'Original page images,exact clauses and independently transcribed tables',
            'reason':'Complete 037 plus Note 41; entity groups, dates, conditions and source assertions remain explicit'},
        'reading':read(HERE/'reading.json')}


def build_products(original):
    from legalmath.prospectus.successor import service
    p1=deepcopy(original['P1']); request=p1['payload']['request']; request['source_statement_cells']=supplied(p1['payload']['graph'])
    p1=service.seal('P1',request['bundle'],{'request':digest(request)},p1['payload'])
    p2=service.construction_product(p1,ROOT); p3=service.interpretation_product(p1,p2,original['P3']['payload'].get('interpretation_input'))
    l,f=original['P4']['payload'],original['P5']['payload']
    return {'P1':p1,'P2':p2,'P3':p3,'P4':service.law_product(p1,p3,l.get('cases'),l.get('law_input')),
            'P5':service.financial_product(p1,p2,p3,f.get('cases'),f.get('scenario_input'))}


def registry_controls():
    from legalmath.prospectus.successor import statement_cells as cells
    graph={'units':combined_units(read(HERE/'source-units.json'))}; rows=[]
    changes={k:(lambda s,k=k:s['distinctions'].update({k:True}))
             for k in read(HERE/'reading.json')['related_parties_evidence']['distinctions']}
    changes.update({
        'company-omitted':lambda s:s['directory'][0]['companies'].pop(),
        'company-duplicated':lambda s:s['directory'][0]['companies'].append(deepcopy(s['directory'][0]['companies'][0])),
        'company-renamed':lambda s:s['directory'][0]['companies'][0].update(quote='Different legal entity'),
        'entity-category':lambda s:s['directory'][0].update(category='Consolidated subsidiaries'),
        'dates-reversed':lambda s:s['tables'][0]['columns'].reverse(),
        'row-lost':lambda s:s['tables'][1]['rows'].pop(),
        'unknown-to-zero':lambda s:s['tables'][2]['rows'][-2]['cells'][0].update(value=0,status='SOURCE_NUMBER'),
        'printed-total-repaired':lambda s:s['tables'][2]['rows'][-2]['cells'][4].update(value=49611),
        'wrong-unit':lambda s:s['tables'][1]['rows'][0]['cells'][0].update(unit='EUR million'),
        'guarantee-amount':lambda s:s['narrative_amounts'][0]['values'].__setitem__(0,'23'),
        'explicit-nil-lost':lambda s:s['narrative_amounts'][0]['values'].__setitem__(1,None),
        'guarantee-condition':lambda s:s['reported_conditions'].update(guarantee_recognition='Unconditional'),
        'approval-disjunction':lambda s:s['reported_conditions'].update(nonexecutive_approvals='Two thirds OR Fiscal Board'),
        'impairment-overclaim':lambda s:s['reported_conditions'].update(impairment='No credit risk'),
        'clause-lost':lambda s:s['clauses'].pop(),
        'discrepancy-hidden':lambda s:s.pop('arithmetic_discrepancy'),
        'note1-resolved':lambda s:s['dependency_resolution'].update(note1_group_structure_resolved=True),
        'authority-resolved':lambda s:s['dependency_resolution'].update(source_authority_or_incorporation_resolved=True)})
    for name,change in changes.items():
        bad=supplied(graph); change(bad['reading']['related_parties_evidence'])
        try: cells.admit(graph,bad)
        except ValueError as exc:
            require('reading differs' in str(exc),'Unexpected reading refusal')
            rows.append({'case':name,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else: raise ValueError('Altered reading accepted: '+name)
    for name in ('missing-page','context-occurrence-lost','source-hash','geometry','duplicate-occurrence'):
        g=deepcopy(graph)
        if name=='missing-page': g['units']=[u for u in g['units'] if u['page']!=157]
        elif name=='context-occurrence-lost': g['units']=[u for u in g['units'] if u['id']!='bes-interim-h1-2010:p154:l0']
        elif name=='source-hash': next(u for u in g['units'] if u['page']==154)['source_sha256']='0'*64
        elif name=='geometry': next(u for u in g['units'] if u['id']=='bes-interim-h1-2010:p156:l245')['bbox'][1]+=4
        else: g['units'].append(deepcopy(next(u for u in g['units'] if u['page']==155)))
        bad=supplied(g)
        try: cells.admit(g,bad)
        except ValueError as exc: rows.append({'case':name,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else: raise ValueError('Altered source accepted: '+name)
    return rows

def consumer_worker(kind):
    from legalmath.prospectus.successor import service
    candidate_frozen(); original=read(BASE/'attempt-007/products.json.gz')
    baseline=prior.build_products(original); before=service.consume(baseline,ROOT,include_artifacts=True)
    previous=read(prior.HERE/'ordinary.json.gz')
    require(digest(before)==previous['answer_sha256'],'Complete037baseline answer changed')
    current=build_products(original); after=service.consume(current,ROOT,include_artifacts=True)
    for phase in ('P2','P3','P4','P5'):
        left,right=deepcopy(baseline[phase]['payload']),deepcopy(current[phase]['payload'])
        if phase=='P2': left.pop('source_statement_cells'); right.pop('source_statement_cells')
        if phase=='P3': left.pop('source_statement_cells_sha256'); right.pop('source_statement_cells_sha256')
        same(left,right,'Unexpected phase payload change: '+phase)
    same(current['P1']['payload']['graph'],baseline['P1']['payload']['graph'],'Source graph changed')
    left,right=deepcopy(baseline['P1']['payload']['request']),deepcopy(current['P1']['payload']['request'])
    left.pop('source_statement_cells'); right.pop('source_statement_cells'); same(left,right,'Unrelated request changed')
    replacements={k:after[k] for k in ('request_sha256','consumed_products','report_sha256')}
    same({**before,**replacements,'source_statement_cells':after['source_statement_cells']},after,'Unrelated answer change')
    same(before['questions'],after['questions'],'Original questions changed')
    require(after['questions']['Q3']['status']=='PARTIAL' and not after['may_execute_transaction'] and
            not after['independent_legal_acceptance'],'Original limits changed')
    baseline_reading=read(prior.HERE/'reading.json')
    for key in baseline_reading: same(before['source_statement_cells'][key],after['source_statement_cells'][key],'Lost037field '+key)
    body=after['source_statement_cells']; reading=read(HERE/'reading.json')
    for key in reading: same(body[key],reading[key],'Incomplete delivered field '+key)
    require(body['consumed'] and not body['independent_financial_acceptance'] and body['legal_dependency_resolution']=='UNCHANGED','Scope overclaim')
    checked=source_check(reading,read(HERE/'source-units.json'),read(HERE/'image-transcript.json'))
    cases=registry_controls()
    imported={n:m.__file__ for n,m in sys.modules.items() if n.startswith('legalmath') and getattr(m,'__file__',None)}
    location=HERE/'installed' if kind=='installed' else ROOT/'src'
    require(imported and all(Path(p).resolve().is_relative_to(location) for p in imported.values()),'Wrong import origin')
    del original,baseline,current,left,right
    composed=read(BASE/'attempt-016/answer-supplement.json.gz'); composition=read(BASE/'attempt-017/composition.json')
    require(digest(composed)==composition['previous_content_sha256'],'Original016changed')
    composed.update(read(BASE/'attempt-017/answer-delta.json.gz'))
    require(digest(composed)==composition['complete_composed_sha256'],'Original017changed')
    keys={21:'h1_normal_statement_consumer',22:'h1_debt_context_consumer',23:'h1_debt_securities_consumer',
          24:'h1_cross_note_consumer',25:'h1_securitisation_consumer',26:'h1_fair_value_consumer',28:'h1_risk_native_consumer',29:'h1_events_consumer',30:'h1_financial_policies_consumer',32:'h1_investment_hedges_consumer',33:'h1_income_collateral_consumer',35:'h1_afs_disclosures_consumer',36:'h1_critical_judgments_consumer',37:'h1_trading_balances_consumer'}
    for n,key in keys.items():
        receipt=read(BASE/f'attempt-{n:03d}/ordinary.json.gz')
        answer={**before,**receipt['replacements'],'source_statement_cells':receipt['addition']}
        require(digest(answer)==receipt['answer_sha256'],'Complete prior answer changed: '+str(n))
        composed[key]=answer
        require(digest(composed)==receipt['full_composed_sha256'],'Complete prior composition changed: '+str(n))
    composed['h1_related_parties_consumer']=after
    receipt={'status':'PASS','prior_complete_answer_sha256':digest(before),'answer_sha256':digest(after),
        'prior_full_composed_sha256':previous['full_composed_sha256'],'full_composed_sha256':digest(composed),
        'reading_sha256':compact_digest(reading),'replacements':replacements,'addition':body,'controls':cases,
        'source_check':checked,'imports':imported,'whole_task_complete':False,'source_truth_established':False,
        'recipe':'Reconstruct 037 from 007; preserve 016/017 and 021/022/023/024/025/026/028/029/030/032/033/035/036/037 compositions; add 039 as h1_related_parties_consumer'}
    del composed,before,after,answer
    if kind=='installed':
        ordinary=read(HERE/'ordinary.json.gz')
        for key in receipt:
            if key!='imports': same(receipt[key],ordinary[key],'Installed mismatch: '+key)
        controls_worker('installed-controls.json')
        same(read(HERE/'installed-controls.json'),read(HERE/'controls.json'),'Installed corruption refusals differ')
    save(HERE/(kind+'.json.gz'),receipt)


def controls_worker(output='controls.json'):
    from legalmath.prospectus.successor import service
    original=read(BASE/'attempt-007/products.json.gz'); current=build_products(original); rows=[]
    for change in ('missing_p2','changed_p2','missing_p3','changed_p3','unsupplied'):
        bad=deepcopy(current); request=bad['P1']['payload']['request']; p2,p3=bad['P2']['payload'],bad['P3']['payload']
        if change=='missing_p2': del p2['source_statement_cells']
        elif change=='changed_p2': p2['source_statement_cells']['reading']['related_parties_evidence']['distinctions']['source_compliance_verified']=True
        elif change=='missing_p3': del p3['source_statement_cells_sha256']
        elif change=='changed_p3': p3['source_statement_cells_sha256']='0'*64
        else: del request['source_statement_cells']
        b=request['bundle']; bad['P1']=service.seal('P1',b,{'request':digest(request)},bad['P1']['payload'])
        for phase,parents in [('P2',['P1']),('P3',['P1','P2']),('P4',['P1','P3']),('P5',['P2','P3'])]:
            bad[phase]=service.seal(phase,b,{p:bad[p]['sha256'] for p in parents},bad[phase]['payload'])
        try: service.consume(bad,ROOT,include_artifacts=True)
        except ValueError as exc:
            require('Consumed statement cells' in str(exc),'Unexpected refusal')
            rows.append({'case':change,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else: raise ValueError('Forged rehashed product accepted: '+change)
    save(HERE/output,{'status':'PASS','actual_consumer_refusals':rows})


def package_worker():
    candidate_frozen(); source=HERE/'package-source'; source.mkdir()
    shutil.copyfile(ROOT/'pyproject.toml',source/'pyproject.toml')
    shutil.copytree(ROOT/'src',source/'src',ignore=shutil.ignore_patterns('__pycache__','*.pyc','*.pyo','*.egg-info'))
    config=read(PREP/'config.json'); python=config['package_python']
    require(sha(python)==config['python_sha256'],'Build interpreter changed')
    command('wheel',[python,'-I','-B','-m','pip','wheel','--no-deps','--no-build-isolation','--no-index',
        '--wheel-dir',str(HERE/'wheel'),str(source)],60)
    wheels=list((HERE/'wheel').glob('*.whl')); require(len(wheels)==1,'Exactly one wheel required')
    expected={n.removeprefix('src/legalmath/'):h for n,h in read(HERE/'candidate-production.json').items()}
    with zipfile.ZipFile(wheels[0]) as archive:
        actual={n.removeprefix('legalmath/'):digest(archive.read(n)) for n in archive.namelist()
                if n.startswith('legalmath/') and not n.endswith('/')}
    same(actual,expected,'Wheel differs from candidate')
    command('install',[python,'-I','-B','-m','pip','install','--no-index','--no-deps','--no-compile',
        '--target',str(HERE/'installed'),str(wheels[0])],60)
    folder=HERE/'installed/legalmath'
    same({str(p.relative_to(folder)):sha(p) for p in folder.rglob('*') if p.is_file()},expected,'Installed bytes differ')
    save(HERE/'package.json',{'python':python,'wheel':common.ref(wheels[0]),'files':expected})


def coverage_worker():
    rows=deepcopy(read(prior.HERE/'requirements.json')['rows'])
    for row in rows:
        if row.get('status','').startswith('THIS_ATTEMPT_MUST_PASS'):
            row.update(status='RETAINED_COMPLETE_FINITE_INTEGRATION',evidence=common.ref(prior.HERE/'result.json'))
    rows.append({'requirement':'Original Note 41 directory, dated balances, lending conditions and reported discrepancy with complete 037 retained',
                 'status':'THIS_ATTEMPT_MUST_PASS; see actual stage results'})
    inventory=deepcopy(read(prior.HERE/'note-inventory.json'))
    for row in inventory['notes']:
        if row['note'] in (17,18): row['status']='RETAINED_FINITE_INTEGRATION'
        elif row['note']==41: row['status']='THIS_ATTEMPT_SUBJECT_TO_STAGE_RESULTS'
    save(HERE/'note-inventory.json',inventory)
    save(HERE/'requirements.json',{'rows':rows,'original_task_acceptance':False,
        'external_adviser_opinion_required':False,
        'next_discriminating_work':'Inspect Note 1 group structure against related-party and retained capital/debt readings; remaining policies/notes, controlling edition and source authority remain.'})

def stage(name):
    require(name in DEPENDENCIES and not (HERE/'stages'/name).exists(),'Stage already started or unknown')
    for parent in DEPENDENCIES[name]: require(read(HERE/'stages'/parent/'result.json')['status']=='PASS','Failed predecessor '+parent)
    frozen(); require(costs(46*1024**2 if name=='package' else 4*1024**2)['execution_allowed'],'Stage reservation exhausted')
    from legalmath.prospectus.execution_authority import process_identity
    save(HERE/'stages'/name/'started.json',{'identity':process_identity(os.getpid()),'at':datetime.now(timezone.utc).isoformat(),'stage':name})
    error=None
    try:
        if name=='render': render_worker()
        elif name=='package': package_worker()
        elif name=='tests': command('tests',[str(ROOT/'.venv/bin/python'),'-B','-m','pytest','-q',*TESTS,'--junitxml='+str(HERE/'tests.xml')],300)
        else:
            python=read(PREP/'config.json')['package_python'] if name=='installed' else str(ROOT/'.venv/bin/python')
            command(name,[python,'-I','-B',str(ROOT/SELF),'worker-'+name],300)
        frozen()
    except Exception as exc: error={'type':type(exc).__name__,'reason':str(exc)}
    save(HERE/'stages'/name/'result.json',{'status':'FAIL' if error else 'PASS','error':error})
    return {'stage':name,'status':'FAIL' if error else 'PASS','error':error,'resources':costs()}


def finalize():
    require(not (HERE/'outputs.json').exists(),'Already sealed')
    outcomes={n:read(HERE/'stages'/n/'result.json')['status'] if (HERE/'stages'/n/'result.json').exists() else 'BLOCKED' for n in DEPENDENCIES}
    passed=all(v=='PASS' for v in outcomes.values())
    save(HERE/'result.json',{'task':'source-bes-dep-05','status':'PASS' if passed else 'FAIL','stages':outcomes,
        'task_complete':False,'whole_program_complete':False,'build_criteria_claimed':[],'resources':costs()})
    (HERE/'RESULT.md').write_text('# Original related-party disclosures\n\n'+('Finite source/consumer integration passed. ' if passed else 'Campaign did not pass. ')
        +'Actual stages: '+json.dumps(outcomes)+'.\n\n'
        +'Note 41 retains related-party groups, dated balances, conditional lending rules and attributed report assertions. '
        +'The printed 2009 discrepancy remains explicit; unknown dashes are not zeros. '
        +'The full 037 answer and all original compositions including supplied OCR risk tables remain preserved. '
        +'Historical report claims do not establish current standards,rights,valuation or whole-source acceptance.\n\n'
        +'|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|\n|---|---|---|---|---|---|\n'
        +'|'+('Retain finite integration' if passed else 'Retain actual failure')+'|Original images/quotes/geometry and actual full normal/installed answers|See stage records|Remaining notes and authority|Record/refresh;reconcile remaining source obligations with actual current coverage|Financial truth,current law,holder entitlement,automatic extraction,whole build|\n\n'
        +'Post-run review: exact profiles preserve supplied readings; a shared wrong interpretation remains the strongest alternative explanation. '
        +'The independent image transcript and full quote/geometry review address source association and omissions. '
        +'They do not prove external financial or legal truth. Remaining coverage is an implementation/evidence gap,not evidence that a package is fundamentally unsuitable.\n')
    save(HERE/'run-manifest.json',{'git_commit':read(HERE/'admission.json')['git_commit'],
        'commands':[read(p) for p in sorted((HERE/'commands').glob('*.json'))],
        'environment':str(ROOT/'.venv/bin/python'),'cpu_gpu':'CPU_ONLY;CUDA_VISIBLE_DEVICES=-1;GPU intentionally hidden',
        'random_seeds':'N/A deterministic','plan':PLAN,'result':rel(HERE/'RESULT.md'),
        'data_version':common.ref(PREP/'freeze.json'),'resources':costs()})
    save(HERE/'outputs.json',{str(p.relative_to(HERE)):sha(p) for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts})
    return {'status':'SEALED','candidate_passed':passed,'resources':costs()}


if __name__=='__main__':
    sys.dont_write_bytecode=True
    os.environ.update(CUDA_VISIBLE_DEVICES='-1',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1')
    action=sys.argv[1]
    if action.startswith('worker-'):
        kind=action.removeprefix('worker-'); sys.path.insert(0,str(HERE/'installed') if kind=='installed' else str(ROOT/'src'))
        def forbidden(*args,**kwargs): raise RuntimeError('No native/network child in source/consumer worker')
        subprocess.Popen=forbidden
        if kind in ('ordinary','installed'): consumer_worker(kind)
        else: {'source':source_worker,'implement':implement_worker,'controls':controls_worker,'coverage':coverage_worker}[kind]()
        result={'status':'PASS','worker':kind}
    elif action=='prepare': result=prepare()
    elif action=='finalize': result=finalize()
    else: result=stage(action)
    print(json.dumps(result))
