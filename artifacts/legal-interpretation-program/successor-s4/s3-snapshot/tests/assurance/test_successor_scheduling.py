"""Historical scheduling evidence must not silently become current assurance."""
from pathlib import Path
import sys
from zipfile import ZipFile
import pytest
from legalmath.errors import LegalMathError

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
import assurance_successor_scheduling as scheduling
from run_assurance_successor import save,sha


def historical_fixture(root):
    code=root/'src/legalmath/example.py';code.parent.mkdir(parents=True);code.write_text('old implementation')
    source=root/'source.json';save(source,{'source':'retained bytes'})
    ref=lambda p:{'path':str(p.relative_to(root)),'sha256':sha(p)}
    replay=root/'replay.json';save(replay,{'upstream_inputs':[ref(code),ref(source)]})
    prior={'evidence':[ref(source)],'replay':{'dossier':ref(replay)}}
    archive=root/'archive.zip'
    with ZipFile(archive,'w') as z:z.write(code,code.relative_to(root))
    return prior,ref(archive),code,source


def test_historical_check_uses_exact_archived_code_without_replacing_current(tmp_path,monkeypatch):
    prior,archive,code,source=historical_fixture(tmp_path)
    code.write_text('new implementation')
    def verify(snapshot,dossier):
        assert (snapshot/'src/legalmath/example.py').read_text()=='old implementation'
        assert (snapshot/'source.json').read_bytes()==source.read_bytes()
        assert dossier==prior
        return {'historical':'checked'}
    monkeypatch.setattr(scheduling,'verify',verify)
    result=scheduling.historical_replay(tmp_path,prior,archive)
    assert not result['current_implementation_conformance']
    assert result['changed_current_sources']==['src/legalmath/example.py']
    assert code.read_text()=='new implementation'


@pytest.mark.parametrize('changed',['archive','source','archived_code'])
def test_changed_historical_evidence_rejects_before_verification(tmp_path,monkeypatch,changed):
    prior,archive,code,source=historical_fixture(tmp_path)
    if changed=='archive':(tmp_path/archive['path']).write_bytes(b'altered archive')
    elif changed=='source':source.write_text('altered authority')
    else:
        with ZipFile(tmp_path/archive['path'],'w') as z:z.writestr('src/legalmath/example.py','different old implementation')
        archive['sha256']=sha(tmp_path/archive['path'])
    monkeypatch.setattr(scheduling,'verify',lambda *args:pytest.fail('Altered evidence must fail before verification'))
    with pytest.raises(LegalMathError) as exc:scheduling.historical_replay(tmp_path,prior,archive)
    assert exc.value.code=='E_HASH_MISMATCH'


def test_absent_review_does_not_authorize_parallel_continuation(tmp_path):
    assert scheduling.reviewed_pilot(tmp_path,tmp_path) is None


def test_changed_review_rejects_before_historical_check(tmp_path,monkeypatch):
    review=tmp_path/'review.md';review.write_text('reviewed rationale')
    save(tmp_path/'pilot-scheduling.json',{'review':{'path':review.name,'sha256':sha(review)}})
    review.write_text('changed rationale')
    monkeypatch.setattr(scheduling,'historical_replay',lambda *args:pytest.fail('Unbound review'))
    with pytest.raises(LegalMathError) as exc:scheduling.reviewed_pilot(tmp_path,tmp_path)
    assert exc.value.code=='E_HASH_MISMATCH'
