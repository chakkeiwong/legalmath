"""Freeze complete evidence and expected question projection before candidate creation."""
from datetime import datetime,timezone
import signal,time
from scripts import prospectus_definition_remainder as prior
from scripts import prospectus_definition_dependency_oracle as oracle

ROOT,AUTH=prior.ROOT,prior.AUTH
PREP=AUTH/'reviews/definition-dependencies-335'
PLAN='docs/plans/prospectus-definition-dependencies-2026-10-19.md'
ORACLE='scripts/prospectus_definition_dependency_oracle.py'
METHOD='scripts/prospectus_definition_dependency_cases.py'

def main():
    assert not PREP.exists() and not (ROOT/'src/legalmath/prospectus/successor/definition_dependencies.py').exists()
    start=time.monotonic();PREP.mkdir()
    prior.save(PREP/'cases-started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_definition_dependency_cases'],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':90})
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Dependency case bound')));signal.alarm(90)
    try:
        for name,checksum in prior.read(prior.HERE/'outputs.json').items():assert prior.sha(prior.HERE/name)==checksum,name
        products,_=prior.baseline();ordinary=prior.read(prior.HERE/'ordinary-answer.json.gz')
        report=ordinary['definition_remainder_review'];source=ordinary['definition_sources']
        assert len(report['records'])==62 and len(report['uses'])==612
        assert not any(u['disposition']=='UNRECONCILED' for u in report['uses'])
        assert sum(u['origin']=='ORIGINAL' for u in report['uses'])==610
        for r in report['records']:
            current=next(v for v in source['records'] if v['id']==r['id'])
            assert r['original_record_sha256']==oracle.digest(current)
            actual=[report['uses'][i] for i in r['use_indices'] if report['uses'][i]['origin']=='ORIGINAL']
            assert len(actual)==len(current['uses'])
            for use,item in zip(actual,current['uses']):
                interval=source['intervals'][item['interval']]
                assert all(use[k]==interval[k] for k in ('start','end','quote'))
                assert use['interval']==item['interval'] and use['record']==r['id']
        content=oracle.freeze_content(ordinary);projected=oracle.question_projection(ordinary,content)
        for path in oracle.PATHS:
            before=oracle.at(ordinary['questions'],path);after=oracle.at(projected,path)
            assert {k:v for k,v in before.items() if k not in ('unresolved','subquestions')}=={k:v for k,v in after.items() if k not in ('unresolved','subquestions')}
            assert [x for x in before['unresolved'] if not x.startswith('definition-source:')]==[x for x in after['unresolved'] if not x.startswith(('definition-premise:','definition-discovery:'))]
        prior.save(PREP/'source-decisions.json',content['records']);prior.save(PREP/'expected-content.json',content)
        prior.save(PREP/'cases-freeze.json',{'created_at':datetime.now(timezone.utc).isoformat(),'candidate_absent':True,
            'source_decisions_sha256':prior.sha(PREP/'source-decisions.json'),'expected_file_sha256':prior.sha(PREP/'expected-content.json'),
            'expected_content_sha256':oracle.digest(content),'expected_questions_sha256':oracle.digest(projected),
            'products_sha256':oracle.digest(products),'ordinary_answer_sha256':oracle.digest(ordinary),
            'oracle_sha256':prior.sha(ROOT/ORACLE),'method_sha256':prior.sha(ROOT/METHOD),'plan_sha256':prior.sha(ROOT/PLAN)})
        result={'status':'PASS','records':62,'associations':612,'question_paths':5,
            'remaining_premises':sum(len(r['remaining_premises']) for r in content['records']),
            'wall_seconds':time.monotonic()-start}
        prior.save(PREP/'case-preparation.json',result);print(result)
    except BaseException as error:
        prior.save(PREP/'case-failure.json',{'type':type(error).__name__,'message':str(error),'wall_seconds':time.monotonic()-start});raise
    finally:signal.alarm(0)

if __name__=='__main__':main()
