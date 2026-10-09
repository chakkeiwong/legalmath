import hashlib
import json
import pytest
from scripts.prospectus_closure_attribution import REL, report


def test_attribution_requires_unchanged_evidence_and_does_not_guess_by_id(tmp_path):
    base = tmp_path/REL
    base.mkdir(parents=True)
    source = tmp_path/'counterexample.json'
    source.write_text('{"local_adapter_failed":true}')
    row = {'id':'G01','finding':'A supplied counterexample fails in the local adapter',
           'remaining':'Package behavior not tested directly','next_action':'Run the direct supported package invocation',
           'evidence':[{'path':'counterexample.json','sha256':hashlib.sha256(source.read_bytes()).hexdigest()}]}
    (base/'gap-status.json').write_text(json.dumps({'gaps':[{'id':'G01'}]}))
    (base/'attribution-review.json').write_text(json.dumps({'gaps':[row],'packages':[]}))
    result = report(tmp_path)
    assert not result['automatic_causal_inference']
    assert result['gaps'][0]['finding']==row['finding']
    source.write_text('{"local_adapter_failed":false}')
    with pytest.raises(ValueError,match='evidence changed'):
        report(tmp_path)


def test_missing_review_is_not_replaced_with_static_classification(tmp_path):
    base = tmp_path/REL
    base.mkdir(parents=True)
    (base/'gap-status.json').write_text(json.dumps({'gaps':[{'id':'G01'}]}))
    (base/'attribution-review.json').write_text(json.dumps({'gaps':[],'packages':[]}))
    with pytest.raises(ValueError,match='cover each'):
        report(tmp_path)
