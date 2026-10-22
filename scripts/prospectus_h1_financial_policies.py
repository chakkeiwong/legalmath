"""Bounded original financial-instrument accounting-policy delivery."""
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
from scripts import prospectus_h1_events as prior
from scripts import prospectus_h1_statement_consumer as common

read, save, sha, digest = prior.read, prior.save, prior.sha, prior.digest
compact_digest, same, require, rel = prior.compact_digest, prior.same, prior.require, prior.rel
AUTH = ROOT / 'docs/implementation/prospectus-execution-authority'
BASE = AUTH / 'attempts/source-bes-dep-05'
PREP = AUTH / 'reviews/h1-financial-policies-393'
HERE = BASE / 'attempt-030'
SELF = 'scripts/prospectus_h1_financial_policies.py'
PLAN = 'docs/plans/prospectus-h1-financial-policies-2026-10-21.md'
PRODUCTION = prior.PRODUCTION
PROFILE = 'bes-h1-2010-statements-financial-policies.v9'
DOCUMENT, PDF = prior.DOCUMENT, prior.PDF
PAGES = tuple(range(73,81))
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
    paths.add(AUTH/'revisions/0393.json')
    paths.update(p for p in (AUTH/'history').glob('*.json') if p.name not in start['history_names'])
    size = sum(p.stat().st_size for p in paths if p.exists())
    size += max(0, (AUTH/'program.json').stat().st_size-start['program_bytes'])
    seconds = sum(read(p)['wall_seconds'] for d in (PREP, HERE) for p in d.glob('commands/*.json'))
    return {'new_bytes': size, 'new_measured_seconds': seconds, 'new_control_seconds': 60,
        'prior_known_bytes': start['prior_known_bytes'], 'prior_known_seconds': start['prior_known_seconds'],
        'known_cumulative_bytes': start['prior_known_bytes']+size,
        'known_cumulative_seconds': start['prior_known_seconds']+seconds+60,
        'earlier_manual_and_unmeasured_costs': 'UNKNOWN; history retained',
        'execution_allowed': size+reserve < 110*1024**2 and seconds < 840}


def prepare():
    tick=time.monotonic(); auth=authority(); old=read(AUTH/'program.json')
    require(old['revision']==392 and not PREP.exists() and not HERE.exists(),'Fresh392 required')
    events=auth.events()
    attempts=[e['attempt'] for e in events if e['kind']=='ADMIT' and e['budget_key']=='source-bes-dep-05']
    require(len(attempts)==old['budgets']['source-bes-dep-05']['maximum_new_attempts']==29,'Retain29attempts')
    require(read(prior.HERE/'result.json')['status']=='PASS','029 must pass')
    protected={}
    for n in (7,15,16,17,21,22,23,24,25,26,27,28,29):
        folder=BASE/f'attempt-{n:03d}'; manifest=folder/'outputs.json'
        records=[e for e in events if e.get('attempt')==rel(folder) and 'outputs_sha256' in e]
        require(records and sha(manifest)==records[-1]['outputs_sha256'],'Unauthenticated original')
        protected[rel(manifest)]=sha(manifest)
        for name,h in read(manifest).items(): require(sha(folder/name)==h,'Changed original '+name)
    previous=prior.costs()
    save(PREP/'accounting-start.json',{'prior_known_bytes':previous['known_cumulative_bytes'],
        'prior_known_seconds':previous['known_cumulative_seconds'],'prior_cost_receipt':previous,
        'history_names':[p.name for p in (AUTH/'history').glob('*.json')],
        'program_bytes':(AUTH/'program.json').stat().st_size})
    (PREP/'baseline').mkdir(); shutil.copyfile(ROOT/PRODUCTION,PREP/'baseline/statement_cells.py')
    production=common.production();save(PREP/'baseline/production.json',production)
    protected.update({n:h for n,h in read(prior.PREP/'freeze.json')['bindings'].items() if n!=PRODUCTION})
    names=[PLAN,SELF,prior.SELF,'pyproject.toml',*TESTS,rel(PREP/'baseline/statement_cells.py'),
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
    new=deepcopy(old);new['revision']=393
    task=next(t for t in new['tasks'] if t['id']=='source-bes-dep-05')
    task.update(dossier=PLAN,pre_admission_review=PLAN,build_criteria_scope=[],
        reason='Deliver original policies2.3–2.7with conditions and exceptions;preserve029and prior OCRintegration')
    task['inputs']=sorted((set(task['inputs'])-{PRODUCTION})|set(protected)|{rel(PREP/'freeze.json'),rel(PREP/'config.json')})
    bounds={'measured_seconds':840,'control_seconds':60,'new_bytes':112*1024**2,'failure_reserve':2*1024**2,
        'previous_known_bytes':previous['known_cumulative_bytes'],'previous_known_seconds':previous['known_cumulative_seconds'],'unchanged_retries':0}
    task['financial_policies_evidence']={'version':PROFILE,'freeze':rel(PREP/'freeze.json'),'bounds':bounds,
        'success_dependencies':DEPENDENCIES,'original_task_acceptance':False}
    new['budgets']['source-bes-dep-05']['maximum_new_attempts']=30
    routes=read(ROOT/old['continuation_review']['routes']); routes['baseline_revision']=393
    for row in routes['tasks']:
        if row['task']==task['id']:
            row.update(task_sha256=compact_digest(task),dossier=PLAN,phase=0,
                remaining='029events and prior OCRintegration retained;policies2.3–2.7and wider source/authority remain.',
                next_action='Execute030policies2.3–2.7through source/normal/installed checks;retain029and reconcile remaining dependencies.',
                stop_condition='30 retained admissions;840+60seconds and112MiB new;no unchanged retry;retain cumulative costs/failures.')
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
        'changes':['Deliver policies2.3–2.7;preserve complete029','Preserve verified original composition including OCRrisk tables','Retain29admissions and all original obligations'],
        'skeptical_audit':{'verdict':'PASS','plan':PLAN,'forecast_new_bytes':forecast,
            'no_proxy_promotion':'Original cross-page conditions and actual consumers;exact hashes do not prove interpretation or current legal standards'},
        'evidence_contract':{'question':'Do original accounting policies reach the answer with conditions and exceptions intact?',
            'primary':'Independent image transcript, original geometry/quotes, prior preservation and normal/installed corruption refusals',
            'promotion_veto':['Wrong date/amount/unit','Omitted clause','Lost prior answer','Conflicting duplicate','Wrong import','Accepted corruption'],
            'continuation_veto':['Invalid authority','Corrupt shared originals','Spent resources'],
            'not_concluded':['Automatic extraction','Verified valuation','Holder recovery','Current law','Whole build']},
        'budget_revision':{'budget_key':'source-bes-dep-05','previous_maximum':29,'new_maximum':30,
            'retained_attempts':attempts,'reason':'Original policies2.3–2.7dependency;no replay of029or historical OCRintegration',
            'next_discriminating_check':'Cross-page hedge discontinuation,embedded AND condition,equity reversal,repo recognition and complete downstream delivery',
            'stop_condition':bounds,'same_scope_authorization':'Recover and continue original build'}})
    save(PREP/'commands/preparation.json',{'wall_seconds':time.monotonic()-tick,
        'command':[sys.executable,'-B','-m','scripts.prospectus_h1_financial_policies','prepare']})
    return {'status':'PREPARED','revision':393,'forecast_new_bytes':forecast,'resources':costs()}


def frozen():
    auth = authority(); admission = read(HERE/'admission.json')
    from legalmath.prospectus.execution_authority import digest as adigest
    require(adigest(read(AUTH/'program.json'))==admission['program_sha256'] and
            auth.binding(admission['task_spec'])==admission['binding'], 'Unchanged admission required')
    f = read(PREP/'freeze.json')
    require(all(sha(ROOT/n)==h for n, h in f['bindings'].items()), 'Frozen input changed')
    expected = read(HERE/'candidate-production.json')[PRODUCTION] if (HERE/'candidate-production.json').exists() else f['baseline_sha256']
    require(sha(ROOT/PRODUCTION)==expected, 'Registry outside implementation window')


def command(name, argv, timeout=240):
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


def render_worker():
    require(sha(BASE/'attempt-001/interim.pdf')==PDF,'Wrong original PDF')
    (HERE/'images').mkdir()
    for page in PAGES:
        command('render-'+str(page),['pdftoppm','-f',str(page),'-l',str(page),'-r','160','-singlefile','-png',
            str(BASE/'attempt-001/interim.pdf'),str(HERE/'images'/f'page-{page}')],60)
    save(HERE/'images.json',[{'page':p,'path':rel(HERE/'images'/f'page-{p}.png'),'sha256':sha(HERE/'images'/f'page-{p}.png')} for p in PAGES])


def original_units():
    products = read(BASE/'attempt-007/products.json.gz')
    return sorted([u for u in products['P1']['payload']['graph']['units']
        if u['document']==DOCUMENT and u['page'] in PAGES], key=lambda u: (u['page'],u['order'],u['id']))


def combined_units(units):
    by_id={}
    for n in (15,22,23,24,25,26,28,29):
        for unit in read(BASE/f'attempt-{n:03d}/source-units.json'):
            if unit['id'] in by_id:same(unit,by_id[unit['id']],'Conflicting prior occurrence')
            by_id[unit['id']]=unit
    require(len(by_id)==2715,'Wrong029occurrence count')
    overlap=0
    for unit in units:
        if unit['id'] in by_id:
            same(unit,by_id[unit['id']],'Conflicting source overlap');overlap+=1
        by_id[unit['id']]=unit
    require(overlap==32 and len(by_id)==2961,'Wrong deduplicated occurrence coverage')
    return sorted(by_id.values(),key=lambda u:(u['page'],u['order'],u['id']))



def policies_reading(units):
    lookup={(u['page'],u['order']):u for u in units}
    def q(page,line):
        u=lookup[page,line];return {'id':u['id'],'quote':u['raw']}
    def qs(page,a,b):return [q(page,i) for i in range(a,b+1)]
    specs=[
        ('fx-monetary',[(73,1,5)],'Translate transactions at transaction-date functional-currency rates; monetary foreign-currency balances at closing euro rates; translation differences in income.'),
        ('fx-nonmonetary',[(73,6,11)],'Historical-cost nonmonetary items use transaction-date rates; fair-value items use valuation-date rates; differences enter income except AFS equity instruments, whose differences enter equity/fair-value reserve.'),
        ('derivative-classification',[(73,12,17)],'Risk-management derivatives include designated hedges and economic risk management of FVTPL assets/liabilities without hedge-accounting classification. All other derivatives are trading.'),
        ('derivative-measurement',[(73,18,27)],'Initial recognition at trade-date fair value; regular remeasurement through income except designated hedges, whose accounting depends on risk and hedge model. Active-market quotes when available; otherwise DCF or option models as appropriate.'),
        ('hedge-criteria',[(74,1,15)],'All four criteria apply: documented relationship, item, instrument and effectiveness at inception; expected high effectiveness at inception and ongoing; reliable measurement at inception and ongoing; cash-flow hedges additionally require highly probable cash flows.'),
        ('fair-value-hedge',[(74,16,26)],'Adjust the hedged item for fair-value changes attributable to the hedged risks; derivative and corresponding item changes enter income. On loss of qualification transfer derivative to trading and discontinue prospectively; amortise EIR-item cumulative adjustment to income until maturity.'),
        ('cash-flow-hedge',[(74,27,33)],'Effective derivative changes enter equity and recycle when the hedged item affects income; ineffective changes enter income immediately.'),
        ('hedge-discontinuation',[(74,34,36),(75,1,2)],'Expiry, sale or loss of hedge qualification leaves accumulated equity to recycle when the hedged transaction affects income. If the transaction is no longer expected, recycle immediately and reclassify the instrument to trading.'),
        ('no-cash-flow-hedges',[(75,3,4)],'The Group reports no transactions classified as cash-flow hedges during the period covered by these statements.'),
        ('embedded-derivatives',[(75,5,9)],'Separate embedded derivatives when economic characteristics and risks are not closely related to the host AND the host is not carried at FVTPL. Remeasure separated derivatives at fair value through income.'),
        ('loan-recognition',[(75,10,13)],'Originated customer loans not intended for short-term sale are recognised when cash is advanced.'),
        ('loan-derecognition',[(75,14,17)],'Derecognise on expiry of cash-flow rights, transfer of substantially all risks and rewards, OR retention of some but not substantially all risks and rewards together with transferred control.'),
        ('loan-measurement',[(75,18,20)],'Initially fair value plus transaction costs; subsequently EIR amortised cost less impairment.'),
        ('loan-economic-hedge',[(75,21,27)],'Certain loans economically hedged by derivatives are FVTPL to eliminate measurement mismatch without hedge accounting. Preserve references to policies 2.4 and 2.6.'),
        ('loan-impairment',[(76,1,9)],'Assess objective evidence at each balance date; losses and later decreases enter income. Impairment requires post-recognition event evidence AND a reliably estimated effect on future cash flows.'),
        ('individual-factors',[(76,10,25)],'Individual assessment considers total exposure/nonperforming loans, business viability and debt-service cash flows, senior creditor commitments, collateral nature and realisable value, financial-sector exposure, and recovery amount/timing.'),
        ('collective-exclusion',[(76,26,29)],'Individually assessed loans without evidence of loss join similar-risk groups for collective assessment; individually impaired loans are excluded from collective assessment.'),
        ('loan-loss-measure',[(76,30,37)],'Loss is book value minus PV of expected cash flows considering recovery period, discounted at original EIR; variable-rate loans use current contractual EIR. Reduce carrying value through allowance; discount unwind enters interest and similar income.'),
        ('collateral-costs',[(77,1,2)],'Collateralised-loan recovery cash flows include foreclosure proceeds less obtaining and selling costs.'),
        ('collective-estimates',[(77,3,8)],'Group loans by similar credit risk; estimate contractual flows using historical loss experience; regularly review assumptions against actual losses.'),
        ('writeoff',[(77,9,10)],'Write off against the allowance only when considered uncollectible AND a 100 percent impairment loss has been recognised.'),
        ('fvtpl-classification',[(77,11,20)],'FVTPL includes trading assets acquired for short-term sale or managed portfolios with recent actual short-term profit-taking, and assets designated FVTPL at inception.'),
        ('fvtpl-designation',[(77,21,33)],'Inception designation applies to assets managed/measured/evaluated on fair value, economically hedged to eliminate mismatch, or containing embedded derivatives. Note 23 summarises designated assets/liabilities; acquired structured products containing embedded derivatives satisfy the stated category conditions.'),
        ('htm-classification',[(78,1,6)],'HTM means nonderivatives with fixed/determinable payments and fixed maturity plus positive intention AND ability to hold to maturity, excluding inception FVTPL/AFS classification.'),
        ('afs-classification',[(78,7,11)],'AFS nonderivatives are intended for indefinite holding, designated AFS at inception, or not classified in the other categories.'),
        ('asset-recognition',[(78,12,18)],'Recognise FVTPL, HTM and AFS purchases/sales on trade date. Initial fair value plus costs, except FVTPL transaction costs enter income immediately.'),
        ('asset-derecognition',[(78,19,22)],'Derecognise on expired cash-flow rights, substantially all risks/rewards transferred, OR some but not substantially all retained with control transferred.'),
        ('fvtpl-subsequent',[(78,23,26)],'Subsequent FVTPL changes enter income in the period arising.'),
        ('afs-subsequent',[(78,27,33)],'AFS fair-value changes enter equity until derecognition/impairment then recycle to income. AFS equity FX enters equity; debt FX enters income. EIR interest and dividends enter income.'),
        ('htm-and-values',[(79,1,6)],'HTM uses EIR amortised cost net of impairment. Active-market quoted investments use current bid prices; unlisted securities use recent arm-length transactions, DCF/options models and market-information assumptions.'),
        ('reclassification',[(79,7,17)],'Only nonderivatives with fixed/determinable payments and fixed maturity may move AFS to HTM with intention AND ability to hold. Use reclassification-date fair value; amortise difference from nominal and fair-value reserve through income via EIR. No reclassifications reported in H1 2010 or 2009.'),
        ('asset-impairment-evidence',[(79,18,26)],'Periodically assess objective post-recognition event evidence; equity includes significant OR prolonged decline below cost; debt requires reliably estimated cash-flow effects. Determine recoverable amount and recognise loss in income.'),
        ('htm-impairment-reversal',[(79,27,32),(80,1,3)],'HTM loss is carrying value minus PV of expected flows at original EIR, with current contractual EIR for variable rates; use allowance. Reverse through income only when decrease objectively relates to a post-loss event.'),
        ('afs-impairment-reversal',[(80,4,11)],'AFS cumulative loss transferred from equity to income equals acquisition cost minus current fair value minus prior income-recognised impairment. Subsequent qualifying post-loss-event recovery reverses through income up to acquisition cost EXCEPT equity instruments, whose reversal enters equity.'),
        ('repo',[(80,12,16)],'Sold repo securities remain recognised; corresponding due-bank/customer liability is recorded. Sale/repurchase difference is EIR interest over the agreement.'),
        ('reverse-repo',[(80,17,20)],'Reverse-repo securities are not recognised; price paid is a loan to bank/customer. Purchase/resale difference is EIR interest over the agreement.'),
        ('securities-lending',[(80,21,23)],'Lent securities remain recognised and measured under 2.6; borrowed securities are not recognised on the balance sheet.')
    ]
    clauses=[{'key':key,'sources':[x for p,a,b in spans for x in qs(p,a,b)],'interpretation':meaning} for key,spans,meaning in specs]
    return {'source_groups':{str(p):[q(p,u['order']) for u in units if u['page']==p] for p in PAGES},
        'clauses':clauses,'policies':['2.3','2.4','2.5','2.6','2.7'],
        'distinctions':{'economic_hedging_implies_hedge_accounting':False,'hedge_criteria_count':4,
            'embedded_separation_operator':'AND','cash_flow_hedges_reported_in_period':False,
            'transaction_no_longer_expected_recycles':'IMMEDIATE','expiry_alone_recycles':'WHEN_HEDGED_TRANSACTION_AFFECTS_INCOME',
            'individually_impaired_in_collective':False,'individual_assessment_factors':6,
            'fixed_rate_impairment_discount':'ORIGINAL_EIR','variable_rate_impairment_discount':'CURRENT_CONTRACTUAL_EIR',
            'writeoff_operator':'UNCOLLECTIBLE_AND_100_PERCENT_IMPAIRED',
            'fvtpl_transaction_costs':'IMMEDIATE_INCOME','afs_equity_fx':'EQUITY','afs_debt_fx':'INCOME',
            'htm_requires':'INTENTION_AND_ABILITY','reclassifications_reported_h12010_or2009':False,
            'equity_impairment_trigger':'SIGNIFICANT_OR_PROLONGED_DECLINE',
            'afs_equity_reversal':'EQUITY','repo_securities_derecognised':False,
            'reverse_repo_securities_recognised':False,'lent_securities_derecognised':False,
            'borrowed_securities_recognised':False,'accounting_recognition_proves_legal_title':False},
        'source_dependencies':{'2.4':'DELIVERED_HERE','2.6':'DELIVERED_HERE','Note23':'ORIGINAL_RETAINED_FULL_INTERPRETATION_NOT_ESTABLISHED'},
        'retained_context':'Page80policy2.8already delivered;32equal occurrences deduplicated',
        'source_context':{'origin':'SUPPLIED_DEVELOPMENT_READING','source_authenticity':'NOT_ESTABLISHED',
            'incorporation_status':'UNRESOLVED','current_law_or_standard_verified':False,
            'historical_report_claims_only':True,'holder_recovery_established':False}}



def source_check(reading,units,transcript):
    require(len(units)==278 and len({u['id'] for u in units})==278,'Complete278occurrences required')
    lookup={u['id']:u for u in units};s=reading['financial_policies_evidence']
    require(all(u['visible'] and u['source_sha256']==PDF and u['page'] in PAGES for u in units),'Changed source')
    def quotes(v):
        ids=[]
        if isinstance(v,dict):
            if 'id' in v and 'quote' in v:
                require(v['id'] in lookup and v['quote']==lookup[v['id']]['raw'],'Changed exact quote');ids.append(v['id'])
            for k,x in v.items():
                if k not in ('id','quote'):ids+=quotes(x)
        elif isinstance(v,list):
            for x in v:ids+=quotes(x)
        return ids
    quotes(s);require(set(quotes(s['source_groups']))==set(lookup),'Incomplete page context')
    end={73:27,74:36,75:27,76:37,77:33,78:33,79:32,80:23}
    expected={u['id'] for u in units if 1<=u['order']<=end[u['page']]}
    refs=quotes(s['clauses']);require(set(refs)==expected and len(refs)==len(expected),'Omitted or duplicate policy clause')
    require(len(s['clauses'])==37,'Wrong clause count')
    by_key={c['key']:c for c in s['clauses']};norm=lambda text:' '.join(text.split())
    require(len(transcript['anchors'])>=12,'Independent discriminating passages required')
    for anchor in transcript['anchors']:
        actual=norm(' '.join(x['quote'] for x in by_key[anchor['key']]['sources']))
        require(norm(anchor['quote']) in actual,'Independent passage mismatch: '+anchor['key'])
    same(s['distinctions'],transcript['distinctions'],'Independent interpretation distinctions mismatch')
    require(transcript['pages_reviewed']==list(PAGES),'All eight original pages must be inspected')
    for page in PAGES:
        selected=sorted((u for u in units if u['page']==page),key=lambda u:u['order'])
        require(all(len(u['bbox'])==4 and u['bbox'][0]<u['bbox'][2] and u['bbox'][1]<u['bbox'][3] for u in selected),'Invalid geometry')
        require(all(b['bbox'][1]>=a['bbox'][1]-3 for a,b in zip(selected,selected[1:])),'Unexpected reading-order geometry')
    old=read(prior.HERE/'reading.json');same({k:v for k,v in reading.items() if k!='financial_policies_evidence'},old,'029reading changed')
    prior.source_check(old,read(prior.HERE/'source-units.json'),read(prior.HERE/'image-transcript.json'))
    return {'local_occurrences':278,'overlap_occurrences':32,'new_occurrences':246,'total_occurrences':len(combined_units(units)),
        'clauses':37,'substantive_occurrences':len(expected),'independent_passages':len(transcript['anchors']),
        'complete_prior_fields_preserved':True,'exact_profiles_are_not_general_parser_proof':True}



def source_worker():
    units=original_units();transcript=read(HERE/'image-transcript.json');review=HERE/'SOURCE-REVIEW.md'
    require(review.is_file() and len(review.read_text())>1000,'Substantive source review required')
    for item in read(HERE/'images.json'):require(sha(ROOT/item['path'])==item['sha256'],'Source image changed')
    reading=deepcopy(read(prior.HERE/'reading.json'));reading['financial_policies_evidence']=policies_reading(units)
    checked=source_check(reading,units,transcript);all_units=combined_units(units)
    save(HERE/'source-units.json',units);save(HERE/'reading.json',reading)
    entry={'document':DOCUMENT,'source':PDF,'reading':compact_digest(reading),'pages_digest':compact_digest(all_units),
        'pages':sorted({u['page'] for u in all_units}),'occurrences':len(all_units),
        'reading_fields':list(read(prior.HERE/'registry-entry.json')['reading_fields'])+['financial_policies_evidence']}
    original=(PREP/'baseline/statement_cells.py').read_text()
    require(PROFILE not in original and original.count('PROFILES = {')==1,'Baseline registry changed')
    candidate=original.replace('PROFILES = {\n','PROFILES = {\n    '+repr(PROFILE)+': '+repr(entry)+',\n',1)
    (HERE/'candidate-statement_cells.py').write_text(candidate);save(HERE/'registry-entry.json',entry)
    names=['reading.json','source-units.json','registry-entry.json','candidate-statement_cells.py','image-transcript.json','SOURCE-REVIEW.md','images.json']
    save(HERE/'candidate-freeze.json',{'bindings':{n:sha(HERE/n) for n in names},'candidate_sha256':digest(candidate.encode())})
    from legalmath.prospectus.successor import statement_cells as cells
    try:cells.admit({'units':all_units},supplied({'units':all_units}))
    except ValueError as exc:require('Unsupported source statement' in str(exc),'Unexpected baseline refusal')
    else:raise ValueError('New profile already supported')
    save(HERE/'source-check.json',{'status':'PASS',**checked,'baseline_gap':'Policies2.3–2.7profile unsupported','source_review':common.ref(review)})


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
        'review':{'kind':'DEVELOPMENT','reviewer':'Original page images,exact clauses and independently transcribed discriminating passages',
            'reason':'Complete029plus policies2.3–2.7;conditions,exceptions and historical scope remain explicit'},
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
    graph={'units':combined_units(read(HERE/'source-units.json'))};rows=[]
    distinctions=read(HERE/'reading.json')['financial_policies_evidence']['distinctions']
    for key,value in distinctions.items():
        bad=supplied(graph)
        bad['reading']['financial_policies_evidence']['distinctions'][key]=not value if isinstance(value,bool) else ('OR' if key=='embedded_separation_operator' else 'ALTERED')
        try:cells.admit(graph,bad)
        except ValueError as exc:rows.append({'case':key,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else:raise ValueError('Altered distinction accepted: '+key)
    for name in ('missing-clause','current-law','incorporation','missing-page','source-hash','geometry','duplicate-occurrence'):
        g=deepcopy(graph);bad=supplied(g);s=bad['reading']['financial_policies_evidence']
        if name=='missing-clause':s['clauses'].pop()
        elif name=='current-law':s['source_context']['current_law_or_standard_verified']=True
        elif name=='incorporation':s['source_context']['incorporation_status']='CONFIRMED'
        elif name=='missing-page':g['units']=[u for u in g['units'] if u['page']!=75]
        elif name=='source-hash':next(u for u in g['units'] if u['page']==79)['source_sha256']='0'*64
        elif name=='geometry':next(u for u in g['units'] if u['page']==79)['bbox'][0]+=1
        else:g['units'].append(deepcopy(next(u for u in g['units'] if u['page']==80)))
        bad['graph_sha256']=digest(g)
        try:cells.admit(g,bad)
        except ValueError as exc:rows.append({'case':name,'refused':True,'reason':str(exc),'input_sha256':digest(bad)})
        else:raise ValueError('Altered source or scope accepted: '+name)
    return rows



def consumer_worker(kind):
    from legalmath.prospectus.successor import service
    candidate_frozen(); original=read(BASE/'attempt-007/products.json.gz')
    baseline=prior.build_products(original); before=service.consume(baseline,ROOT,include_artifacts=True)
    previous=read(prior.HERE/'ordinary.json.gz')
    require(digest(before)==previous['answer_sha256'],'Complete029baseline answer changed')
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
    for key in baseline_reading: same(before['source_statement_cells'][key],after['source_statement_cells'][key],'Lost029field '+key)
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
          24:'h1_cross_note_consumer',25:'h1_securitisation_consumer',26:'h1_fair_value_consumer',28:'h1_risk_native_consumer',29:'h1_events_consumer'}
    for n,key in keys.items():
        receipt=read(BASE/f'attempt-{n:03d}/ordinary.json.gz')
        answer={**before,**receipt['replacements'],'source_statement_cells':receipt['addition']}
        require(digest(answer)==receipt['answer_sha256'],'Complete prior answer changed: '+str(n))
        composed[key]=answer
        require(digest(composed)==receipt['full_composed_sha256'],'Complete prior composition changed: '+str(n))
    composed['h1_financial_policies_consumer']=after
    receipt={'status':'PASS','prior_complete_answer_sha256':digest(before),'answer_sha256':digest(after),
        'prior_full_composed_sha256':previous['full_composed_sha256'],'full_composed_sha256':digest(composed),
        'reading_sha256':compact_digest(reading),'replacements':replacements,'addition':body,'controls':cases,
        'source_check':checked,'imports':imported,'whole_task_complete':False,'source_truth_established':False,
        'recipe':'Reconstruct029from007;preserve016/017and021/022/023/024/025/026/028/029compositions;add030as h1_financial_policies_consumer'}
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
        elif change=='changed_p2': p2['source_statement_cells']['reading']['financial_policies_evidence']['distinctions']['embedded_separation_operator']='OR'
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
    previous=read(prior.HERE/'requirements.json');rows=deepcopy(previous['rows'])
    for row in rows:
        if row.get('status','').startswith('THIS_ATTEMPT_MUST_PASS'):
            row.update(status='RETAINED_COMPLETE_FINITE_INTEGRATION',evidence=common.ref(prior.HERE/'result.json'))
    rows.append({'requirement':'Original policies2.3–2.7 with conditions and exceptions;prior029and OCRrisk integration retained',
                 'status':'THIS_ATTEMPT_MUST_PASS;see stage outcomes'})
    inventory=deepcopy(read(prior.HERE/'note-inventory.json'))
    for row in inventory['notes']:
        if row['note'] in (45,46):row['status']='RETAINED_FINITE_INTEGRATION'
    for policy in ('2.3','2.4','2.5','2.6','2.7'):inventory['policies'][policy]='THIS_ATTEMPT_SUBJECT_TO_STAGE_RESULTS'
    inventory['task_acceptance']=False
    save(HERE/'note-inventory.json',inventory)
    save(HERE/'requirements.json',{'rows':rows,'original_task_acceptance':False,'external_adviser_opinion_required':False,
        'next_discriminating_work':'Inspect retained Note23and related loan/asset note coverage before next refinement. Preserve earlier OCR162–163,benefits and supplement coverage. Controlling edition,source authority,incorporation and wider notes remain.'})



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
        elif name=='tests': command('tests',[str(ROOT/'.venv/bin/python'),'-B','-m','pytest','-q',*TESTS,'--junitxml='+str(HERE/'tests.xml')],240)
        else:
            python=read(PREP/'config.json')['package_python'] if name=='installed' else str(ROOT/'.venv/bin/python')
            command(name,[python,'-I','-B',str(ROOT/SELF),'worker-'+name],240)
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
    (HERE/'RESULT.md').write_text('# Original financial-instrument accounting policies\n\n'+('Finite source/consumer integration passed. ' if passed else 'Campaign did not pass. ')
        +'Actual stages: '+json.dumps(outcomes)+'.\n\n'
        +'Policies2.3–2.7retain FX,hedge criteria,loan impairment,asset classification,reversals and repo recognition with their conditions and exceptions. '
        +'The full029answer and all original compositions including supplied OCRrisk tables remain preserved. '
        +'Historical report claims do not establish current standards,rights,valuation or whole-source acceptance.\n\n'
        +'|Decision|Primary criterion|Veto status|Uncertainty|Next action|Not concluded|\n|---|---|---|---|---|---|\n'
        +'|'+('Retain finite integration' if passed else 'Retain actual failure')+'|Original images/quotes/geometry and actual full normal/installed answers|See stage records|Remaining notes and authority|Record/refresh;review Note23and remaining original coverage|Financial truth,current law,holder entitlement,automatic extraction,whole build|\n\n'
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
