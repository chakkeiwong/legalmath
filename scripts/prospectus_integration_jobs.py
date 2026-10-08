"""Fixed jobs for the reviewed integration repair; immutable attempts only."""
from copy import deepcopy
import json
from pathlib import Path
import sys
from scripts.prospectus_integration_repair import ROOT,OUT,SIDECAR,save,sha,command


def load(path):
    return json.loads(path.read_text())


def layout(folder):
    from legalmath.prospectus.successor.layout_adapter import map_layout,project_layout,evaluate_relationships
    old=ROOT/'docs/implementation/prospectus-adoption/phases/A3/attempt-005'
    unit_path=ROOT/'docs/implementation/prospectus-adoption/phases/A0/attempt-007/raw-units.json'
    units=load(unit_path)
    inputs=load(old/'layout-input.json')
    target=load(old/'critical-spans-before-prediction.json')
    save(folder/'layout-input.json',inputs)
    save(folder/'critical-targets.json',target)
    bound={str(p.relative_to(ROOT)):sha(p) for p in (unit_path,old/'layout-input.json',old/'critical-spans-before-prediction.json')}
    for row in inputs['pages']:
        path=ROOT/row['path']
        if sha(path)!=row['sha256']:raise ValueError('PDF source changed')
        bound[row['path']]=sha(path)
    save(folder/'inputs.json',bound)
    # The exact same pinned worker/configuration as the rejected arm.
    command(folder,'docling',[str(ROOT/'.venv/bin/python'),'-m','scripts.prospectus_adoption_sidecar','layout',
            '--input',str(folder/'layout-input.json'),'--output',str(folder/'layout')],300)
    strict=[];repaired=[]
    for i,row in enumerate(inputs['pages']):
        raw=[u for u in units if u['document']==row['document'] and u['page']==row['page']]
        doc=load(folder/'layout'/f'layout-{i}.json')
        strict.append(map_layout(raw,doc,source_sha256=row['sha256']))
        repaired.append(project_layout(raw,doc,source_sha256=row['sha256']))
    save(folder/'strict.json',strict);save(folder/'repaired.json',repaired)
    def missing(results):
        seen={(c['unit'],c['source_offset']) for r in results for m in r['mappings'] for c in m['characters']}
        return [u['id'] for u in target if any((u['id'],i) not in seen for i,ch in enumerate(u['raw']) if not ch.isspace())]
    before,after=missing(strict),missing(repaired)
    if after or any(r['failures'] for r in repaired):
        raise ValueError('Source projection still incomplete; inspect repaired.json')
    prefix='basf-base-september-2022-exchange:p112:l'
    def anchor(number):
        u=next(r for r in units if r['id']==prefix+str(number))
        return {'document':u['document'],'source_sha256':u['source_sha256'],'unit':u['id'],
                'start':0,'end':len(u['raw']),'quote':u['raw']}
    target_edge={'kind':'governs','scope':'all Actual/Actual options',
                 'from':[anchor(i) for i in (64,65,66)],'to':[anchor(i) for i in (85,86,87)]}
    image_path=ROOT/'docs/implementation/prospectus-repair-2026-10-06/document-review/prospectus-basf-bracket-112.png'
    save(folder/'margin-target.json',{'edge':target_edge,'review':'Implementer source-image review, 8 October 2026; not independent adjudication',
         'image':str(image_path.relative_to(ROOT)),'image_sha256':sha(image_path),
         'basis':'Printed p112: shared reference-period definition alongside margin applying to all Actual/Actual options'})
    mapped=[m for r in repaired for m in r['mappings']]
    # Manual reviewed and automatic model arms are explicitly separate.
    empty=evaluate_relationships(units,mapped,[],[target_edge])
    accepted=evaluate_relationships(units,mapped,[target_edge],[target_edge])
    wrong=deepcopy(target_edge);wrong['scope']='long coupon only'
    counter=evaluate_relationships(units,mapped,[wrong],[target_edge])
    omitted=deepcopy(target_edge);omitted['from']=omitted['from'][:1]
    lost=evaluate_relationships(units,mapped,[omitted],[target_edge])
    assert accepted['status']=='PASS' and all(r['status']=='FAIL' for r in (empty,counter,lost))
    relations={'automatic':empty,'reviewed_input':accepted,'wrong_scope_control':counter,'omitted_margin_control':lost}
    save(folder/'relationships.json',relations)
    return {'status':'PASS','strict_missing_critical_lines':len(before),'projected_missing_critical_lines':len(after),
            'designated':len(target),'candidate_hyphen_deletions_accounted':sum(len(m['candidate_changes']) for r in repaired for m in r['mappings']),
            'relationships':relations,'decision':'SOURCE_PRESERVING_OPTIONAL_STRUCTURE_PASSES_DEVELOPMENT; AUTOMATIC_LEGAL_SCOPE_UNIMPLEMENTED',
            'attribution':'Upstream normalized text is unsuitable as exact quotation; local projection repair preserves original text',
            'default_promotion':False}


def authoring(folder):
    from scripts.prospectus_integration_authoring import execute
    return execute(folder)


def feasibility(folder):
    from legalmath.prospectus.successor.adoption_trials import coupon_cases
    from legalmath.prospectus.successor.fixed_coupon import year_fraction,adjusted
    from fractions import Fraction
    cases=coupon_cases()
    save(folder/'coupon-input.json',{'cases':cases,'calendar_dates':['2024-03-29','2024-05-01','2024-12-25']})
    command(folder,'quantlib',[str(ROOT/'.venv/bin/python'),'-m','scripts.prospectus_adoption_sidecar','coupon',
            '--input',str(folder/'coupon-input.json'),'--output',str(folder/'coupon')],90)
    actual=load(folder/'coupon/result.json')
    if actual.get('execution')!='EXECUTED' or len(actual['fractions'])!=len(cases):
        raise ValueError('Incomplete QuantLib comparison')
    for case,other in zip(cases,actual['fractions']):
        expected=Fraction(case['expected_exact'])
        local=year_fraction(case['start'],case['end'],case['convention'],references=case['references'],frequency=case['frequency'],eom=case['eom'])
        if case['id']!=other['id'] or local!=expected or abs(float(expected)-other['year_fraction'])>1e-12:
            raise ValueError('Financial comparator mismatch')
    try:
        year_fraction('2024-01-31','2024-08-31','ACT_ACT_ICMA',references=[],frequency=2,eom=True)
    except ValueError:
        missing_reference='REJECTED'
    else:raise ValueError('Missing reference schedule accepted')
    calendar={'edition':'TARGET explicit 2024 development list','valid_from':'2024-01-01',
        'valid_until':'2025-01-01','holidays':['2024-01-01','2024-03-29','2024-04-01','2024-05-01','2024-12-25','2024-12-26'],
        'weekend':[5,6],'coverage':'COMPLETE_DECLARED_INTERVAL'}
    independent_dates={'2024-03-29':('2024-04-02','2024-03-28'),
        '2024-05-01':('2024-05-02','2024-05-02'),'2024-12-25':('2024-12-27','2024-12-27')}
    if {r['input'] for r in actual['calendar']}!=set(independent_dates):
        raise ValueError('Missing calendar comparison')
    for row in actual['calendar']:
        for index,(kind,key) in enumerate((('FOLLOWING','following'),('MODIFIED_FOLLOWING','modified_following'))):
            if adjusted(row['input'],kind,calendar)!=row[key] or row[key]!=independent_dates[row['input']][index]:
                raise ValueError('Calendar adjustment mismatch')
    try:adjusted('2025-01-01','FOLLOWING',calendar)
    except ValueError:missing_calendar='REJECTED'
    else:raise ValueError('Out-of-edition calendar accepted')
    source=ROOT/'docs/research/prospectus-adoption-2026-10-07/sources'
    evidence={}
    for name in ('actus-service-build/source.txt','actus-service-readme-fixed/source.md',
                 'actus-core-terms/source.md','cdm-settlement/source.txt','cdm-bond-input/source.json'):
        path=source/name;evidence[str(path.relative_to(ROOT))]=sha(path)
    save(folder/'feasibility-source-hashes.json',evidence)
    from scripts.prospectus_tool_feasibility import refresh
    save(folder/'official-source-refresh.json',refresh())
    official=OUT/'official-sources'
    core=load(official/'actus-core-repository.json')
    distributions=load(official/'actus-distributions-tree.txt')
    architecture=(official/'actus-python-architecture.txt').read_text()
    python_readme=(official/'cdm-python-readme.txt').read_text()
    if core['http_status']!='404' or distributions['truncated'] or any(r['path']!='LICENSE' for r in distributions['tree']):
        raise ValueError('ACTUS availability changed; inspect the newly available core before deferral')
    if 'Backend Service Interfaces' not in architecture or 'NotImplementedError' not in python_readme:
        raise ValueError('Official capabilities changed; refresh feasibility analysis')
    decision={'ACTUS':{'runtime_test':'NOT_EXECUTED','requirement':'Generate event/payoff/state transitions from admitted bond terms',
        'source_findings':['Unauthenticated actusfrf/actus-core API returns 404; this does not prove nonexistence',
            'Official distributions tree b6116e8 contains LICENSE only',
            'Service build pins core 1.1.0/Java17; copied README names webapp/core 1.0.1, so README alone is not a version authority',
            'Official Awesome ACTUS architecture delegates event simulation to a local/remote backend',
            'Core License 1.0 sections 2.1-2.5 impose distinct distribution, conformance and use conditions; not generic Apache terms'],
        'remaining':['Obtain exact authorized core bytes and version-specific license through the project owner',
            'Audit PAM schedule/payoff/state code and official tests; then run isolated plain PAM before bond-specific overrides',
            'Admit currency, role, principal, rate, status/initial/maturity dates, day count, calendar, EOM and event-order inputs explicitly'],
        'smallest_runtime_trial':{'contract':'Synthetic fixed-rate principal-at-maturity; no optionality, fees or FX',
            'primary':'Every scheduled date, event type, payoff and post-event state equals independent exact enumeration',
            'veto':'Any implicit calendar/event default, missing payoff/state, or unidentified engine/version',
            'next_ladder':['regular coupon','short and long stubs','holiday/equal-time order','rate reset and early termination only after explicit terms']},
        'verdict':'ACCESS_AND_VERSION_PREREQUISITES_UNRESOLVED; NO_RUNTIME_PACKAGE_DEFECT_ESTABLISHED'},
        'FINOS_CDM':{'runtime_test':'NOT_EXECUTED','requirement':'Exchange a cash/security settlement trace with a receiving system',
        'source_revision':'65996cfa8defcd1f15eb457f9d2c50295b3e9691',
        'source_findings':['Official Python distribution supports generated types/functions and explicit validate_model/validate_conditions',
            'Python native Java function stubs raise NotImplementedError without registered replacements; LoadCodeList explicitly identified',
            'Python requires 3.11+, Pydantic>=2.10.3 and rune.runtime>=2,<3',
            'Inspected source POM enforces Java21 for build; existing INCEpTION Java17 is not a valid CDM source-build baseline'],
        'remaining':['Name receiving-system CDM version/profile and exact required functions',
            'Choose supported Java runtime or audit/implement each needed native Python function',
            'Map asset, currency, quantity, payer/receiver, settlement date and identifiers bidirectionally and validate actual runtime conditions'],
        'smallest_runtime_trial':{'example':'Retained official bond DvP fixture GB00B24FF097',
            'primary':'Deserialize, resolve references, explicitly validate conditions, serialize, and recover all semantic fields with selected receiver',
            'negative_controls':['missing asset/quantity/date','currency-unit mismatch','negative quantity','unresolved party reference','native-function sentinel'],
            'veto':'Silent defaults, dropped fields, unresolved references or any required native stub'},
        'verdict':'RECEIVER_REQUIREMENT_MISSING; DOCUMENTED_PYTHON_NATIVE_FUNCTION_GAP; LOCAL_RUNTIME_UNTESTED'}}
    save(folder/'deferred-tool-decisions.json',decision)
    return {'status':'PASS','quantlib_fractions':len(cases),'quantlib_adjusted_dates':6,
            'missing_reference':missing_reference,'out_of_edition_calendar':missing_calendar,
            'financial_verdict':'Known fixture error repaired; actual instrument input remains a separate obligation',
            'deferred':decision,'scope':'Usage and feasibility audit; ACTUS/CDM runtime capability untested'}


def analyze(folder):
    from scripts.prospectus_integration_repair import current, verify_outputs
    rows=[]
    for phase in ('preflight','check','layout','authoring','feasibility'):
        paths=sorted(OUT.glob(phase+'-*/manifest.json'))
        if not paths:raise ValueError('Missing phase: '+phase)
        path=paths[-1];receipt=load(path)
        verify_outputs(path,receipt)
        result=load(path.parent/'result.json') if (path.parent/'result.json').exists() else {'status':'FAILED'}
        rows.append({'phase':phase,'receipt':str(path.relative_to(ROOT)),'sha256':sha(path),
                     'current':current(phase)==path,'result':result})
    save(folder/'evidence.json',rows)
    if not all(r['result']['status']=='PASS' and r['current'] for r in rows):
        return {'status':'INCOMPLETE','phases':rows,'reason':'Failed or stale phase; attribution cannot be finalized'}
    by_phase={r['phase']:r for r in rows}
    author=ROOT/Path(by_phase['authoring']['receipt']).parent
    ops=load(author/'operations.json')
    required={'initial-reader-a','initial-reader-b','created-span','deleted-span','changed-boundary',
              'discontinuous-group','semantic-relation','peer-unchanged'}
    if {o['stage'] for o in ops}!=required or len(ops)!=8:raise ValueError('Incomplete actual authoring operations')
    for op in ops:
        command(folder,op['stage']+'-redecode',[str(SIDECAR),'-m','scripts.prospectus_integration_codec','decode',
            str(author/op['expected']),str(author/op['raw']),str(folder/(op['stage']+'-verified.json'))],30)
    access=load(author/'access.json')
    if len(access)!=4 or not all(r['denied'] for r in access):raise ValueError('Access denial evidence missing')
    if not load(author/'server-stop.json')['stopped']:raise ValueError('Server cleanup missing')
    layout=by_phase['layout']['result'];finance=by_phase['feasibility']['result']
    if layout['projected_missing_critical_lines'] or layout['designated']!=53 or finance['quantlib_adjusted_dates']!=6:
        raise ValueError('Primary results changed')
    decisions=[
        {'tool':'Docling source text','attribution':'UPSTREAM_NORMALIZATION_PLUS_LOCAL_ADAPTER_DESIGN',
         'primary':'53/53 retained with source projection; old strict map misses 14',
         'veto':'Candidate normalized quotations remain inadmissible; six original hyphens preserved',
         'uncertainty':'Two exposed digital pages, one pinned model; OCR/scans not evaluated',
         'alternative':'Candidate looks successful because raw source is reused; that is the declared design, not model extraction credit',
         'next':'Use optional structural projection with raw evidence and review; expand only under a new frozen criterion',
         'not_concluded':'Default replacement or general legal interpretation'},
        {'tool':'Margin scope','attribution':'LOCAL_CAPABILITY_AND_REVIEW_GAP',
         'primary':'Reviewed supplied edge passes; empty automatic, wrong-scope and omitted-margin controls fail',
         'veto':'No automatic governing edge established',
         'uncertainty':'One implementer-reviewed relation; no independent adjudication',
         'alternative':'A layout engine supplies geometry, which cannot alone decide the legal relation',
         'next':'Bind actual reviewed relations in scope; automatic model would need a distinct evaluation',
         'not_concluded':'Docling semantic capability was disproved'},
        {'tool':'INCEpTION / Cassis','attribution':'LOCAL_SCHEMA_API_AND_BROWSER_USAGE_ERRORS_REPAIRED',
         'primary':'8 exact exports, actual creation/deletion/reselection/group/relation and 4 access denials',
         'veto':'Wrong password rejected, peer unchanged, immutable source validation active',
         'uncertainty':'Synthetic users/development text; no genuine independent humans',
         'alternative':'DOM-only edits could mimic success; reloads and raw server-export redecoding rule out that explanation here',
         'next':'Use draft schema for real first readings with identity verification/adjudication',
         'not_concluded':'Human independence, legal correctness, direct-handle resizing or all GUI workflows'},
        {'tool':'QuantLib','attribution':'LOCAL_EXPECTED_FRACTION_ERROR_REPAIRED; INSTRUMENT_INPUTS_STILL_REQUIRED',
         'primary':'9 exact fractions and 6 exact adjusted dates agree',
         'veto':'Missing reference and out-of-edition calendar rejected',
         'uncertainty':'Development conventions; actual instrument calendar and entitlement not supplied',
         'alternative':'Agreement may share assumptions; explicit rational/date controls check the declared assumptions only',
         'next':'Admit source-backed instrument premises; retain optional comparator',
         'not_concluded':'Instrument-specific cashflows accepted'},
        {'tool':'ACTUS','attribution':'ACCESS_VERSION_AND_INPUT_PREREQUISITES; RUNTIME_UNTESTED',
         'primary':'Official access, distributions, build, architecture and license inspected',
         'veto':'No exact authorized core/runtime available in this program',
         'uncertainty':'404 is an unauthenticated observation; private access or alternative distribution may exist',
         'alternative':'Installing a Python client does not supply a local numerical backend',
         'next':finance['deferred']['ACTUS']['smallest_runtime_trial'],
         'not_concluded':'Fundamental numerical defect'},
        {'tool':'FINOS CDM','attribution':'RECEIVER_REQUIREMENTS_MISSING; DOCUMENTED_BINDING_LIMIT',
         'primary':'Concrete official settlement schema and runtime support matrix inspected',
         'veto':'Required native Python stubs would block that path; affected required functions not yet selected',
         'uncertainty':'No receiver/version profile and no local runtime trial',
         'alternative':'Java or a reviewed native Python replacement may satisfy a function unsupported in the binding',
         'next':finance['deferred']['FINOS_CDM']['smallest_runtime_trial'],
         'not_concluded':'Whole CDM package unsuitable'},
    ]
    save(folder/'attribution.json',decisions)
    save(folder/'inference-status.json',{'hard_veto_screen':'Named adversarial controls pass; automatic margin remains unsupported',
        'statistically_supported_ranking':'NONE; deterministic bounded correctness comparisons only',
        'descriptive_only':'Counts/timing; two-page development retention is not population accuracy',
        'default_readiness':'NOT_ESTABLISHED','next_evidence':'Independent heldout source interpretation and authentic reader records'})
    return {'status':'PASS',
            'phases':rows,'legal_acceptance':'PENDING','fundamental_package_unsuitability':'NOT_ESTABLISHED'}
