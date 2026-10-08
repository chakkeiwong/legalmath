"""Local source-update monitor and separately compiled Java host; no bank deployment."""
from argparse import ArgumentParser
from copy import deepcopy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from legalmath.canonical import canonical,digest,raw_digest,loads
from legalmath.interpretation.assurance.monitor import Monitor
from legalmath.interpretation.assurance.sources import acquire_context,packet_from_context
from legalmath.interpretation.search.formal import bundle
from legalmath.java.host_package import prepare,run
from tests.assurance.support import reading
from tests.search.test_formal import AT


def main(out):
    out=Path(out).resolve()
    if out.exists() or not out.is_relative_to(ROOT/'artifacts/interpretation/round4'):
        raise ValueError('Use a new round4 output directory')
    out.mkdir(parents=True);jdk=ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1'
    urls={k:'https://www.sfc.hk/test/synthetic-integration/'+k for k in ('gift','unrelated')}
    documents={url:{'url':url,'media_type':'text/plain','data':b'A distributor should not offer gifts.'} for url in urls.values()}
    controls=[{'control_id':k,'source':url,'dependencies':[],'selected_slice':'Synthetic gift integration control'} for k,url in urls.items()]
    scenario={'subject_id':'fixture','facts':{name:{'type':'bool','status':'known','value':True,'evidence_ids':['fixture'],
        'valid_from':AT,'valid_until':None,'recorded_at':AT} for name in ('gift','discount')}}
    called=[]
    def investigate(control,scope):
        doc=documents[control['source']]
        assert raw_digest(doc['data'])==scope['sources'][control['source']]
        packet=packet_from_context(acquire_context([doc]),control['selected_slice']);packet['authority']='SYNTHETIC_FIXTURE'
        omitted=b'other than' not in doc['data'];r=reading(omitted);uid=packet['units'][0]['unit_id']
        r['citations']=[{'unit_id':uid,'quote':packet['units'][0]['text']}]
        for f in r['formalization']['facts']:f['source_unit_ids']=[uid]
        compiled=bundle(r,packet,AT);expected='TRUE' if omitted else 'FALSE'
        case={'id':'discount-offer','bundle':compiled,'snapshot':scenario,'rule_id':'selected.control',
              'valid_at':AT,'known_at':AT,'expected':{'status':expected}}
        directory=out/'packages'/control['control_id']/digest(scope)
        metadata=prepare(compiled,[case],{doc['url']:doc['data']},directory,jdk)
        java=run(directory,scenario,'selected.control',AT,jdk)
        assert java['status']==expected;called.append(control['control_id'])
        return {'status':'LOCAL_JAVA_CONFORMANCE_ONLY','execution_complete':True,'release_eligible':False,
                'interpretation_authority':'DEVELOPER_CONTROLLED_FIXTURE','java':java,'package':str(directory),'metadata':metadata}
    versions=lambda:{url:raw_digest(doc['data']) for url,doc in documents.items()}
    monitor=Monitor(out/'monitor',cadence_seconds=10,max_attempts=2)
    first=monitor.tick(controls,versions(),'local.fixture.v1','fact-schema.v1',0,investigate,evaluation_at=AT)
    old={str(p):raw_digest(p.read_bytes()) for p in (out/'packages').rglob('*') if p.is_file()}
    unchanged=monitor.tick(controls,versions(),'local.fixture.v1','fact-schema.v1',1,investigate,evaluation_at=AT)
    assert all(r['status']=='UNCHANGED' for r in unchanged['results'])
    documents[urls['gift']]['data']=b'A distributor should not offer gifts other than a discount of fees or charges.'
    updated=monitor.tick(controls,versions(),'local.fixture.v1','fact-schema.v1',30,investigate,evaluation_at=AT)
    assert updated['overdue'] and updated['results'][0]['status']=='COMPLETED' and updated['results'][1]['status']=='UNCHANGED'
    assert called==['gift','unrelated','gift'] and all(raw_digest(Path(p).read_bytes())==h for p,h in old.items())
    result=loads((out/'monitor/results'/(updated['results'][0]['result_hash']+'.json')).read_bytes())
    assert result['result']['java']['status']=='FALSE'
    bad=Monitor(out/'failure-monitor',cadence_seconds=10,max_attempts=2)
    for t in (0,1):
        assert bad.tick(controls[:1],versions(),'m','f',t,lambda c,s:{'release_eligible':True})['results'][0]['status']=='FAILED'
    exhausted=bad.tick(controls[:1],versions(),'m','f',30,lambda c,s:None)
    assert exhausted['results'][0]['status']=='REVISION_RETRY_LIMIT'
    summary={'engineering_status':'PASS','institution_operational_status':'CONFIGURATION_REQUIRED',
        'new_live_calls':0,'java_host_processes':3,'source_updates':1,'unchanged_control_preserved':True,
        'old_java_outcome':'TRUE','new_java_outcome':'FALSE','scope':'CONTROLLED_SYNTHETIC_GIFT_FIXTURE',
        'overdue_reported':True,'retry_exhaustion_reported':True,'automatic_release_allowed':False,
        'packages':list(str(p.relative_to(out)) for p in (out/'packages').glob('*/*/package.json')),
        'external_inputs_required':['Institution staging host and service identity','Institution control registry and fact bindings',
                                    'Institution scheduler and source-update policy','Institution release-role configuration']}
    (out/'summary.json').write_bytes(canonical(summary))
    (out/'manifest.json').write_bytes(canonical({'files':{str(p.relative_to(out)):raw_digest(p.read_bytes())
        for p in sorted(out.rglob('*')) if p.is_file()}}))
    print('B5 local PASS: source change produced a successor Java package and changed checked outcome; institution inputs remain missing.')


if __name__=='__main__':
    p=ArgumentParser(description=__doc__);p.add_argument('--out',required=True);main(p.parse_args().out)
