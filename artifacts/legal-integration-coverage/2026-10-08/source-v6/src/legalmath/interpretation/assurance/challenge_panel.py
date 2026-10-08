"""Blind breadth, bounded discrepancy follow-up, and mechanically distinct checks."""
from copy import deepcopy
import inspect
from pathlib import Path

from ...canonical import canonical, digest, loads, raw_digest
from ...errors import LegalMathError
from ..search.models import Settings
from . import challenge_contract as contract, conditional_elimination as logic, source_references, challenge_proof
from .diversity import save
from .issue_limits import IssueLimits
from .workflow import EvidenceJournal

ROLES = ('structure-reader','exception-challenger')
PROFILE = 'legalmath.challenge-panel.v1'


def provider_identity(provider):
    filename=inspect.getsourcefile(type(provider))
    allowance=getattr(provider,'allowance',None)
    return {'provider_id':provider.provider_id,'class':type(provider).__module__+'.'+type(provider).__qualname__,
        'implementation_sha256':raw_digest(Path(filename).read_bytes()) if filename else None,
        'route':deepcopy(getattr(provider,'routing',None)), 'live':getattr(provider,'live',True) is not False,
        'grant_sha256':raw_digest(allowance.grant_bytes) if getattr(allowance,'grant_bytes',None) else None,
        'ledger':str(allowance.path.resolve()) if allowance else None,
        'arm':str(allowance.slice_path.resolve()) if hasattr(allowance,'slice_path') else None,
        'remote_execution_attested':False}


def configuration(providers, *, batch_size=12, rounds=3, input_profile='readable-tables.v1', maximum_actions=96):
    if (set(providers)!=set(ROLES) or type(batch_size)is not int or not 1<=batch_size<=128 or
            type(rounds)is not int or not 1<=rounds<=3 or type(maximum_actions)is not int or
            not 2<=maximum_actions<=500 or input_profile not in ('literal','readable-tables.v1','readable-challenges.v1')):
        raise LegalMathError('E_SCHEMA')
    identities={role:provider_identity(p) for role,p in providers.items()}
    live=[p for p in identities.values() if p['live']]
    if live and (any(not p['grant_sha256'] or not p['ledger'] for p in live) or
                 len({(p['grant_sha256'],p['ledger'],p['arm']) for p in live})!=1):
        raise LegalMathError('E_AUTHORITY',details='Live challenge readers must share the original grant and fixed arm')
    return {'profile':PROFILE,'providers':identities,'batch_size':batch_size,'rounds':rounds,
        'input_profile':input_profile,'maximum_actions':maximum_actions,
        'maximum_attempts_per_obligation_role':3,'deadline_seconds':86400,
        'response_policy':'Blind first round; same prior round for both roles; no automatic legal elimination'}


def method_dependencies(config):
    routes={digest(p['route']) for p in config['providers'].values()}
    return {'mechanisms':[
        {'id':'literal-source-cues.v1','kind':'DETERMINISTIC_LEXICAL','shared_dependencies':['source_packet']},
        {'id':logic.PROFILE,'kind':'INDEPENDENT_TOTAL_BOOLEAN_ENUMERATION','shared_dependencies':['source_packet','formal_vocabulary','proposed_obligations']},
        *[{'id':role,'kind':'LANGUAGE_MODEL_PROPOSAL','provider':value,
           'shared_dependencies':['source_packet','question','candidate_vocabulary','possibly_shared_model_training']}
          for role,value in config['providers'].items()]],
        'distinct_configured_routes':len(routes), 'distinct_model_families_established':False,
        'statistical_independence_established':False,
        'additional_model_family':'NOT_ESTABLISHED' if len(routes)>1 else 'UNAVAILABLE_IN_THIS_CONFIGURED_PANEL'}


def premises(bound,packet,candidates,history):
    result={cid:deepcopy(bound['formal_obligations'].get(cid,[])) for cid in candidates}
    for row in [*bound.get('initial_evidence',[]),*history]:
        if row['status']!='VALIDATED':continue
        for proposal in row['value']['proposed_formal_premises']:
            cid=proposal['candidate_id']
            if cid not in result:raise LegalMathError('E_REFERENCE')
            obligation={k:deepcopy(proposal[k]) for k in ('question_hash','when','expected','evidence','rationale')}
            obligation.update(obligation_id='proposed.'+digest(proposal),packet_hash=digest(packet),
                              premise_status='PROPOSED_FORMAL_PREMISE')
            if obligation not in result[cid]:result[cid].append(obligation)
    return result


def mechanical_checks(bound,packet,candidates,questions,history):
    proposed=premises(bound,packet,candidates,history)
    return {cid:logic.check(packet,r,questions[cid],proposed[cid]) for cid,r in candidates.items()}


def investigation_request(bound,packet,candidates,questions,selected,role,round_no,prior):
    if bound.get('initial_evidence'):
        prior=[*bound['initial_evidence'],*(prior or [])]
    request=contract.request(bound['contract'],packet,candidates,questions,selected,role,prior=prior)
    request['round']=round_no
    request['independent_formal_checks']=mechanical_checks(bound,packet,candidates,questions,prior or [])
    request['declared_grammar_alternatives']={}
    for cid,reading in candidates.items():
        formal=reading.get('formalization')
        if formal and all(f['type']=='bool' for f in formal['facts']):
            try:request['declared_grammar_alternatives'][cid]=logic.enumerate_grammar([f['name'] for f in formal['facts']])
            except LegalMathError:pass  # The certificate retains the unsupported domain.
    request['instructions']+=' Inspect the actual independent_formal_checks and their assignments. A witness rejects '
    request['instructions']+='only the candidate under its stated proposed formal premise; challenge a mistaken premise '
    request['instructions']+='explicitly. The declared_grammar_alternatives expose a finite syntax search, not all legal '
    request['instructions']+='readings. Propose a relevant alternative when its stated vocabulary helps, and retain missing abstractions.'
    return request


def summarize(bound, packet, candidates, questions, history, formal):
    original=contract.build(packet,candidates,questions)
    if bound['contract']!=original: raise LegalMathError('E_STALE_REVIEW')
    expected=[o['obligation_id'] for o in original['obligations']]
    latest={role:{} for role in ROLES}; alternatives=[]; concerns=[]; failed=[]; seen=set()
    for row in history:
        key=(row['round'],row['role'],row['batch'])
        if key in seen or row['role'] not in ROLES: raise LegalMathError('E_DUPLICATE_ID')
        seen.add(key)
        if row['status']!='VALIDATED':
            failed.append({k:row[k] for k in ('round','role','selected','error')});continue
        value=contract.validate_response(row['value'],original,packet,row['selected'])
        for answer in value['answers']: latest[row['role']][answer['obligation_id']]=answer
        alternatives.extend({'round':row['round'],'role':row['role'],'reading':r} for r in value['alternative_readings'])
        concerns.extend({'round':row['round'],'role':row['role'],'concern':c} for c in value['unrepresented_concerns'])
    missing=[]; unresolved=[]; differences=[]
    for oid in expected:
        rows=[latest[role].get(oid) for role in ROLES]
        absent=[role for role in ROLES if oid not in latest[role]]
        if absent: missing.append({'obligation_id':oid,'roles':absent})
        if any(row is None or row['status']!='PROPOSED_SUPPORTED' or row['followup_question'] for row in rows):
            unresolved.append(oid)
        if all(rows) and canonical(rows[0])!=canonical(rows[1]):
            differences.append({'obligation_id':oid,
                'kind':'STATUS_DIFFERENCE' if rows[0]['status']!=rows[1]['status'] else 'EXPLANATION_DIFFERENCE_UNADJUDICATED',
                'responses':rows})
    qualifications=[]; grammars=[]
    if set(formal)!=set(candidates): raise LegalMathError('E_REFERENCE')
    proposed=premises(bound,packet,candidates,history)
    for cid,reading in candidates.items():
        obligations=proposed[cid]
        certificate=logic.verify(formal[cid],packet,reading,questions[cid],obligations)
        qualifications.append({'candidate_id':cid,'certificate':certificate})
        f=reading['formalization']
        if f and all(x['type']=='bool' for x in f['facts']) and 1<=len(f['facts'])<=8:
            try: grammars.append({'candidate_id':cid,'enumeration':logic.enumerate_grammar([x['name'] for x in f['facts']])})
            except LegalMathError as exc: grammars.append({'candidate_id':cid,'unsupported':exc.code})
    required=sorted(set(unresolved)|{d['obligation_id'] for d in differences})
    if alternatives or concerns: required=expected[:]
    if any(q['certificate']['status']=='CONDITIONALLY_REJECTED' for q in qualifications):required=expected[:]
    return {'profile':PROFILE,'binding_hash':digest(bound),'contract':original,'history':deepcopy(history),
        'latest':latest,'missing_perspectives':missing,'unresolved_obligation_ids':unresolved,
        'response_differences':differences,'followup_obligation_ids':required,
        'alternative_readings':alternatives,'unrepresented_concerns':concerns,'failed_actions':failed,
        'formal_checks':qualifications,'finite_grammars':grammars,'methods':method_dependencies(bound['configuration']),
        'execution_complete':not missing and not failed and not alternatives,
        'legal_correctness':'NOT_ESTABLISHED','cross_batch_semantic_consistency':'NOT_ESTABLISHED',
        'legal_candidates_removed':[],'retained_candidate_ids':list(candidates),'release_eligible':False}


def run(packet,candidates,questions,providers,directory,*,batch_size=12,rounds=3,input_profile='readable-tables.v1',
        maximum_actions=96,formal_obligations=None,issue_directory=None,inherited_issues=None,pilot_guard=False,initial_evidence=None):
    config=configuration(providers,batch_size=batch_size,rounds=rounds,input_profile=input_profile,maximum_actions=maximum_actions)
    formal_obligations=formal_obligations or {}
    if not set(formal_obligations)<=set(candidates): raise LegalMathError('E_REFERENCE')
    original=contract.build(packet,candidates,questions)
    bound={'configuration':config,'contract':original,'formal_obligations':formal_obligations}
    if inherited_issues is not None: bound['inherited_issues']=deepcopy(inherited_issues)
    if initial_evidence: bound['initial_evidence']=deepcopy(initial_evidence)
    if pilot_guard: bound['pilot_guard']=True
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    binding_path=directory/'binding.json'
    if binding_path.exists() and loads(binding_path.read_bytes())!=bound: raise LegalMathError('E_STALE_REVIEW')
    save(binding_path,bound)
    proof=challenge_proof.kernel(directory/'kernel')
    if (directory/'result.json').exists() and 'rounds_executed' in loads((directory/'result.json').read_bytes()):
        return verify(directory,packet,candidates,questions,expected_configuration=config)
    journal=EvidenceJournal(directory/'actions',bound,maximum_actions=maximum_actions,maximum_per_issue=3,deadline_seconds=86400)
    issue_root=Path(issue_directory) if issue_directory else directory/'issues'
    issues={role:IssueLimits(issue_root/(digest([digest(packet),role])+'.json'),
              {'source_packet_hash':digest(packet),'role':role,'profile':PROFILE},
              inherited=(inherited_issues or {}).get(role)) for role in ROLES}
    settings=Settings(timeout_seconds=300,max_input_bytes=200000,max_output_bytes=200000)
    formal=mechanical_checks(bound,packet,candidates,questions,[])
    save(directory/'formal-checks.json',formal)
    history=loads((directory/'history.json').read_bytes()) if (directory/'history.json').exists() else []
    selected=[o['obligation_id'] for o in original['obligations']]; prior=None
    pilot_failed=False
    for round_no in range(1,rounds+1):
        groups=[selected[i:i+batch_size] for i in range(0,len(selected),batch_size)]
        for index,group in enumerate(groups):
            for role in ROLES:
                if any(r['round']==round_no and r['batch']==index and r['role']==role for r in history):
                    continue
                if pilot_guard and len(history)==2 and any(r['status']!='VALIDATED' for r in history):
                    pilot_failed=True
                    break
                request=investigation_request(bound,packet,candidates,questions,group,role,round_no,prior)
                schema=contract.ChallengeResponse.model_json_schema()
                schema['properties']['answers'].update(minItems=len(group),maxItems=len(group))
                schema['$defs']['ChallengeAnswer']['properties']['obligation_id']['enum']=group
                def dispatch(work):
                    reservation=issues[role].reserve(group,digest(request));save(work/'reservation.json',reservation)
                    answer=source_references.complete(providers[role],request,schema,settings,work/'transport',input_profile=input_profile)
                    try:
                        validated=contract.validate_response(answer.value,original,packet,group)
                    except LegalMathError as exc:
                        if exc.code=='E_STALE_REVIEW':
                            raise LegalMathError('E_REFERENCE',details='Model response does not match original challenge identity') from exc
                        raise
                    return {'value':validated,'provenance':answer.provenance}
                row={'round':round_no,'role':role,'batch':index,'selected':group}
                try:
                    value,ref=journal.execute('challenge',{'request':request,'schema':schema},dispatch,
                                              issue=role+'.'+digest(group))
                    row.update(status='VALIDATED',value=value['value'],action_sequence=ref['sequence'])
                except LegalMathError as exc:
                    if exc.code in ('E_INTEGRITY','E_AUTHORITY','E_STALE_REVIEW'): raise
                    matching=[a for a in journal.report()['actions'] if a['spec']['inputs'].get('request')==request]
                    row.update(status='FAILED',error=exc.code,details=str(exc.details)[:2000],
                               action_sequence=matching[-1]['sequence'] if matching else None)
                history.append(row)
                save(directory/'history.json',history)
            if pilot_failed: break
        previous=[r for r in history if r['round']<=round_no]
        formal=mechanical_checks(bound,packet,candidates,questions,previous)
        save(directory/'formal-checks.json',formal)
        summary=summarize(bound,packet,candidates,questions,previous,formal)
        save(directory/'result.json',summary)
        selected=summary['followup_obligation_ids']
        if not selected or pilot_failed: break
        # Shared snapshot of the whole preceding round, never the peer's current response.
        prior=deepcopy(previous)
    summary=summarize(bound,packet,candidates,questions,history,formal)
    summary['rounds_executed']=round_no
    summary['followup_limit_reached']=bool(summary['followup_obligation_ids'] and round_no==rounds)
    summary['journal_actions']=journal.report()['consumed_actions']
    summary['issue_histories']={role:limits.report() for role,limits in issues.items()}
    summary['kernel']=proof
    if pilot_guard: summary['pilot_stopped']=pilot_failed
    save(directory/'result.json',summary)
    return summary


def verify(directory,packet,candidates,questions,*,expected_configuration=None):
    directory=Path(directory);bound=loads((directory/'binding.json').read_bytes())
    if expected_configuration is not None and bound['configuration']!=expected_configuration:
        raise LegalMathError('E_STALE_REVIEW')
    c=bound['configuration']
    journal=EvidenceJournal(directory/'actions',bound,maximum_actions=c['maximum_actions'],maximum_per_issue=3,deadline_seconds=86400)
    actions=journal.report()  # Recheck every actual retained response and transport artifact.
    history=loads((directory/'history.json').read_bytes());formal=loads((directory/'formal-checks.json').read_bytes())
    used=set()
    for row in history:
        prior=[r for r in history if r['round']<row['round']] if row['round']>1 else None
        request=investigation_request(bound,packet,candidates,questions,row['selected'],row['role'],row['round'],prior)
        index=row['action_sequence']
        if index is None:
            if row['status']!='FAILED' or row['error']!='E_RESOURCE_LIMIT' or not (
                    actions['remaining_actions']==0 or actions['deadline_exhausted']):
                raise LegalMathError('E_INTEGRITY',details='Unattributed challenge failure')
            continue
        if type(index)is not int or not 0<=index<len(actions['actions']):raise LegalMathError('E_INTEGRITY')
        action=actions['actions'][index]
        if index in used:raise LegalMathError('E_INTEGRITY',details='Challenge action counted twice')
        used.add(index)
        if action['spec']['inputs']['request']!=request:raise LegalMathError('E_INTEGRITY',details='Response does not belong to this original challenge')
        if row['status']=='VALIDATED':
            if action['status']!='EXECUTED':raise LegalMathError('E_INTEGRITY')
            actual=loads((journal.directory/action['result_file']).read_bytes())
            if actual['value']!=row['value']:raise LegalMathError('E_INTEGRITY',details='Summary replaced actual model response')
        elif action['status'] not in ('FAILED','INTERRUPTED'):raise LegalMathError('E_INTEGRITY')
    result=loads((directory/'result.json').read_bytes())
    # A summary cannot hide an executed or failed action by deleting its row.
    if used!=set(range(len(actions['actions']))):raise LegalMathError('E_INTEGRITY',details='Challenge history omitted a spent action')
    if (type(result.get('rounds_executed')) is not int or not 1<=result['rounds_executed']<=c['rounds'] or
        any(type(r['round']) is not int or not 1<=r['round']<=result['rounds_executed'] for r in history) or
        result['journal_actions']!=actions['consumed_actions']):raise LegalMathError('E_INTEGRITY')
    if result.get('kernel')!=challenge_proof.verify(directory/'kernel'):raise LegalMathError('E_INTEGRITY')
    expected=summarize(bound,packet,candidates,questions,history,formal)
    for key,value in expected.items():
        if result.get(key)!=value: raise LegalMathError('E_INTEGRITY',details='Challenge summary does not replay: '+key)
    return result


def recover_partial(directory,packet,candidates,questions):
    """Rebuild an interrupted report from recorded actions without dispatch."""
    directory=Path(directory);bound=loads((directory/'binding.json').read_bytes())
    c=bound['configuration']
    if c['rounds']!=1:raise LegalMathError('E_UNSUPPORTED_PROFILE')
    journal=EvidenceJournal(directory/'actions',bound,maximum_actions=c['maximum_actions'],maximum_per_issue=3,deadline_seconds=86400)
    actions=journal.report()
    history=loads((directory/'history.json').read_bytes())
    used={r['action_sequence'] for r in history if r['action_sequence'] is not None}
    expected=[o['obligation_id'] for o in bound['contract']['obligations']]
    groups=[expected[i:i+c['batch_size']] for i in range(0,len(expected),c['batch_size'])]
    for action in actions['actions']:
        if action['sequence'] in used:continue
        if action['status'] not in ('FAILED','INTERRUPTED'):
            raise LegalMathError('E_INTEGRITY',details='Unreported action is not a recorded failure')
        req=action['spec']['inputs']['request']
        if req['round']!=1 or req['selected_obligation_ids'] not in groups:raise LegalMathError('E_INTEGRITY')
        history.append({'round':1,'role':req['role'],'batch':groups.index(req['selected_obligation_ids']),
            'selected':req['selected_obligation_ids'],'status':'FAILED','error':action['error'],
            'details':action.get('details'),'action_sequence':action['sequence']})
    formal=mechanical_checks(bound,packet,candidates,questions,history)
    summary=summarize(bound,packet,candidates,questions,history,formal)
    summary.update(rounds_executed=1,followup_limit_reached=bool(summary['followup_obligation_ids']),
        journal_actions=actions['consumed_actions'],kernel=challenge_proof.verify(directory/'kernel'))
    summary['issue_histories']={role:IssueLimits(directory/'issues'/(digest([digest(packet),role])+'.json'),
        {'source_packet_hash':digest(packet),'role':role,'profile':PROFILE},
        inherited=bound.get('inherited_issues',{}).get(role)).report() for role in ROLES}
    if bound.get('pilot_guard'):summary['pilot_stopped']=len(history)>=2 and any(r['status']!='VALIDATED' for r in history[:2])
    save(directory/'history.json',history);save(directory/'formal-checks.json',formal);save(directory/'result.json',summary)
    return verify(directory,packet,candidates,questions)
