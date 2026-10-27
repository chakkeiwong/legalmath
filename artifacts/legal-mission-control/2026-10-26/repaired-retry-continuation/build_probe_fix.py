from pathlib import Path
import shutil,sys
ROOT=Path('/home/chakwong/python/legalmath');WORK=ROOT/'artifacts/legal-mission-control/2026-10-26/repaired-retry-continuation'
FIX=WORK/'probe-capacity-fix';FIX.mkdir(exist_ok=True)
paths=['scripts/legal_review_repair_service.py','scripts/legal_repaired_retry_continuation.py','tests/assurance/test_repaired_retry_continuation.py']
for name in paths:
    target=FIX/'before'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
body=(ROOT/paths[0]).read_text()
anchor='def recover():\n'
helper='''def probe_settings(service,request):
    from legalmath.interpretation.assurance.phased.downstream_input import input_byte_limit
    from legalmath.interpretation.assurance.phased.capacity_policy import output_bytes
    # Match the ordinary BoundDispatch contract, including reviewed larger output.
    return Settings(timeout_seconds=300).model_copy(update={
        'max_input_bytes':input_byte_limit(request,service.limits),
        'max_output_bytes':output_bytes(request,service.limits)})


def resume_undispatched_probe(service,folder,circuit,binding):
    """Caller owns supervisor/service locks. Never repeat a reserved call."""
    scheduled,started=read(folder/'scheduled.json'),read(folder/'started.json')
    charge=scheduled['charge'];slot=charge['failed_slot']
    require(not circuit['open'] and circuit.get('half_open_reserved') is False
        and circuit.get('half_open_request_hash')==charge['request_hash']
        and circuit.get('half_open_schema_hash')==charge['schema_hash']
        and started['stage']==charge['stage']==read(ROOT/BASE/'current-stage.json'),
        'Scheduled probe is not safely undispatched')
    verify(ROOT,started['ledger_before']);verify(ROOT,scheduled['original_failure'])
    require(read(ROOT/BASE/'live-calls.json')==read(ROOT/started['ledger_before']['path']),
        'Probe may have dispatched; retain and diagnose')
    ledger=read(ROOT/Path(binding['phase_service_scope']['path']).parent/'service-recovery.json')
    require(charge in ledger['charges'],'Lost scheduled probe reservation')
    request,schema,_,manifest=terminal_receipt(ROOT,BASE,slot,charge['request_hash'],
        allow_terminal_499=bool(binding.get('terminal_cancellation_recovery')))
    require(ref(ROOT,manifest)==scheduled['original_failure'] and digest(schema)==charge['schema_hash'],
        'Changed scheduled probe payload')
    settings=probe_settings(service,request)
    save(folder/'resumed-before-dispatch.json',dict(at_utc=datetime.now(timezone.utc).isoformat(),
        stage=charge['stage'],ledger_before=started['ledger_before'],settings=settings.model_dump(),
        reason='Retained scheduled request never reserved a provider call; correct capacity selection'))
    response=service._complete(request,schema,settings)
    save(folder/'response.json',dict(value=response.value,provenance=response.provenance,
        failed_slot=slot,service_scope=binding['phase_service_scope'],
        legal_acceptance=False,substituted_into_product=False))
    execution=MasterExecution(ROOT,PROGRAM,STATE)
    restored=restore_deferred(execution,ref(ROOT,folder/'response.json'));execution.sync_mission()
    return dict(required=True,recovered=True,restored=restored,evidence=ref(ROOT,folder/'response.json'),legal_acceptance=False)


'''
assert body.count(anchor)==1;body=body.replace(anchor,helper+anchor)
anchor="        if not circuit['open']:\n"
new="""        if not circuit['open'] and circuit.get('half_open_request_hash'):
            require(successor and successor.get('probe_capacity_repair'),
                'Unreviewed half-open probe continuation')
            slot=circuit['failed_slots'][-1]
            return resume_undispatched_probe(provider(),ROOT/service_work/'service-resumption'/str(slot),circuit,binding)
"""
assert body.count(anchor)==1;body=body.replace(anchor,new+anchor)
old='response = service._complete(request, schema, Settings(timeout_seconds=300))'
assert body.count(old)==1;body=body.replace(old,'response = service._complete(request, schema, probe_settings(service,request))')
target=FIX/'source'/paths[0];target.parent.mkdir(parents=True,exist_ok=True);target.write_text(body)
body=(ROOT/paths[1]).read_text()
anchor="        require(process_alive(saved['process']),'Ended retry worker requires reviewed recovery')"
# Match exact arm block, preserving all initial launch records.
old="""        if path.exists():
            saved=read(path);require(process_alive(saved['process']),'Ended retry worker requires reviewed recovery')
            return saved
"""
new="""        if path.exists():
            saved=read(path)
            if process_alive(saved['process']):return saved
            revision=read(ROOT/PROGRAM)[KEY]
            require(revision.get('probe_capacity_repair'),'Ended retry worker requires reviewed recovery')
            path=ROOT/WORK/'probe-capacity-fix'/'armed.json'
            if path.exists():
                saved=read(path);require(process_alive(saved['process']),'Bounded probe repair already ended')
                return saved
"""
assert body.count(old)==1;body=body.replace(old,new)
target=FIX/'source'/paths[1];target.parent.mkdir(parents=True,exist_ok=True);target.write_text(body)
body=(ROOT/paths[2]).read_text()+'''

def test_exact_recovery_uses_same_capacity_as_product_dispatch():
    from pathlib import Path
    from scripts.legal_review_repair_service import probe_settings
    from legalmath.interpretation.assurance.bounded_context import Limits
    from legalmath.canonical import canonical
    root=Path('/home/chakwong/python/legalmath')
    request=json.loads((root/'artifacts/legal-mission-control/2026-10-13/master/provider-evidence/6471-c585d8d50bb60dc3/request.json').read_text())
    value=probe_settings(SimpleNamespace(limits=Limits()),request)
    assert 100000 < len(canonical(request)) < value.max_input_bytes==250000
    assert value.max_output_bytes==262144 and value.timeout_seconds==300
    request['capacity_profile']='unreviewed'
    with pytest.raises(LegalMathError):probe_settings(SimpleNamespace(limits=Limits()),request)

def test_started_probe_with_a_new_charge_must_not_repeat(tmp_path,monkeypatch):
    from scripts import legal_review_repair_service as service
    from scripts.legal_mission_execution import Refused,ref
    from pathlib import Path
    monkeypatch.setattr(service,'ROOT',tmp_path);monkeypatch.setattr(service,'BASE',Path('base'))
    folder=tmp_path/'probe';stage={'path':'stage.json','sha256':'s'}
    charge=dict(failed_slot=1,request_hash='r',schema_hash='s',stage=stage)
    save(tmp_path/'before.json',dict(calls=[]));save(tmp_path/'failure.json',{})
    save(folder/'scheduled.json',dict(charge=charge,original_failure=ref(tmp_path,'failure.json')))
    save(folder/'started.json',dict(stage=stage,ledger_before=ref(tmp_path,'before.json')))
    save(tmp_path/'base/current-stage.json',stage);save(tmp_path/'base/live-calls.json',dict(calls=[{}]))
    circuit=dict(open=False,half_open_reserved=False,half_open_request_hash='r',half_open_schema_hash='s')
    with pytest.raises(Refused,match='may have dispatched'):
        service.resume_undispatched_probe(SimpleNamespace(_complete=lambda *a:pytest.fail('Repeated transport')),folder,circuit,{})
'''
target=FIX/'source'/paths[2];target.parent.mkdir(parents=True,exist_ok=True);target.write_text(body)
for name in paths:
    source=FIX/'source'/name;compile(source.read_text(),name,'exec')
    shutil.copyfile(source,Path('/tmp/legalmath-repaired-retry-continuation')/name)
print('Bounded probe-capacity correction staged.')
