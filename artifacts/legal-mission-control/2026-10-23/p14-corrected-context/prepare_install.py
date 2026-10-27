"""Freeze the exact locally checked source identities before the idle handover."""
from hashlib import sha256
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[4]
CANDIDATE=Path('/tmp/legalmath-p14-corrected-context-20261023')
sys.path.insert(0,str(ROOT))
from scripts import legal_review_context_isolation as isolation
from scripts.legal_mission_execution import read,save,ref,require

suite=ET.parse(ROOT/isolation.HERE/'deployment-tests.xml').getroot()
leaves=list(suite.iter('testsuite'))
require(leaves and sum(int(s.attrib['tests']) for s in leaves)==68
    and all(int(s.attrib.get('failures',0))==int(s.attrib.get('errors',0))==int(s.attrib.get('skipped',0))==0
    for s in leaves), 'The focused deployment checks must all pass')
rows=[]
for relative in isolation.CHANGED+isolation.ADDED:
    source=(CANDIDATE if relative in isolation.CHANGED else ROOT)/relative
    require(not source.is_symlink(), 'Symlink candidate is not reviewed')
    data=source.read_bytes()
    compile(data,str(source),'exec')
    rows.append(dict(path=relative,sha256=sha256(data).hexdigest(),
        current=ref(ROOT,relative)))
value=dict(profile='corrected-context-install-candidate.v1', files=rows,
    tests=ref(ROOT,isolation.HERE/'deployment-tests.xml'),review=ref(ROOT,isolation.REVIEW),
    provider_calls=0,legal_acceptance=False)
save(ROOT/isolation.HERE/'candidate-source.json',value)
print({'prepared':True,'checked_files':len(rows),'passing_tests':68,'provider_calls':0})
