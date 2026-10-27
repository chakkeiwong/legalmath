from pathlib import Path
import json
import shutil
ROOT=Path('/home/chakwong/python/legalmath')
WORK=ROOT/'artifacts/legal-mission-control/2026-10-26/repaired-retry-continuation'
TREE=Path('/tmp/legalmath-repaired-retry-continuation')
import sys
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts.legal_mission_execution import ref,save
path=WORK/'tests-staged.xml'
if path.exists() and not (WORK/'tests-first-environment.xml').exists():
    shutil.copyfile(path,WORK/'tests-first-environment.xml')
value=json.loads((WORK/'preparation.json').read_text())
for name in value['sources']:
    source=WORK/'source'/name
    compile(source.read_text(),name,'exec')
    shutil.copyfile(source,TREE/name)
    value['sources'][name]=ref(ROOT,source)
save(WORK/'preparation.json',value)
print('Candidate synchronized; first failed test report preserved.')
