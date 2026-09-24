from legalmath.interpretation.assurance.monitor import Monitor
from legalmath.canonical import loads


def controls():
    return [{'control_id':'gift','source':'circular','dependencies':['definition']},
            {'control_id':'other','source':'unrelated','dependencies':[]}]


def test_source_method_and_schema_changes_trigger_only_affected_replay(tmp_path):
    monitor=Monitor(tmp_path);calls=[]
    def run(control,scope):calls.append(control['control_id']);return {'status':'CHECKED','release_eligible':False}
    versions={'circular':'c1','definition':'d1','unrelated':'u1'}
    first=monitor.tick(controls(),versions,'model.prompt.v1','facts.v1',0,run)
    oldfiles={p.name:p.read_bytes() for p in (tmp_path/'results').glob('*.json')}
    assert calls==['gift','other']
    assert all(r['status']=='UNCHANGED' for r in monitor.tick(controls(),versions,'model.prompt.v1','facts.v1',1,run)['results'])
    versions['definition']='d2'
    monitor.tick(controls(),versions,'model.prompt.v1','facts.v1',2,run)
    assert calls==['gift','other','gift']
    monitor.tick(controls(),versions,'model.prompt.v2','facts.v1',3,run)
    assert calls[-2:]==['gift','other']
    monitor.tick(controls(),versions,'model.prompt.v2','facts.v2',4,run)
    assert calls[-2:]==['gift','other'] and len(calls)==7
    assert all((tmp_path/'results'/name).read_bytes()==data for name,data in oldfiles.items())


def test_missing_dependency_invalidates_current_and_preserves_unrelated(tmp_path):
    m=Monitor(tmp_path);calls=[]
    def run(c,s):calls.append(c['control_id']);return {'release_eligible':False}
    m.tick(controls(),{'circular':'c','definition':'d','unrelated':'u'},'m','f',0,run)
    tick=m.tick(controls(),{'circular':'c','unrelated':'u'},'m','f',1,run)
    assert tick['results'][0]['status']=='SOURCE_UNAVAILABLE'
    assert tick['results'][1]['status']=='UNCHANGED' and len(calls)==2


def test_failures_consume_retry_budget_and_overdue_is_visible(tmp_path):
    m=Monitor(tmp_path,cadence_seconds=10,max_attempts=2)
    def bad(c,s):raise OSError('upstream unavailable')
    c=controls()[:1];v={'circular':'c','definition':'d'}
    assert m.tick(c,v,'m','f',0,bad)['results'][0]['status']=='FAILED'
    assert m.tick(c,v,'m','f',1,bad)['results'][0]['status']=='FAILED'
    final=m.tick(c,v,'m','f',30,bad)
    assert final['overdue'] and final['results'][0]['status']=='REVISION_RETRY_LIMIT'


def test_callback_cannot_grant_release_authority(tmp_path):
    m=Monitor(tmp_path)
    r=m.tick(controls()[:1],{'circular':'c','definition':'d'},'m','f',0,lambda c,s:{'release_eligible':True})
    evidence=loads((tmp_path/'results'/(r['results'][0]['result_hash']+'.json')).read_bytes())
    assert evidence['result']['error']=='E_AUTHORITY'


def test_failed_assurance_result_is_retried_instead_of_cached_as_completed(tmp_path):
    m=Monitor(tmp_path);calls=[]
    def run(c,s):calls.append(c);return {'status':'FAILED_INTEGRITY','release_eligible':False}
    for t in (0,1):
        assert m.tick(controls()[:1],{'circular':'c','definition':'d'},'m','f',t,run)['results'][0]['status']=='FAILED'
    assert len(calls)==2


def test_new_evaluation_date_replays_even_when_source_bytes_are_unchanged(tmp_path):
    m=Monitor(tmp_path);calls=[]
    def run(c,s):calls.append(s['evaluation_at']);return {'release_eligible':False}
    args=(controls()[:1],{'circular':'c','definition':'d'},'m','f')
    m.tick(*args,0,run,evaluation_at='2026-05-01T00:00:00.000000Z')
    m.tick(*args,1,run,evaluation_at='2026-05-01T00:00:00.000000Z')
    m.tick(*args,2,run,evaluation_at='2026-06-01T00:00:00.000000Z')
    assert calls==['2026-05-01T00:00:00.000000Z','2026-06-01T00:00:00.000000Z']
