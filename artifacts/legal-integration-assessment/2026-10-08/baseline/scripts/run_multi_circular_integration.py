#!/usr/bin/env python3
"""Run offline circular verification; preserve exact inputs, reports and history."""
import argparse
from datetime import datetime, timezone
from importlib.metadata import version
import json
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from legalmath.canonical import raw_digest
from legalmath.interpretation.reports import Reports
from legalmath.interpretation.service import Interpretations
from legalmath.storage import Database
from legalmath.storage.archive import export_history, import_history
from tests.integration.multi_circular_support import run_suite, write


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/interpretation/multi-circular-round1/attempt-03/report.json')
    parser.add_argument('--jdk', type=Path, default=ROOT / '.localresources/java-toolchain/jdk-17.0.20.1+1')
    args = parser.parse_args()
    out = args.output.resolve().parent
    if out.exists() and any(out.iterdir()):
        raise RuntimeError('Use a fresh evidence directory; prior attempts are immutable.')
    out.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    paths = [ROOT / 'scripts/run_multi_circular_integration.py', ROOT / 'tests/integration/multi_circular_support.py',
             ROOT / 'tests/integration/test_multi_circular_interpretation.py', ROOT / 'pyproject.toml']
    paths += [p for base in ('src/legalmath', 'examples/multi-circular-2026') for p in (ROOT/base).rglob('*')
              if p.is_file() and '__pycache__' not in p.parts]
    freeze=json.loads((ROOT/'examples/multi-circular-2026/source-freeze.json').read_bytes())
    paths += [ROOT / item['raw_path'] for item in freeze['sources']]
    input_hashes={str(p.relative_to(ROOT)):raw_digest(p.read_bytes()) for p in sorted(set(paths))}
    for name, expected in input_hashes.items():
        retained = (ROOT / name).read_bytes()
        assert raw_digest(retained) == expected
        destination = out / 'inputs' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(retained)
    manifest=dict(status='RUNNING',started_at_utc=datetime.now(timezone.utc).isoformat(),argv=[sys.executable,*sys.argv],
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        working_tree_status=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).splitlines(),
        environment=dict(python=sys.version,executable=sys.executable,platform=platform.platform(),
            packages={p:version(p) for p in ('pydantic','jsonschema','pypdf','pytest')},
            jdk=str(args.jdk.resolve()),javac=subprocess.check_output([str(args.jdk/'bin/javac'),'-version'],text=True,timeout=10).strip()),
        device='CPU only; no GPU/ML framework invoked',seeds='N/A: deterministic named scenarios',
        plan='docs/plans/multi-circular-integration-2026-09-23.md',
        result_note='docs/implementation/interpretation-round1/multi-circular-result.md',
        input_sha256=input_hashes,data_version=raw_digest((ROOT/'examples/multi-circular-2026/source-freeze.json').read_bytes()))
    write(out/'run-manifest.json',manifest)
    try:
        result=run_suite(ROOT,out,jdk=args.jdk)
        archived=export_history(Database(out/'work/db'),out/'history.zip')
        restored=import_history(out/'history.zip',out/'work/restored')
        svc=Interpretations(restored)
        for run in result['runs']:
            assert Reports(svc).verify('meaning',run['run_id'])==run['report_hash']
        assert all(raw_digest((ROOT/name).read_bytes())==h for name,h in input_hashes.items()), 'Inputs changed while running'
        result['history_archive']=archived
        result['history_roundtrip_verified']=True
        write(args.output,result)
        manifest['status']='PASSED'
        print(json.dumps({'output':str(args.output),'scenarios':result['total_scenarios'],
            'compiled_mutants_detected':result['compiled_mutants_detected'],'verdict':result['engineering_verdict']},indent=2))
    except Exception as exc:
        manifest['status']='FAILED'
        write(out/'failure.json',dict(exception=type(exc).__name__,message=str(exc),traceback=traceback.format_exc()))
        raise
    finally:
        manifest['wall_seconds']=round(time.monotonic()-started,3)
        manifest['finished_at_utc']=datetime.now(timezone.utc).isoformat()
        manifest['output_sha256']={str(p.relative_to(out)):raw_digest(p.read_bytes()) for p in sorted(out.rglob('*'))
            if p.is_file() and 'work' not in p.relative_to(out).parts and p.name!='run-manifest.json'}
        write(out/'run-manifest.json',manifest)


if __name__=='__main__': main()
