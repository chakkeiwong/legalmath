"""Executed checks for the reviewed interpretation-assurance revision."""
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
from run_assurance_gap_master import ROOT, OUT, PLAN, PYTHON, command, save, read, sha, receipt


def junit(path):
    tree = ET.parse(path).getroot()
    suites = [tree] if tree.tag == 'testsuite' else list(tree.iter('testsuite'))
    result = {name: sum(int(s.get(name, 0)) for s in suites) for name in ('tests','failures','errors','skipped')}
    if result['failures'] or result['errors'] or result['skipped']: raise RuntimeError('Nonpassing or skipped required checks')
    return result


def tests(work, names, *, cwd=ROOT, timeout=1800):
    command([PYTHON,'-m','pytest','-q',*names,'--junitxml='+str(work/'tests.xml')], work, 'tests', cwd=cwd, timeout=timeout)
    return junit(work/'tests.xml')


def G0(work):
    baseline = read(OUT/'manuscript-baseline.json')
    if sha(OUT/'manuscript-baseline.zip') != baseline['archive_sha256']: raise RuntimeError('Changed manuscript baseline')
    with ZipFile(OUT/'manuscript-baseline.zip') as archive:
        for name in archive.namelist():
            old = archive.read(name).decode().splitlines(); current = iter((ROOT/name).read_text().splitlines())
            if not all(any(line == candidate for candidate in current) for line in old):
                raise RuntimeError('Inspect removed manuscript content: '+name)
    # Isolate the document build so it cannot replace the delivered PDFs early.
    from run_executable_reference_master import snapshot
    target, frozen = snapshot(work, 'gap-g0-attempt-'+work.name)
    command(['/home/chakwong/miniconda3/envs/tfgpu/bin/python3','scripts/build_reader_facing_monograph.py'],
            work,'manuscript',cwd=target,timeout=240)
    result = {'status':'PLAN_REVIEWED_AND_MANUSCRIPT_BUILT', 'protected_files':len(baseline['files']),
        'snapshot':str(target), 'method_revision':'DEVELOPMENT', 'legal_correctness':'NOT_ESTABLISHED',
        'baseline_tests':2097, 'new_live_allocation':48, 'old_future_pilot_reserved':120}
    save(work/'result.json',result); return result


def G1(work): return tests(work,['tests/assurance/test_challenge_contract.py'])
def G2(work): return tests(work,['tests/assurance/test_conditional_elimination.py'])
def G3(work): return tests(work,['tests/assurance/test_challenge_panel.py'])
def G4(work):
    from run_executable_reference_master import snapshot
    target,frozen=snapshot(work,'gap-integration-'+work.name)
    return {'snapshot':str(target),'tests':tests(work,[
        'tests/assurance/test_challenge_contract.py','tests/assurance/test_conditional_elimination.py',
        'tests/assurance/test_challenge_panel.py','tests/assurance/test_challenge_integration.py',
        'tests/assurance/test_investigation_observations.py','tests/assurance/test_continuation_integration.py',
        'tests/assurance/test_executable_references_v2.py'],cwd=target,timeout=600)}
def G5(work):
    from assurance_gap_evidence import execute
    return execute(work)
def G5r(work):
    from assurance_gap_evidence import repair_acquisition
    return repair_acquisition(work)
def G6(work):
    return tests(work,['tests/assurance/test_challenge_proof.py','tests/assurance/test_challenge_panel.py',
                       'tests/assurance/test_challenge_integration.py'],timeout=240)
def G7(work):
    from assurance_gap_live import execute
    return execute(work)
def G7r(work):
    from assurance_gap_recovery import execute
    return execute(work)
def G8(work):
    from assurance_gap_delivery import verify
    return verify(work)
def deliver():
    from assurance_gap_delivery import deliver as finish
    return finish()
