import json
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.phased.preparation_diagnosis import diagnose


def put(root, name, value):
    path=root/name;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value))


def test_returned_failure_retains_resource_refusal_without_authorizing_retry(tmp_path):
    put(tmp_path,'product/result.json',{'answers':{'p10':{'status':'FAILED','error':'E_DEPENDENCY','reason':'Dependent synthesis failed'}}})
    put(tmp_path,'product/phases/reduction-p10-0/outcome.json',{'phase':'reduction-p10-0',
        'execution_complete':False,'results':[],
        'resource_refusal':{'status':'FAILED','error':'E_RESOURCE_LIMIT','reason':'Phase exceeds original global window'}})
    report=diagnose(tmp_path,tmp_path/'product','p10')
    assert not report['prepared'] and report['provider_calls_authorized']==0
    assert report['failures'][0]['origin']=='returned_answer'
    assert report['incomplete_phases'][0]['resource_refusal']['reason']=='Phase exceeds original global window'


def test_failed_call_and_exception_are_retained(tmp_path):
    put(tmp_path,'product/phases/reduction/outcome.json',{'execution_complete':False,
        'results':[{'key':'reduce-0','result':{'status':'FAILED','error':'E_DEPENDENCY','reason':'model failed'}}]})
    report=diagnose(tmp_path,tmp_path/'product','p10',exception=LegalMathError('E_DEPENDENCY',details='preparation failed'))
    assert report['failures'][0]['origin']=='exception'
    assert report['incomplete_phases'][0]['failed_calls'][0]['key']=='reduce-0'


def test_prepared_result_is_not_failure(tmp_path):
    report=diagnose(tmp_path,tmp_path/'product','p10',result={'answers':{'p10':{'status':'PREPARED'}}})
    assert report['prepared'] and report['failures']==[] and report['incomplete_phases']==[]


def test_missing_preparation_is_never_reported_as_success(tmp_path):
    report=diagnose(tmp_path,tmp_path/'product','p10')
    assert not report['prepared'] and report['failures'][0]['origin']=='missing_preparation'


def test_optional_candidate_failure_does_not_block_prepared_baseline(tmp_path):
    put(tmp_path,'product/phases/call-candidates-p10/outcome.json',{'phase':'call-candidates-p10',
        'execution_complete':False,'results':[{'key':'candidates-p10','result':
        {'status':'FAILED','error':'E_RESOURCE_LIMIT','reason':'Too large'}}]})
    report=diagnose(tmp_path,tmp_path/'product','p10',result={'answers':{'p10':{'status':'PREPARED'}}})
    assert report['prepared'] and not report['required_incomplete_phases']
    assert len(report['optional_incomplete_phases'])==len(report['incomplete_phases'])==1
    assert not report['legal_acceptance'] and report['provider_calls_authorized']==0


def test_optional_integrity_failure_still_blocks(tmp_path):
    put(tmp_path,'product/phases/call-candidates-p10/outcome.json',{'phase':'call-candidates-p10',
        'execution_complete':False,'results':[{'key':'candidates-p10','result':
        {'status':'FAILED','error':'E_INTEGRITY','reason':'Changed source'}}]})
    report=diagnose(tmp_path,tmp_path/'product','p10',result={'answers':{'p10':{'status':'PREPARED'}}})
    assert not report['prepared'] and report['required_incomplete_phases']
