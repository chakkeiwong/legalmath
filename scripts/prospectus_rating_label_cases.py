"""Freeze literal source labels and independent outcomes before implementation."""
from datetime import datetime,timezone
import signal,time
from scripts import prospectus_definition_dependency as prior
from scripts import prospectus_rating_label_oracle as oracle
ROOT,AUTH=prior.ROOT,prior.AUTH
PREP=AUTH/'reviews/rating-labels-336'
PLAN='docs/plans/prospectus-rating-labels-2026-10-19.md'
ORACLE='scripts/prospectus_rating_label_oracle.py'
METHOD='scripts/prospectus_rating_label_cases.py'

def main():
    assert not PREP.exists() and not (ROOT/'src/legalmath/prospectus/successor/rating_labels.py').exists()
    start=time.monotonic();PREP.mkdir()
    prior.save(PREP/'cases-started.json',{'command':['.venv/bin/python','-m','scripts.prospectus_rating_label_cases'],
        'started_at':datetime.now(timezone.utc).isoformat(),'seconds_bound':90})
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('Rating cases bound')));signal.alarm(90)
    try:
        for name,checksum in prior.read(prior.HERE/'outputs.json').items():assert prior.sha(prior.HERE/name)==checksum,name
        products,_=prior.baseline();ordinary=prior.read(prior.HERE/'ordinary-answer.json.gz')
        node=ordinary['causal_rating_review']['context']
        actual=next(n for n in products['P3']['payload']['clauses']['nodes'] if n['id']=='basf-redemption:control_put')
        assert node==actual
        text=products['P2']['payload']['assembly']['continuous_text']
        anchors=['S&P Global Ratings Europe\nLimited ("S&P")',"""Moody's Deutschland GmbH ("Moody's")""",
            'Fitch Ratings Ireland\nLimited ("Fitch")','BBB- von S&P und Fitch/Baa3 von',
            "BB+ von S&P und Fitch/Ba1 von Moody's"]
        evidence=[]
        for anchor in anchors:
            assert text.count(anchor)==1,anchor
            a=text.index(anchor);evidence.append({'start':a,'end':a+len(anchor),'quote':anchor})
        assert 'auf Grund des' in node['quote'] and '120 Tage' in node['quote']
        cases=oracle.input_cases(ordinary);content=oracle.frozen_content(ordinary,products,cases)
        outcomes={r['id']:oracle.expectations(r,oracle.labels(r['agency_label'],r['before_label'],r['after_label'])) for r in cases}
        assert set(x['rating'] for x in outcomes.values())=={'YES','NO','UNKNOWN','CONFLICT'}
        decisions={'cases':cases,'source_evidence':evidence,'source_context':node,
            'source_names':oracle.NAMES,'thresholds':[{'agency':a,'label':l,'category':c} for a,l,c in oracle.TABLE]}
        prior.save(PREP/'source-decisions.json',decisions);prior.save(PREP/'expected-content.json',content)
        prior.save(PREP/'independent-outcomes.json',outcomes)
        prior.save(PREP/'cases-freeze.json',{'created_at':datetime.now(timezone.utc).isoformat(),'candidate_absent':True,
            'source_decisions_sha256':prior.sha(PREP/'source-decisions.json'),'expected_file_sha256':prior.sha(PREP/'expected-content.json'),
            'expected_content_sha256':oracle.digest(content),'products_sha256':oracle.digest(products),
            'ordinary_answer_sha256':oracle.digest(ordinary),'oracle_sha256':prior.sha(ROOT/ORACLE),
            'method_sha256':prior.sha(ROOT/METHOD),'plan_sha256':prior.sha(ROOT/PLAN)})
        result={'status':'PASS','thresholds':6,'agency_spellings':6,'scenarios':len(cases),
            'independent_boolean_outcomes':True,'wall_seconds':time.monotonic()-start}
        prior.save(PREP/'case-preparation.json',result);print(result)
    except BaseException as error:
        prior.save(PREP/'case-failure.json',{'type':type(error).__name__,'message':str(error),'wall_seconds':time.monotonic()-start});raise
    finally:signal.alarm(0)

if __name__=='__main__':main()
