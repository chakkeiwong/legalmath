"""Correct only identical diagnostic-reference paths in the uninstalled candidate."""
from pathlib import Path
import shutil
ROOT=Path('/home/chakwong/python/legalmath');WORK=ROOT/'artifacts/legal-mission-control/2026-10-26/repaired-retry-continuation'
path=WORK/'source/src/legalmath/interpretation/assurance/phased/retry_checkpoint.py'
body=path.read_text()
old='''def equivalent(previous, current, checkpoint, row):
    if capacity_policy.annotate(previous) == capacity_policy.annotate(current):
        return True
    return (checkpoint.get('retry_profile') == PROFILE
        and row['mode'] in ('VALIDATED','REVIEWED_FAILURE_RETRY')
        and normalized(previous) == normalized(current))
'''
new='''def equivalent(previous, current, checkpoint, row, root=None):
    if capacity_policy.annotate(previous) == capacity_policy.annotate(current):
        return True
    if checkpoint.get('retry_profile') != PROFILE or row['mode'] not in ('VALIDATED','REVIEWED_FAILURE_RETRY'):
        return False
    left,right=normalized(previous),normalized(current)
    # An identical local diagnostic may move with the fresh runtime. Verify both
    # files before restoring its old pointer; no substantive prompt field changes.
    a=left.get('payload',{}).get('invalid_review_repair',{}).get('full_diagnostic') if isinstance(left.get('payload'),dict) else None
    b=right.get('payload',{}).get('invalid_review_repair',{}).get('full_diagnostic') if isinstance(right.get('payload'),dict) else None
    if a and b and a != b and root is not None and a['sha256']==b['sha256']:
        read_evidence(a,root,json_value=False);read_evidence(b,root,json_value=False)
        right['payload']['invalid_review_repair']['full_diagnostic']=a
    return left==right
'''
assert body.count(old)==1;path.write_text(body.replace(old,new))
path=WORK/'source/src/legalmath/interpretation/assurance/phased/capacity_checkpoint.py';body=path.read_text()
old='if not equivalent(request, wanted, checkpoint, candidate):'
assert body.count(old)==1;path.write_text(body.replace(old,'if not equivalent(request, wanted, checkpoint, candidate, product.root):'))
path=WORK/'source/tests/assurance/test_repaired_retry_continuation.py'
body=path.read_text()+'''

def test_identical_diagnostic_relocation_keeps_request_but_changed_content_does_not(tmp_path,monkeypatch):
    monkeypatch.setattr(retry.capacity_policy,'annotate',lambda x:deepcopy(x))
    (tmp_path/'old.json').write_text('fixed diagnostic')
    (tmp_path/'new.json').write_text('fixed diagnostic')
    old=dict(task='AUDIT_SOURCE_DEPENDENCY_ASSIGNMENTS',payload={'invalid_review_repair':
        {'full_diagnostic':evidence_file(tmp_path/'old.json',tmp_path),'reason':'fixed'}})
    current=deepcopy(old);current['payload']['invalid_review_repair']['full_diagnostic']=evidence_file(tmp_path/'new.json',tmp_path)
    checkpoint={'retry_profile':retry.PROFILE};row={'mode':'VALIDATED'}
    assert retry.equivalent(old,current,checkpoint,row,tmp_path)
    current['payload']['invalid_review_repair']['reason']='changed'
    assert not retry.equivalent(old,current,checkpoint,row,tmp_path)
    current['payload']['invalid_review_repair']['reason']='fixed'
    (tmp_path/'new.json').write_text('changed diagnostic')
    with pytest.raises(LegalMathError):retry.equivalent(old,current,checkpoint,row,tmp_path)
'''
path.write_text(body)
for name in ('tests-staged.xml','staged-verification.json'):
    p=WORK/name
    if p.exists():shutil.copyfile(p,WORK/('before-diagnostic-'+name))
print('Final diagnostic-reference correction applied to staged candidate only.')
