"""Sixty-second read-only diagnostic of current validation; not acceptance."""
from pathlib import Path
from collections import defaultdict
import cProfile,json,signal,sys,time
ROOT=Path('/home/chakwong/python/legalmath');sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
WORK=ROOT/'artifacts/legal-mission-control/2026-10-26/product-closure'
from scripts.legal_mission_execution import read,validate_program
program=read(ROOT/'docs/implementation/legal-mission-control/integration-master.json')
counts=defaultdict(lambda:[0,0,0.0]);original=Path.read_bytes;original_text=Path.read_text
def tracked(p,*a,**k):
    started=time.perf_counter();value=original(p,*a,**k)
    row=counts[str(p)];row[0]+=1;row[1]+=len(value);row[2]+=time.perf_counter()-started
    return value
def tracked_text(p,*a,**k):
    started=time.perf_counter();value=original_text(p,*a,**k)
    row=counts[str(p)];row[0]+=1;row[1]+=len(value);row[2]+=time.perf_counter()-started
    return value
class BoundedDiagnostic(Exception):pass
def end(*args):raise BoundedDiagnostic()
signal.signal(signal.SIGALRM,end);signal.alarm(60)
prof=cProfile.Profile();started=time.perf_counter();complete=False
try:
    Path.read_bytes=tracked;Path.read_text=tracked_text;prof.enable()
    validate_program(program,ROOT);complete=True
except BoundedDiagnostic:pass
finally:
    prof.disable();signal.alarm(0);Path.read_bytes=original;Path.read_text=original_text
    prof.dump_stats(str(WORK/'validation-profile.pstats'))
    value=dict(complete=complete,diagnostic_only=True,elapsed=time.perf_counter()-started,
        total_reads=sum(r[0] for r in counts.values()),unique_paths=len(counts),
        total_bytes=sum(r[1] for r in counts.values()),
        top_reads=sorted([dict(path=p,reads=r[0],bytes=r[1],read_seconds=r[2]) for p,r in counts.items()],
            key=lambda r:r['bytes'],reverse=True)[:20])
    (WORK/'validation-profile.json').write_text(json.dumps(value,indent=2))
    print(json.dumps(value,indent=2))
