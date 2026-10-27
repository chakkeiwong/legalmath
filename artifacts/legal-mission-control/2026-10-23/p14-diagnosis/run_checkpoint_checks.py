"""Run the exact required local refresh and status, preserving full output."""
from datetime import datetime, timezone
from pathlib import Path
import json
import subprocess
import time

ROOT=Path('/home/chakwong/python/legalmath')
OUT=Path(__file__).resolve().parent
commands=[('refresh',['.venv/bin/python','scripts/legal_mission_control.py','refresh']),
    ('master-status',['.venv-context/bin/python','scripts/legal_integration_master.py','status'])]
rows=[]
for name,command in commands:
    start=time.monotonic()
    with (OUT/(name+'.stdout')).open('w') as stdout,(OUT/(name+'.stderr')).open('w') as stderr:
        result=subprocess.run(command,cwd=ROOT,stdout=stdout,stderr=stderr,timeout=900)
    row=dict(name=name,command=command,returncode=result.returncode,seconds=time.monotonic()-start)
    rows.append(row)
    print(json.dumps(row),flush=True)
    if result.returncode: break
value=dict(at_utc=datetime.now(timezone.utc).isoformat(),commands=rows,provider_calls=0)
status=OUT/'master-status.stdout'
if status.exists():
    try:
        data=json.loads(status.read_text())
        value['frontier']={k:data.get(k) for k in ('execution','ready','running','local_deadline')}
        value['blocked_count']=len(data.get('blocked',{}))
    except ValueError: value['status_parse_failed']=True
(OUT/'checkpoint-validation.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps(value,indent=2),flush=True)
