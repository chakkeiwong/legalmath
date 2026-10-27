"""Run required exact mission commands once and retain their results."""
from pathlib import Path
from datetime import datetime,timezone
import json,subprocess,time
ROOT=Path('/home/chakwong/python/legalmath')
WORK=ROOT/'artifacts/legal-mission-control/2026-10-26/product-closure'
rows=[]
for action in ('check','status','admit'):
    command=['.venv/bin/python','scripts/legal_mission_control.py',action]
    started=time.monotonic()
    with (WORK/(action+'.stdout')).open('x') as out,(WORK/(action+'.stderr')).open('x') as err:
        code=subprocess.call(command,cwd=ROOT,stdout=out,stderr=err)
    row=dict(command=command,exit_code=code,elapsed_seconds=time.monotonic()-started,
        at_utc=datetime.now(timezone.utc).isoformat())
    rows.append(row);(WORK/'admission-results.json').write_text(json.dumps(rows,indent=2))
    print(json.dumps(row),flush=True)
    if code:raise SystemExit(code)
