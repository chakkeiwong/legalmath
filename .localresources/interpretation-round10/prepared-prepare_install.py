"""Install the separately tested continuation only after the frozen comparison."""
from pathlib import Path
import shutil
from legalmath.canonical import loads,digest,raw_digest
from legalmath.interpretation.assurance.monitor import save
ROOT=Path('/home/chakwong/python/legalmath');STAGE=Path('/tmp/legalmath-issue-cli')
prepared=[STAGE/name for name in ('public_issue.py','cli.py','run_public_issue_plan.py','audit_public_issue.py','prepare_install.py')]
prepared += [STAGE/'repaired-src/legalmath/interpretation/assurance'/name for name in ('declared_evaluation.py','issue_search.py')]
prepared += list((STAGE/'tests').glob('test_*.py'))
save(STAGE/'prepared-manifest.json',{'status':'PREPARED_FOR_POST_G3_INSTALLATION',
    'files':{str(p.relative_to(STAGE)):raw_digest(p.read_bytes()) for p in prepared}})

state=loads((ROOT/'artifacts/interpretation/round9/state.json').read_bytes())
assert all(v['status']=='PASSED' for v in state['phases'].values())
assert (ROOT/'docs/implementation/interpretation-round9/execution-report.md').is_file()
base=ROOT/'.localresources/interpretation-round10'
archive=base/'round9-implementation';archive.mkdir(parents=True,exist_ok=False)
for folder in ('src','tests','scripts'):
    shutil.copytree(ROOT/folder,archive/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
# Preserve the demonstrated old failures and the isolated repairs as evidence.
for name in ('baseline-discrepancies.xml','repaired-discrepancies.xml','repaired-discrepancies-2.xml','baseline-rejected-reconsideration.xml','repaired-rejected-reconsideration.xml','repaired-deadline.xml','baseline-deadline.xml'):
    shutil.copy2(STAGE/name,base/name)
shutil.copytree(STAGE/'tests',base/'isolated-tests',ignore=shutil.ignore_patterns('__pycache__','.pytest_cache'))
shutil.copytree(STAGE/'repaired-src/legalmath',base/'isolated-repair',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for name in ('public_issue.py','cli.py','run_public_issue_plan.py','audit_public_issue.py','prepare_install.py','h0-review.json','prepared-manifest.json'):
    shutil.copy2(STAGE/name,base/('prepared-'+name))
for name in ('issue_search.py','declared_evaluation.py'):
    shutil.copy2(STAGE/'repaired-src/legalmath/interpretation/assurance'/name,ROOT/'src/legalmath/interpretation/assurance'/name)
shutil.copy2(STAGE/'public_issue.py',ROOT/'src/legalmath/interpretation/assurance/public_issue.py')
shutil.copy2(STAGE/'cli.py',ROOT/'src/legalmath/cli.py')
for name in ('run_public_issue_plan.py','audit_public_issue.py'):
    shutil.copy2(STAGE/name,ROOT/'scripts'/name)
for name in ('test_public_issue.py','test_discrepancy_triggers.py','test_rejected_reconsideration.py','test_declared_evaluation.py','test_public_issue_master.py'):
    text=(STAGE/'tests'/name).read_text()
    text=text.replace("ROOT=Path('/home/chakwong/python/legalmath')","ROOT=Path(__file__).resolve().parents[2]")
    if name=='test_public_issue.py':
        a=text.index('def module():');b=text.index('\n\ndef fixture',a)
        text=text[:a]+'''def module():
    from legalmath.interpretation.assurance import public_issue
    return public_issue
''' +text[b:]
        text=text.replace("spec=importlib.util.spec_from_file_location('legalmath.cli','/tmp/legalmath-issue-cli/cli.py')", "spec=importlib.util.spec_from_file_location('legalmath.cli',ROOT/'src/legalmath/cli.py')")
    (ROOT/'tests/assurance'/name).write_text(text)
source=loads((ROOT/'docs/implementation/interpretation-round8/source.json').read_bytes())
issue=loads((ROOT/'docs/implementation/interpretation-round8/qualification-issue.json').read_bytes())
public={'packet':source['packet'],'issue':issue,'at':'2026-09-24T00:00:00.000000Z'}
save(ROOT/'examples/interpretation-assurance/declared-issue.json',public)
doc=ROOT/'docs/implementation/interpretation-round10';doc.mkdir(parents=True,exist_ok=True)
shutil.copy2(STAGE/'operator-guide.md',doc/'operator-guide.md')
shutil.copy2(STAGE/'h0-review.json',doc/'h0-review.json')
ledger=loads((ROOT/'artifacts/interpretation/round7/live-allowance.json').read_bytes())
assert len(ledger['calls'])+24<=ledger['maximum']==500
save(doc/'authorization.json',{'authority':'User authorized another 500 model calls; this continuation uses the existing grant',
    'allowance_path':'artifacts/interpretation/round7/live-allowance.json','allowance_maximum':500,
    'used_at_preparation':len(ledger['calls']),'maximum_new_calls':24,'public_hash':digest(public),
    'no_refunds':True,'new_grant_created':False})
phases=[('H0','Focused discrepancy, public command and supervisor checks'),
        ('H1','Ordinary public command, bounded live clause investigation and zero-dispatch resume'),
        ('H2','Full regression and final protected-evidence verification')]
save(doc/'master-plan.json',{'version':1,'max_failed_attempts_per_phase':3,'phases':[
    {'id':ident,'executable':True,'tasks':[task],'acceptance':[task,'Current-source review, executed repairs and protected prior evidence']}
    for ident,task in phases]})
protected=loads((ROOT/'.localresources/interpretation-round9/baseline.json').read_bytes())['protected']
for folder in (ROOT/'artifacts/interpretation/round9',ROOT/'docs/implementation/interpretation-round9',base):
    for p in folder.rglob('*'):
        if p.is_file():protected[str(p.relative_to(ROOT))]=raw_digest(p.read_bytes())
p=ROOT/'.localresources/interpretation-round9/baseline.json';protected[str(p.relative_to(ROOT))]=raw_digest(p.read_bytes())
save(base/'baseline.json',{'protected':protected,'allowance_checkpoint_hash':digest(ledger),
    'prior_phase':'G0-G3 all passed; version 1 implementation retained',
    'new_method':'declared-predicate-methods.v2'})
print({'installed':'H0 continuation','protected_files':len(protected),'used':len(ledger['calls']),
       'maximum_additional_calls':24})
