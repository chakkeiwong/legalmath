from copy import deepcopy
import json
import pytest
from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.integration_contract import evidence_file
from legalmath.interpretation.assurance.time_authority import effective_deadline, PROFILE, USER


def fixture(tmp_path):
    def save(name, value):
        p = tmp_path/name
        p.write_text(json.dumps(value))
        return evidence_file(p, tmp_path)
    grant = {'deadline_utc':'2026-10-18T19:03:39+00:00', 'maximum_calls':8100}
    grant_ref = save('live-grant.json', grant)
    ledger = {'grant_hash':digest(grant), 'maximum':8100, 'calls':[{'slot':1}, {'slot':2}]}
    before = save('ledger-before.json', ledger)
    save('live-calls.json', ledger)
    review = save('review.json', {'review':'approved'})
    extension = dict(profile=PROFILE, approved=True, user_instruction=USER, duration_seconds=172800,
        original_grant=grant_ref, original_grant_hash=digest(grant), maximum_calls=8100,
        approved_at_utc='2026-10-18T18:55:16+00:00', deadline_utc='2026-10-20T18:55:16+00:00',
        review=review, ledger_before=before, prior_calls=2)
    def bind(value):
        pointer = save('extension.json', value)
        program = save('program.json', {'deadline_utc':value['deadline_utc'],
            'synthesis_continuation':{'time_extension':pointer}})
        binding = dict(time_extension=pointer, grant_hash=digest(grant), deadline_utc=grant['deadline_utc'],
            effective_deadline_utc=value['deadline_utc'], review=review, program=program)
        save('current-binding.json', binding)
        return binding
    return grant, ledger, extension, bind, save


def test_extension_preserves_original_identity_and_charges(tmp_path):
    grant, ledger, extension, bind, save = fixture(tmp_path)
    bind(extension)
    save('live-calls.json', {**ledger, 'calls':ledger['calls']+[{'slot':3}]})
    assert effective_deadline(tmp_path,tmp_path) == extension['deadline_utc']
    assert json.loads((tmp_path/'live-grant.json').read_text()) == grant


@pytest.mark.parametrize('key,value', [('approved',False), ('user_instruction','continue'),
    ('maximum_calls',8200), ('prior_calls',0), ('duration_seconds',172801),
    ('deadline_utc','2026-10-21T18:55:16+00:00'), ('approved_at_utc','2026-10-18T19:55:16+00:00')])
def test_rejects_authority_changes(tmp_path,key,value):
    grant, ledger, extension, bind, save = fixture(tmp_path)
    extension[key] = value
    bind(extension)
    with pytest.raises(LegalMathError): effective_deadline(tmp_path,tmp_path)


def test_rejects_lost_charges(tmp_path):
    grant, ledger, extension, bind, save = fixture(tmp_path)
    bind(extension)
    save('live-calls.json',{**ledger,'calls':ledger['calls'][1:]})
    with pytest.raises(LegalMathError): effective_deadline(tmp_path,tmp_path)


def test_original_path_and_unbound_extension(tmp_path):
    grant, ledger, extension, bind, save = fixture(tmp_path)
    assert effective_deadline(tmp_path,tmp_path) == grant['deadline_utc']
    save('current-binding.json',{'effective_deadline_utc':extension['deadline_utc']})
    with pytest.raises(LegalMathError): effective_deadline(tmp_path,tmp_path)


def test_stale_program_binding_is_rejected(tmp_path):
    grant, ledger, extension, bind, save = fixture(tmp_path)
    binding=bind(extension)
    binding['program']=save('stale-program.json',{'deadline_utc':extension['deadline_utc']})
    save('current-binding.json',binding)
    with pytest.raises(LegalMathError): effective_deadline(tmp_path,tmp_path)


@pytest.mark.parametrize('continuation', [False, True])
def test_expired_original_grant_admits_and_charges_only_with_bound_extension(tmp_path, continuation):
    from datetime import datetime,timedelta,timezone
    from legalmath.interpretation.assurance.bounded_provider import CampaignAllowance,SERVICE_DELAYED_POLICY
    from legalmath.interpretation.assurance.phased.admission import admit
    def save(name,value):
        path=tmp_path/name;path.write_text(json.dumps(value));return evidence_file(path,tmp_path)
    now=datetime.now(timezone.utc);route={'model':'fixture','provider':'fixture','fields':{}}
    proposal=save('proposal.json',dict(dispatch_ready=True,maximum_calls=8100,routing_hash=digest(route),window_seconds=3600,bindings=[]))
    grant=dict(profile='integration-master-live-grant.v1',approved=True,approval_text='synthetic',proposal=proposal,
        maximum_calls=8100,routing_hash=digest(route),started_utc=(now-timedelta(hours=2)).isoformat(),deadline_utc=(now-timedelta(hours=1)).isoformat())
    original=save('live-grant.json',grant)
    ledger=dict(grant_hash=digest(grant),maximum=8100,calls=[{'request_hash':'spent'}])
    save('live-calls.json',ledger);before=save('before.json',ledger);review=save('review.json',{'review':'synthetic'})
    allowance=CampaignAllowance(tmp_path,route,root=tmp_path)
    with pytest.raises(LegalMathError):allowance.check()
    extension=dict(profile=PROFILE,approved=True,user_instruction=USER,duration_seconds=172800,
        approved_at_utc=now.isoformat(),deadline_utc=(now+timedelta(hours=48)).isoformat(),original_grant=original,
        original_grant_hash=digest(grant),maximum_calls=8100,prior_calls=1,ledger_before=before,review=review)
    pointer=save('extension.json',extension)
    program=save('program.json',{'deadline_utc':extension['deadline_utc'],'synthesis_continuation':{'time_extension':pointer}})
    binding=dict(profile='integration-current-binding.v1',user_instruction=USER,review=review,historical_archives=[],bindings=[],
        grant_hash=digest(grant),maximum_calls=8100,routing_hash=digest(route),deadline_utc=grant['deadline_utc'],
        effective_deadline_utc=extension['deadline_utc'],time_extension=pointer,program=program,ledger_before=before,
        service_recovery_policy=SERVICE_DELAYED_POLICY,phase_service_scope=None)
    save('current-binding.json',binding)
    if continuation:
        extension,binding = extend_fixture(save,extension,binding)
    assert allowance.check()['calls']==ledger['calls']
    stage_ref=admit(tmp_path,'.','live','reduction-p10-0',105,owner='prepare-p10')
    stage=json.loads((tmp_path/stage_ref['path']).read_text())
    assert stage['deadline_utc']==extension['deadline_utc'] and stage['grant_hash']==digest(grant)
    allowance.expected='pending-synthesis'
    assert allowance.reserve('pending-synthesis')==2
    assert json.loads((tmp_path/'live-calls.json').read_text())['calls'][0]==ledger['calls'][0]
    assert evidence_file(tmp_path/'live-grant.json',tmp_path)==original


def extend_fixture(save, extension, binding):
    from datetime import datetime, timedelta
    from legalmath.interpretation.assurance.time_authority import CONTINUATION_PROFILE, CONTINUATION_USER
    previous_program = dict(deadline_utc=extension['deadline_utc'], synthesis_continuation={'time_extension':binding['time_extension']})
    prior_program = save('previous-program.json',previous_program)
    previous_extension = save('previous-extension.json',extension)
    previous_program['synthesis_continuation']['time_extension'] = previous_extension
    prior_program = save('previous-program.json',previous_program)
    old_binding = dict(binding,program=prior_program,time_extension=previous_extension)
    prior_binding = save('previous-binding.json',old_binding)
    value = dict(extension,profile=CONTINUATION_PROFILE,user_instruction=CONTINUATION_USER,duration_seconds=259200,
        deadline_utc=(datetime.fromisoformat(extension['approved_at_utc'])+timedelta(hours=72)).isoformat(),
        previous_extension=previous_extension,prior_program=prior_program,prior_binding=prior_binding,
        previous_deadline_utc=extension['deadline_utc'])
    pointer = save('new-extension.json',value)
    program = save('program.json',dict(deadline_utc=value['deadline_utc'],time_continuation={'time_extension':pointer}))
    current = dict(binding,time_extension=pointer,program=program,effective_deadline_utc=value['deadline_utc'])
    save('current-binding.json',current)
    return value,current


def test_72_hour_chain_preserves_prior_extension(tmp_path):
    grant,ledger,extension,bind,save = fixture(tmp_path)
    value,current = extend_fixture(save,extension,bind(extension))
    assert effective_deadline(tmp_path,tmp_path) == value['deadline_utc']
    assert json.loads((tmp_path/'previous-extension.json').read_text()) == extension
    assert json.loads((tmp_path/'live-calls.json').read_text()) == ledger


@pytest.mark.parametrize('mutation', ['duration','instruction','ceiling','ledger','predecessor','clock','program','review'])
def test_72_hour_chain_rejects_changed_authority(tmp_path,mutation):
    grant,ledger,extension,bind,save = fixture(tmp_path)
    value,current = extend_fixture(save,extension,bind(extension))
    if mutation == 'duration': value['duration_seconds'] += 1
    elif mutation == 'instruction': value['user_instruction'] = 'continue'
    elif mutation == 'ceiling': value['maximum_calls'] += 1
    elif mutation == 'ledger': save('live-calls.json',dict(ledger,calls=[]))
    elif mutation == 'predecessor': value['previous_extension'] = save('unknown.json',dict(extension,profile='unknown'))
    elif mutation == 'clock': value['previous_deadline_utc'] = value['deadline_utc']
    elif mutation == 'review': current['review'] = save('different-review.json',{})
    current['time_extension'] = save('new-extension.json',value)
    current['program'] = save('program.json',dict(deadline_utc=value['deadline_utc'],
        time_continuation={} if mutation == 'program' else {'time_extension':current['time_extension']}))
    save('current-binding.json',current)
    with pytest.raises(LegalMathError): effective_deadline(tmp_path,tmp_path)
