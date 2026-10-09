"""Actual executor/subprocess outputs versus fresh assessment after mutations."""
import json
from pathlib import Path
import subprocess
import shutil
import tempfile
from hypothesis import given, settings, strategies as st
from scripts.prospectus_closure_fixtures import full_term_fixture
from legalmath.prospectus.successor import closure_program as c, service
from legalmath.prospectus.successor.contracts import read, write


PROBE = '''from pathlib import Path
from legalmath.prospectus.successor import service
from legalmath.prospectus.successor.contracts import read, write

def test_actual_assessment(pytestconfig):
    root = Path(__file__).resolve().parents[2]
    case = root / "docs/implementation/prospectus-integration-closure/inputs/R0/cases"
    try:
        result = {"questions": service.assess(read(case/"request.json"), case)["questions"]}
    except (ValueError, FileNotFoundError) as exc:
        result = {"error": type(exc).__name__ + ": " + str(exc).replace(str(case), "CASE")}
    write(Path(pytestconfig.option.xmlpath).with_name("assessment.json"), result)
'''


@settings(max_examples=5, derandomize=True, deadline=None)
@given(st.lists(st.sampled_from(['source','missing','repair','holding','calendar','corrupt']), min_size=2, max_size=4))
def test_real_executor_sequences_match_clean_recomputation(actions):
    with tempfile.TemporaryDirectory(prefix='closure-controller-check-') as temporary:
        root = Path(temporary)
        shutil.copytree(Path(c.__file__).resolve().parents[2], root/'src/legalmath',
                        ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
        # A real isolated Git baseline supplies the executor's manifest. No
        # repository under development or external remote is modified.
        subprocess.run(['git','init','-q',str(root)],check=True,capture_output=True)
        subprocess.run(['git','-c','user.name=Controller fixture','-c','user.email=fixture@invalid',
                        'commit','--allow-empty','-qm','Isolated controller fixture'],cwd=root,check=True,capture_output=True)
        probe = root/'tests/prospectus_successor/probe.py'
        probe.parent.mkdir(parents=True)
        probe.write_text(PROBE)
        case = root/c.REL/'inputs/R0/cases'
        case.mkdir(parents=True)
        req = full_term_fixture(case)
        source = case/'source.txt'
        original = source.read_bytes()
        write(case/'request.json',req)
        old = c.JOBS['R0']
        c.JOBS['R0'] = ('tests/prospectus_successor/probe.py',None)
        try:
            for index,action in enumerate(['repair',*actions]):
                if action=='source':
                    source.write_bytes(original+b'altered')
                elif action=='missing':
                    source.unlink(missing_ok=True)
                elif action=='repair':
                    source.write_bytes(original)
                elif action=='holding':
                    req['contract_calculation']['premises']['holdings'][0]['principal']='200.2'
                elif action=='calendar':
                    req['contract_calculation']['premises']['calendar']['holidays'].append('2025-01-02')
                elif action=='corrupt':
                    current = next(r for r in c.status(root)['phases'] if r['phase']=='R0')
                    (root/current['directory']/'assessment.json').write_text('corrupted')
                    assert not c.status(root)['phases'][0]['current']
                write(case/'request.json',req)
                # Explicit recovery/mutation record supplies the reason for a
                # new attempt, including when input bytes return to an old value.
                write(root/c.REL/'inputs/R0/recovery.json',{'step':index,'action':action})
                assert not c.status(root)['phases'][0]['current']
                result = c.execute(root,'R0')
                assert result['engineering_checks']=='PASS'
                actual = read(root/result['directory']/'assessment.json')
                try:
                    expected = {'questions':service.assess(req,case)['questions']}
                except (ValueError,FileNotFoundError) as exc:
                    expected = {'error':type(exc).__name__+': '+str(exc).replace(str(case),'CASE')}
                assert actual == expected
                assert c.execute(root,'R0')['reused']
        finally:
            c.JOBS['R0'] = old
