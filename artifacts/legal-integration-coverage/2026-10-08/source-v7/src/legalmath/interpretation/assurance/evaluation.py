"""Frozen four-arm evaluation; development fixtures cannot establish effectiveness."""
from copy import deepcopy
from math import log, sqrt
from math import isfinite
from pathlib import Path
from random import Random
from time import monotonic
from typing import Literal
from pydantic import Field
from ...canonical import canonical,digest,loads,raw_digest
from ...domain import timestamp
from ...errors import LegalMathError
from ...ir.typecheck import validate_snapshot
from ...ir.evaluate import evaluate
from ...storage import Database
from ..contracts import Strict,Id,Text,Hash,parse
from ..service import Interpretations
from ..search.models import Settings,Generation,Reading,generation_request,validate_generation
from ..search.alignment import discover,translate_snapshot
from ..search.formal import Comparisons,bundle,project
from ..search.engine import create_search
from .engine import Assurance,AssuranceSettings,SourceCheckedSearch,CONVENTION
from .journal import JournalProvider
from .sources import acquire_context,packet_from_context,official_url,extract_document,selection_ranges
from .semantics import check_quotes
from .monitor import save

ARMS=('single-reader','isolated-readers','search','assurance')


class Contract(Strict):
    version: Literal['paired-evaluation.v1']
    study_id: Id
    task: Literal['CONTROLLED_SEMANTIC_TESTS','LEGAL_OUTCOMES']
    call_cap: int = Field(ge=7,le=36)
    seconds_per_arm: int = Field(ge=30,le=3600)
    bytes_per_input: int = Field(ge=1000,le=200000)
    bytes_per_output: int = Field(ge=1000,le=200000)
    seed: int = Field(ge=0,le=2147483647)
    development_families: list[Id] = Field(max_length=1000)
    minimum_families: int = Field(ge=2,le=1000)
    iid_family_sampling_attested: bool
    confidence_error_ppm: int = Field(ge=1,le=100000)
    maximum_coverage_loss_ppm: int = Field(ge=0,le=100000)
    criterion_basis: Text


class PublicDocument(Strict):
    url: Text
    media_type: Literal['application/pdf','application/json','text/html','text/plain']
    raw_hex: str = Field(min_length=2,max_length=2000000)
    sha256: Hash
    selection: dict | None = None


class EvaluationCase(Strict):
    case_id: Id
    family_id: Id
    variant: Literal['CLEAN','ALTERED']
    roots: list[PublicDocument] = Field(min_length=1,max_length=20)
    selected_slice: Text
    at: Text
    reference: dict


def documents(case):
    result=[]
    for record in case['roots']:
        official_url(record['url'])
        try:data=bytes.fromhex(record['raw_hex'])
        except ValueError:raise LegalMathError('E_SCHEMA')
        if raw_digest(data)!=record['sha256']:raise LegalMathError('E_HASH_MISMATCH')
        doc={'url':record['url'],'media_type':record['media_type'],'data':data}
        if record.get('selection') is not None:
            doc['selection']=deepcopy(record['selection'])
            selection_ranges({**doc,**extract_document(doc)})
        result.append(doc)
    return result


def source_packet(case):
    # Same fixed source set for every arm; no hidden live retrieval advantage.
    context=acquire_context(documents(case),max_depth=0,max_documents=20)
    return packet_from_context(context,case['selected_slice'])


def output_identity(reading):
    # A shared polarity marker does not identify the legal question being answered.
    # Exact declarations permit a bounded comparison; semantic paraphrase alignment
    # needs separate evidence and must not be silently inferred by the scorer.
    return {'subject':reading['subject'],'statement':reading['statement']}


def reference_signatures(case,packet):
    """Check labels against explicit reference programs, never against English truth.

    Alternative accepted answers need their own executable witnesses with exactly
    comparable fact meanings. A bare additional label cannot enlarge the oracle.
    """
    reference=case['reference']
    required={'basis','evidence','binding_reading','snapshots','accepted','limitations'}
    if not required<=set(reference) or set(reference)-required-{'alternate_readings'}:
        raise LegalMathError('E_SCHEMA')
    check_quotes(reference['evidence'],packet)
    if (not reference['evidence'] or not reference['limitations']
            or not isinstance(reference['limitations'],list)
            or any(not isinstance(x,str) or not x.strip() for x in reference['limitations'])
            or not 1<=len(reference['snapshots'])<=64):
        raise LegalMathError('E_SCHEMA')
    readings=[reference['binding_reading'],*reference.get('alternate_readings',[])]
    if len(readings)>8:raise LegalMathError('E_RESOURCE_LIMIT')
    results=[]
    for reading in readings:
        reading=parse(Reading,reading);check_quotes(reading['citations'],packet)
        compiled=bundle(reading,packet,case['at'])
        mapping=discover(reference['binding_reading'],reading)['mapping']
        if mapping is None or output_identity(reading)!=output_identity(reference['binding_reading']):
            raise LegalMathError('E_REFERENCE',details='Reference alternatives have incompatible meanings')
        signature=[]
        for snapshot in reference['snapshots']:
            target=translate_snapshot(snapshot,mapping)
            if validate_snapshot(compiled,target):raise LegalMathError('E_SCHEMA',details='Invalid hidden scenario')
            result=evaluate(compiled,target,'selected.control',case['at'],case['at'])
            if result['status']=='ERROR':raise LegalMathError('E_REFERENCE',details='Reference program failed')
            signature.append(project(result))
        results.append(signature)
    # Canonical comparison preserves Boolean versus integer distinctions.
    accepted=reference['accepted']
    if (not isinstance(accepted,list) or not accepted
            or len({digest(s) for s in accepted})!=len(accepted)
            or {digest(s) for s in accepted}!={digest(s) for s in results}):
        raise LegalMathError('E_REFERENCE',details='Accepted answers differ from executable reference witnesses')
    return results


def prepare_study(contract,cases):
    contract=parse(Contract,contract);cases=[parse(EvaluationCase,c) for c in cases]
    # Preserve the v1 representation when no selected-document extension is used.
    for case in cases:
        for doc in case['roots']:
            if doc.get('selection') is None:doc.pop('selection',None)
    if not 1<=len(cases)<=1000 or len({c['case_id'] for c in cases})!=len(cases):raise LegalMathError('E_RESOURCE_LIMIT')
    families={c['family_id'] for c in cases}
    if any({c['variant'] for c in cases if c['family_id']==f}!={'CLEAN','ALTERED'} for f in families):
        raise LegalMathError('E_REFERENCE',details='Every family needs clean and altered controls')
    owners={}
    for case in cases:
        timestamp(case['at']);p=source_packet(case);reference=case['reference']
        for doc in case['roots']:
            # Shared sources cannot manufacture independent family replications.
            for identity in ('url:'+official_url(doc['url']),'sha256:'+doc['sha256']):
                if identity in owners and owners[identity]!=case['family_id']:
                    raise LegalMathError('E_REFERENCE',details='A source is split across evaluation families')
                owners[identity]=case['family_id']
        if reference['basis'] not in ('DEVELOPER_FIXTURE','SEEDED_TRANSFORMATION','PUBLIC_WORKED_EXAMPLE',
                                       'PUBLIC_QA_INTERPRETATION','RECORDED_ADJUDICATION'):
            raise LegalMathError('E_AUTHORITY')
        if contract['task']=='LEGAL_OUTCOMES' and reference['basis'] in ('DEVELOPER_FIXTURE','SEEDED_TRANSFORMATION','PUBLIC_QA_INTERPRETATION'):
            raise LegalMathError('E_AUTHORITY',details='A seeded edit cannot label complete legal correctness')
        reference_signatures(case,p)
        case['packet_hash']=digest(p)
    jobs=[{'case_id':c['case_id'],'arm':arm} for c in cases for arm in ARMS]
    Random(contract['seed']).shuffle(jobs)
    for i,job in enumerate(jobs):job['blind_id']='job.'+str(i)
    result={'contract':contract,'cases':cases,'jobs':jobs,'families':sorted(families),
            'heldout':not (families & set(contract['development_families'])),
            'required_call_reservation':len(jobs)*contract['call_cap']}
    return result


def freeze(contract,cases,directory):
    result=prepare_study(contract,cases)
    directory=Path(directory)
    if directory.exists():raise LegalMathError('E_IDEMPOTENCY')
    directory.mkdir(parents=True);save(directory/'study.json',result)
    save(directory/'manifest.json',{'study_hash':digest(result),'files':{'study.json':raw_digest((directory/'study.json').read_bytes())}})
    return result


def load_frozen(directory):
    directory=Path(directory);manifest=loads((directory/'manifest.json').read_bytes())
    if manifest['files']!={'study.json':raw_digest((directory/'study.json').read_bytes())}:raise LegalMathError('E_INTEGRITY')
    value=loads((directory/'study.json').read_bytes())
    if digest(value)!=manifest['study_hash']:raise LegalMathError('E_INTEGRITY')
    try:
        cases=[{k:v for k,v in c.items() if k!='packet_hash'} for c in value['cases']]
        checked=prepare_study(value['contract'],cases)
        if canonical(checked)!=canonical(value):raise LegalMathError('E_INTEGRITY')
    except (KeyError,TypeError,ValueError) as exc:
        raise LegalMathError('E_INTEGRITY',details='Frozen study structure or derived fields changed') from exc
    return value


def admit(study,available_calls):
    if type(available_calls)is not int or available_calls<0:raise LegalMathError('E_SCHEMA')
    needed=study['required_call_reservation']
    return {'status':'ADMITTED' if available_calls>=needed else 'UNDER_BUDGETED',
            'required_calls':needed,'available_calls':available_calls,'study_hash':digest(study),
            'legal_accuracy_evaluated':False}


def run_method(arm,public,provider,directory,jdk,contract):
    """Only the public task crosses the dispatch boundary; hidden references do not."""
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=False)
    settings=Settings(max_model_calls=contract['call_cap'],max_rounds=1,max_output_repairs=0,
        max_input_bytes=contract['bytes_per_input'],max_output_bytes=contract['bytes_per_output'],
        timeout_seconds=min(300,contract['seconds_per_arm']),deadline_seconds=contract['seconds_per_arm'],max_comparisons=4)
    packet=source_packet(public);checker=Comparisons(directory/'java',jdk,public['at'])
    if arm=='assurance':
        config=AssuranceSettings(total_model_calls=contract['call_cap'],output_repairs=0,
            deadline_seconds=contract['seconds_per_arm'],max_context_passes=1,max_reference_depth=0,
            max_derived_comparisons=0,search=settings.model_copy(update={'max_model_calls':3,'reconstruction_required':False}))
        engine=Assurance(directory/'assurance',provider,jdk,public['at'],config)
        report=engine.drive(documents(public),public['selected_slice'])
        path=directory/'assurance/candidates.json'
        readings=list(loads(path.read_bytes()).values()) if path.exists() else []
        status='FAILED' if not report['execution_complete'] else 'ABSTAIN' if report['findings'] else 'CANDIDATES'
        return {'status':status,'readings':readings,'calls':report['model_calls'],
                'source_packet_hash':report.get('source_packet_hash'),'report':report}
    journal=JournalProvider(provider,directory/'calls',maximum=contract['call_cap'],deadline_seconds=contract['seconds_per_arm'])
    if arm in ('single-reader','isolated-readers'):
        readings=[]
        roles=('normative',) if arm=='single-reader' else ('normative','controlled-language','alternatives')
        for role in roles:
            request=generation_request(packet,role);request['instructions']+=CONVENTION
            value=journal.complete(request,Generation.model_json_schema(),settings)
            readings.extend(validate_generation(value.value,packet)['readings'])
        return {'status':'CANDIDATES','readings':readings,'calls':journal.calls,'source_packet_hash':digest(packet)}
    if arm!='search':raise LegalMathError('E_SCHEMA')
    service=Interpretations(Database(directory/'work'))
    service.lc.register({'evaluation.author':{'token':'evaluation.fixture','roles':['author']}})
    # Same source intake as assurance; packet spans are checked by the service.
    from ...sources.intake import import_source
    from .sources import extract_document
    with service.db.transaction() as con:
        for doc in documents(public):
            e=extract_document(doc)
            import_source(service.db,con,'d'+digest(doc['url'])[:12],doc['data'],doc['media_type'],doc['url'],public['at'],
                          retained_text=e['text'],extractor=e['primary_method'],authority='RETAINED_PUBLIC_SOURCE')
    run=create_search(service,'evaluation.author','evaluation.start',packet,settings)
    engine=SourceCheckedSearch(service,'evaluation.author',run['run_id'],journal,checker,source_claims=[],source_findings=[])
    report=engine.drive();save(directory/'search-report.json',report);save(directory/'search-state.json',engine.state)
    readings=[n['reading'] for n in engine.state['nodes']]+[n['reading'] for n in engine.state['frontier']]
    return {'status':'FAILED' if report['status']=='FAILED_INTEGRITY' else 'CANDIDATES',
            'readings':readings,'calls':journal.calls,'source_packet_hash':digest(packet),'report':report}


def score(result,case,checker):
    if result['status']!='CANDIDATES' or not result['readings']:
        return {'status':'MISSING' if result['status']=='FAILED' else 'ABSTAIN','signature':None}
    reference=case['reference'];p=source_packet(case);signatures=[]
    for reading in result['readings']:
        if reading['formalization'] is None:return {'status':'ABSTAIN','signature':None,'reason':'UNSUPPORTED_READING'}
        mapping=discover(reference['binding_reading'],reading)['mapping']
        if mapping is None:return {'status':'ABSTAIN','signature':None,'reason':'REFERENCE_FACT_BINDINGS_UNALIGNED'}
        if output_identity(reading)!=output_identity(reference['binding_reading']):
            return {'status':'ABSTAIN','signature':None,'reason':'OUTPUT_MEANING_UNALIGNED'}
        b=bundle(reading,p,case['at']);values=[]
        for snapshot in reference['snapshots']:
            replay=checker.replay([b],translate_snapshot(snapshot,mapping))[0]
            if replay['java']['status']=='ERROR':return {'status':'MISSING','signature':None,'reason':'EXECUTION_ERROR'}
            values.append(project(replay['java']))
        signatures.append(values)
    if len({digest(s) for s in signatures})!=1:return {'status':'ABSTAIN','signature':None,'reason':'COMPETING_EXECUTABLE_OUTCOMES'}
    return {'status':'ACCEPTED','signature':signatures[0],
            'meaning':'Agreement on finite hidden scenarios; evaluation disposition only, never bank release'}


def summarize(study,results,*,live):
    expected={(j['case_id'],j['arm']) for j in study['jobs']}
    observed={(r['case_id'],r['arm']) for r in results}
    if expected!=observed or len(results)!=len(expected):raise LegalMathError('E_REFERENCE',details='Missing or repeated arm/case')
    cases={c['case_id']:c for c in study['cases']};contract=study['contract'];counts={};family={};veto=[]
    for arm in ARMS:counts[arm]={'unsafe_accepted':0,'correct_accepted':0,'abstain':0,'missing':0};family[arm]={}
    for row in results:
        case=cases[row['case_id']];arm=row['arm'];outcome=row['outcome']
        if (row['packet_hash']!=case['packet_hash'] or row['budget']!=contract['call_cap']
                or type(row['calls'])is not int or not 0<=row['calls']<=row['budget']):
            raise LegalMathError('E_INTEGRITY',details='Source/resource parity failed')
        elapsed=float(row.get('wall_seconds','0'))
        if not isfinite(elapsed) or elapsed<0:raise LegalMathError('E_INTEGRITY',details='Invalid elapsed time')
        if elapsed>contract['seconds_per_arm']:
            veto.append('ARM_TIME_LIMIT:'+row['case_id']+'/'+arm)
        status=outcome['status']
        if status not in ('ACCEPTED','ABSTAIN','MISSING'):raise LegalMathError('E_SCHEMA')
        unsafe=status=='ACCEPTED' and digest(outcome['signature']) not in {digest(s) for s in case['reference']['accepted']}
        correct=status=='ACCEPTED' and not unsafe
        counts[arm]['unsafe_accepted' if unsafe else 'correct_accepted' if correct else status.lower()]+=1
        family[arm].setdefault(case['family_id'],[]).append({'unsafe':int(unsafe),'coverage':int(correct)})
        if status=='MISSING':veto.append('MISSING_EXECUTION:'+row['case_id']+'/'+arm)
    n=len(study['families']);alpha=contract['confidence_error_ppm']/1000000
    # Six simultaneous bounds: unsafe and coverage for three paired contrasts.
    radius=sqrt(2*log(12/alpha)/n)
    comparisons=[]
    for arm in ARMS[1:]:
        stats={}
        for metric in ('unsafe','coverage'):
            differences=[]
            for f in study['families']:
                avg=lambda a:sum(x[metric] for x in family[a][f])/len(family[a][f])
                differences.append(avg(arm)-avg(ARMS[0]))
            mean=sum(differences)/n
            stats[metric]={'mean_difference':str(mean),'lower':str(max(-1.,mean-radius)),
                           'upper':str(min(1.,mean+radius)),'unit':'paired circular-family mean'}
        supported=(float(stats['unsafe']['upper'])<0 and
                   float(stats['coverage']['lower'])>=-contract['maximum_coverage_loss_ppm']/1000000)
        comparisons.append({'arm':arm,'baseline':ARMS[0],'metrics':stats,'joint_criterion_passed':supported})
    if not study['heldout']:veto.append('DEVELOPMENT_FAMILY_OVERLAP')
    if not live:veto.append('SCRIPTED_FIXTURE_NOT_LIVE_EVIDENCE')
    if n<contract['minimum_families']:veto.append('INSUFFICIENT_FAMILY_REPLICATION')
    if not contract['iid_family_sampling_attested']:veto.append('INDEPENDENT_FAMILY_SAMPLING_NOT_ESTABLISHED')
    if any(c['reference']['basis']=='DEVELOPER_FIXTURE' for c in cases.values()):veto.append('DEVELOPER_REFERENCE_ONLY')
    if any(c['reference']['basis']=='PUBLIC_QA_INTERPRETATION' for c in cases.values()):
        veto.append('PUBLIC_QA_TRANSLATION_NOT_INDEPENDENTLY_VERIFIED')
    return {'counts':counts,'families':n,'comparisons':comparisons,'promotion_vetoes':veto,
        'ranking_supported':not veto and any(c['joint_criterion_passed'] for c in comparisons),
        'legal_accuracy_evaluated':False,'evaluated_target':contract['task'],
        'reference_semantics_independently_verified':False,
        'interval_method':'Simultaneous Hoeffding bounds for IID bounded family differences; invalid as population inference without the declared sampling assumption',
        'interval_derivation':'For Xi in [-1,1], P(|mean-Emean|>=r)<=2 exp(-n r^2/2); union over six metrics sets r=sqrt(2 log(12/alpha)/n).',
        'review_cost_saving_measured':False,'release_eligible':False}


def execute_study(frozen,out,provider,jdk,*,available_calls):
    study=load_frozen(frozen);out=Path(out)
    if out.exists():raise LegalMathError('E_IDEMPOTENCY')
    out.mkdir(parents=True)
    if provider.live:
        allowance=getattr(provider,'allowance',None)
        if allowance is None:raise LegalMathError('E_AUTHORITY')
        ledger=loads(allowance.path.read_bytes())
        actual=min(allowance.maximum,allowance.reservation_ceiling)-len(ledger['calls'])
        available_calls=min(available_calls,actual)
    admission=admit(study,available_calls);save(out/'admission.json',admission)
    if admission['status']!='ADMITTED':return admission
    results=[];cases={c['case_id']:c for c in study['cases']};contract=study['contract']
    for job in study['jobs']:
        case=cases[job['case_id']];directory=out/job['blind_id']
        public={k:deepcopy(case[k]) for k in ('roots','selected_slice','at')}
        # Persist assignment before dispatch, retain failures without dropping pairs.
        save(out/(job['blind_id']+'-reservation.json'),{'job':job,'public_input_hash':digest(public)})
        began=monotonic()
        try:
            result=run_method(job['arm'],public,provider,directory,jdk,contract)
            if result['source_packet_hash']!=case['packet_hash']:raise LegalMathError('E_INTEGRITY')
            save(directory/'method-result.json',result)
            outcome=score(result,case,Comparisons(directory/'scoring-java',jdk,case['at']))
            calls=result['calls']
        except Exception as exc:
            calls=len(list(directory.glob('**/call-*/status.json')))
            result={'status':'FAILED','error':getattr(exc,'code',type(exc).__name__),'details':str(exc)[:500]}
            outcome={'status':'MISSING','signature':None};save(directory/'failure.json',result)
        row={**job,'packet_hash':case['packet_hash'],'budget':contract['call_cap'],'calls':calls,
             'wall_seconds':str(monotonic()-began),
             'outcome':outcome,'method_result_hash':digest(result)}
        save(out/(job['blind_id']+'-scored.json'),row);results.append(row)
    summary=summarize(study,results,live=provider.live);save(out/'results.json',results);save(out/'summary.json',summary)
    save(out/'manifest.json',{'study_hash':digest(study),'files':{str(p.relative_to(out)):raw_digest(p.read_bytes())
        for p in sorted(out.rglob('*')) if p.is_file() and '/work/' not in str(p)}})
    return summary


def execute_cli(args):
    from .cli import ReplayProvider
    from ..search.providers import Allowance,CodexProvider
    study=load_frozen(args.frozen)
    if args.replay_responses:
        provider=ReplayProvider(args.replay_responses);available=study['required_call_reservation']
    else:
        if not args.allowance:raise LegalMathError('E_AUTHORITY')
        ledger=loads(Path(args.allowance).read_bytes())
        if ledger['maximum']!=args.total_calls:raise LegalMathError('E_INTEGRITY')
        available=args.total_calls-len(ledger['calls'])
        # Admission happens before provider initialization or any model dispatch.
        if admit(study,available)['status']!='ADMITTED':
            out=Path(args.out)
            if out.exists():raise LegalMathError('E_IDEMPOTENCY')
            out.mkdir(parents=True);result=admit(study,available);save(out/'admission.json',result);return result
        provider=CodexProvider(allowance=Allowance(args.allowance,args.total_calls))
    return execute_study(args.frozen,args.out,provider,args.jdk,available_calls=available)
