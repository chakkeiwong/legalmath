"""Continue the challenge stage while retaining the original complete investigation."""
from copy import deepcopy
from pathlib import Path
from ...canonical import canonical, digest, loads
from ...errors import LegalMathError
from . import challenge_panel as panel, challenge_contract, source_references, readable_challenges
from .diversity import save
from .integration_contract import read_evidence, evidence_file
from .issue_limits import IssueLimits

PROFILE = 'complete-investigation-challenge-continuation.v1'


def inherited(root, previous, refs=None):
    packet = read_evidence(previous['packet'],root)
    old_directory = (root/previous['component_refs']['challenges']['path']).parent
    source_root = old_directory.parents[2]/'challenge-issues'
    receipts = {}; counts = {}
    for role in panel.ROLES:
        path = source_root/(digest([digest(packet),role])+'.json') if refs is None else root/refs[role]['path']
        if refs is not None: read_evidence(refs[role],root)
        limits = IssueLimits(path,{'source_packet_hash':digest(packet),'role':role,'profile':panel.PROFILE})
        report = limits.report()
        if report != previous['challenges']['issue_histories'][role]:
            raise LegalMathError('E_INTEGRITY',details='Original challenge spending changed')
        receipts[role] = evidence_file(path,root)
        counts[role] = {key:{**value,'evidence_hash':receipts[role]['sha256']} for key,value in report.items()}
    return receipts, counts


def context(root, previous):
    return (read_evidence(previous['packet'],root), read_evidence(previous['candidates'],root),
            {r['candidate_id']:r['question'] for r in previous['questions']['assignments']})


def preflight(packet,candidates,questions,configuration,counts,initial):
    bound={'configuration':configuration,'contract':challenge_contract.build(packet,candidates,questions),
           'formal_obligations':{},'inherited_issues':counts,'pilot_guard':True}
    if initial: bound['initial_evidence']=initial
    selected=[o['obligation_id'] for o in bound['contract']['obligations']]
    rows=[]
    for offset in range(0,len(selected),configuration['batch_size']):
        group=selected[offset:offset+configuration['batch_size']]
        for role in panel.ROLES:
            request=panel.investigation_request(bound,packet,candidates,questions,group,role,1,None)
            schema=challenge_contract.ChallengeResponse.model_json_schema()
            schema['properties']['answers'].update(minItems=len(group),maxItems=len(group))
            schema['$defs']['ChallengeAnswer']['properties']['obligation_id']['enum']=group
            expanded,_,_=source_references.prepare(request,schema)
            wire=readable_challenges.encode(expanded)
            restored=readable_challenges.decode(wire,expected_request_hash=digest(expanded))
            if canonical(restored)!=canonical(expanded):raise LegalMathError('E_INTEGRITY')
            size=len(canonical(wire))
            if size>200000:raise LegalMathError('E_RESOURCE_LIMIT',details={'encoded_bytes':size,'maximum':200000})
            rows.append({'role':role,'batch':offset//configuration['batch_size'],
                         'request_hash':digest(request),'expanded_hash':digest(expanded),
                         'wire_hash':digest(wire),'encoded_bytes':size,'selected':group})
    return {'status':'EXACT_ALL_REQUEST_PREFLIGHT_PASSED','requests':rows,'maximum_input_bytes':200000,
            'candidate_count':len(candidates),'obligation_count':len(selected),'live_calls':0}


def verify_predecessor(root, previous, ref, snapshot_ref=None):
    from .complete_investigation import verify as verify_complete
    for item in previous['evidence']:
        read_evidence(item,root,json_value=False)
    historic=root
    if snapshot_ref is not None:
        snapshot=read_evidence(snapshot_ref,root)
        historic=Path(snapshot['path']).resolve()
        from ...canonical import raw_digest
        for name,expected in snapshot['inputs'].items():
            if raw_digest((historic/name).read_bytes())!=expected:
                raise LegalMathError('E_INTEGRITY',details='Historical source snapshot changed')
        if read_evidence(ref,historic)!=previous:
            raise LegalMathError('E_INTEGRITY',details='Historical dossier differs')
    return verify_complete(historic,previous)


def run(runner, predecessor, *, pilot_guard=True, predecessor_snapshot=None):
    from .complete_investigation import verify as verify_complete
    from .investigation_observations import method
    root=runner.root; directory=runner.directory
    if directory.exists() and (directory/'dossier.json').exists():
        report=loads((directory/'dossier.json').read_bytes());verify(root,report);return report
    predecessor=Path(predecessor).resolve()
    ref=evidence_file(predecessor,root);previous=read_evidence(ref,root)
    if previous.get('profile')!='complete-investigation.v1':raise LegalMathError('E_UNSUPPORTED_PROFILE')
    snapshot_ref=evidence_file(predecessor_snapshot,root) if predecessor_snapshot is not None else None
    verify_predecessor(root,previous,ref,snapshot_ref)
    config=panel.configuration(runner.challenge_providers,**{'input_profile':runner.input_profile,**runner.challenge_options})
    if config['input_profile']!=readable_challenges.PROFILE or config['rounds']!=1:
        raise LegalMathError('E_UNSUPPORTED_PROFILE',details='Capacity continuation requires one readable challenge round')
    refs,counts=inherited(root,previous)
    packet,candidates,questions=context(root,previous)
    initial=[r for r in previous['challenges']['history'] if r['status']=='VALIDATED']
    directory.mkdir(parents=True,exist_ok=True)
    before=method(runner)
    checked=preflight(packet,candidates,questions,config,counts,initial)
    save(directory/'preflight.json',checked)
    result=panel.run(packet,candidates,questions,runner.challenge_providers,directory/'challenges',
        inherited_issues=counts,initial_evidence=initial,pilot_guard=pilot_guard,**{
            'input_profile':runner.input_profile,**runner.challenge_options})
    if method(runner)!=before:raise LegalMathError('E_STALE_REVIEW')
    binding={'predecessor':ref,'predecessor_snapshot':snapshot_ref,'method':before,'configuration':config,'inherited_issue_ledgers':refs,
             'retained_stage_method':previous['binding']['investigation_method'],
             'reused_components':{k:v for k,v in previous['component_refs'].items() if k!='challenges'},
             'history_policy':'Original failed actions retained in predecessor; validated prior responses supplied to both roles.'}
    report={'profile':PROFILE,'binding':binding,'revision':digest(binding),'challenges':result,
        'component_refs':{'challenges':evidence_file(directory/'challenges/result.json',root)},
        'preflight':evidence_file(directory/'preflight.json',root),'execution_complete':bool(
            previous['core']['execution_complete'] and previous['replay'] and previous['scoped']['stopped'] is None
            and result['execution_complete']), 'fresh_whole_method_execution':False,
        'legal_correctness_established':False,'release_eligible':False,
        'evidence':[evidence_file(p,root) for p in sorted(directory.rglob('*')) if p.is_file()
                    and p.name not in ('dossier.json','.lock') and not p.name.endswith(('.lock','-wal','-shm'))]}
    save(directory/'dossier.json',report)
    verify(root,report)
    return report


def verify(root, report):
    from .complete_investigation import verify as verify_complete
    root=Path(root).resolve();binding=report['binding']
    if report['profile']!=PROFILE or report['revision']!=digest(binding):raise LegalMathError('E_INTEGRITY')
    for ref in report['evidence']:read_evidence(ref,root,json_value=False)
    previous=read_evidence(binding['predecessor'],root)
    if previous.get('profile')!='complete-investigation.v1':raise LegalMathError('E_UNSUPPORTED_PROFILE')
    verify_predecessor(root,previous,binding['predecessor'],binding.get('predecessor_snapshot'))
    expected_components={k:v for k,v in previous['component_refs'].items() if k!='challenges'}
    if (binding['reused_components']!=expected_components or
            binding['retained_stage_method']!=previous['binding']['investigation_method'] or
            binding['configuration']!=binding['method']['challenge_panel']):raise LegalMathError('E_INTEGRITY')
    _,counts=inherited(root,previous,binding['inherited_issue_ledgers'])
    packet,candidates,questions=context(root,previous)
    path=(root/report['component_refs']['challenges']['path']).parent
    actual=read_evidence(report['component_refs']['challenges'],root)
    if actual!=report['challenges']:raise LegalMathError('E_INTEGRITY')
    bound=loads((path/'binding.json').read_bytes())
    initial=[r for r in previous['challenges']['history'] if r['status']=='VALIDATED']
    if bound.get('inherited_issues')!=counts or bound.get('initial_evidence',[])!=initial:
        raise LegalMathError('E_INTEGRITY',details='Continuation reset or changed original history')
    actual=panel.verify(path,packet,candidates,questions,expected_configuration=binding['configuration'])
    for role in panel.ROLES:
        limits=IssueLimits(path/'issues'/(digest([digest(packet),role])+'.json'),
            {'source_packet_hash':digest(packet),'role':role,'profile':panel.PROFILE},inherited=counts[role])
        if actual['issue_histories'][role]!=limits.report():raise LegalMathError('E_INTEGRITY')
    checked=read_evidence(report['preflight'],root)
    if checked!=preflight(packet,candidates,questions,binding['configuration'],counts,initial):
        raise LegalMathError('E_INTEGRITY',details='Preflight does not reconstruct actual requests')
    expected=bool(previous['core']['execution_complete'] and previous['replay'] and
        previous['scoped']['stopped'] is None and actual['execution_complete'])
    if (report['execution_complete']!=expected or report['fresh_whole_method_execution'] is not False or
        report['legal_correctness_established'] is not False or report['release_eligible'] is not False):
        raise LegalMathError('E_INTEGRITY')
    return {'status':'FILE_BOUND_CHALLENGE_CONTINUATION_VERIFIED','execution_complete':expected,
            'fresh_whole_method_execution':False,'release_eligible':False}
