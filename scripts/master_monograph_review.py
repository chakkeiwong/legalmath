"""Execute the reversible monograph review and retain a stage manifest.

This is an evidence-producing orchestrator, not an autonomous legal certifier.
It fails closed on build, preservation, citation, mathematics or focused-test
errors. A successful run still leaves human and independent legal acceptance
pending.
"""
from __future__ import annotations
from pathlib import Path
import hashlib
import json
import os
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT/'docs/monograph/review/revision'


def run_stage(name, command, *, timeout=900, env=None):
    started = time.time()
    log = REVIEW/(f'master-{name}.log')
    try:
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=timeout, env=env)
        stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ''
        stderr = exc.stderr or ''
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors='replace')
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors='replace')
        stderr += f'\nStage exceeded {timeout} seconds.'
        code = 124
    except OSError as exc:
        stdout, stderr, code = '', str(exc), 127
    log.write_text(stdout + ('\nSTDERR\n' + stderr if stderr else ''))
    return {'name':name, 'command':command, 'exit_code':code,
            'wall_seconds':time.time()-started, 'log':str(log.relative_to(ROOT)),
            'stdout_sha256':hashlib.sha256(stdout.encode()).hexdigest(),
            'stderr_sha256':hashlib.sha256(stderr.encode()).hexdigest()}


def execute_stages(specifications):
    results = []
    for name, command, options in specifications:
        result = run_stage(name, command, **options)
        results.append(result)
        if result['exit_code']:
            break
    return results


def main():
    REVIEW.mkdir(parents=True, exist_ok=True)
    started = time.time()
    py = sys.executable
    math_py = '/home/chakwong/miniconda3/envs/mathdevmcp-backends/bin/python'
    math_env = dict(os.environ, PYTHONPATH='/home/chakwong/python/MathDevMCP/src', PYTHONDONTWRITEBYTECODE='1', CUDA_VISIBLE_DEVICES='-1')
    test_py = str(ROOT/'.venv/bin/python') if (ROOT/'.venv/bin/python').exists() else py
    test_env = dict(os.environ, PYTHONPATH=str(ROOT/'src'), CUDA_VISIBLE_DEVICES='-1')
    specifications = [
        ('reversible-text-edits', [py, 'scripts/revise_monograph_text.py'], {}),
        ('build-and-structural-check', [py, 'scripts/build_unified_monograph.py'], {'timeout':1200}),
        ('inventory', [py, 'scripts/audit_monograph_revision.py', 'inventory'], {}),
        ('citation-packets', [py, 'scripts/prepare_monograph_citation_packets.py'], {}),
        ('citation-bind', [py, 'scripts/bind_monograph_citation_claims.py'], {}),
        ('citation-validate', [py, 'scripts/check_monograph_citations.py'], {}),
        ('math-document-rigor', [math_py, '-m', 'mathdevmcp.cli', 'audit-math-document-rigor',
        'docs/monograph/review/revision/expanded.tex', '--max-labels', '100', '--output-md',
        'docs/monograph/review/revision/mathdevmcp-final.md', '--output-json',
        'docs/monograph/review/revision/mathdevmcp-final.json'], {'timeout':600, 'env':math_env}),
        ('math-obligations', [math_py, 'scripts/check_monograph_mathematics.py'], {'timeout':300, 'env':math_env}),
        ('preservation', [py, 'scripts/check_unified_monograph.py'], {}),
        ('final-verify', [py, 'scripts/audit_monograph_revision.py', 'verify'], {}),
        ('evidence-artifacts', [py, 'scripts/check_monograph_evidence_artifacts.py'], {}),
        ('focused-tests', [test_py, '-m', 'pytest', 'tests/security', 'tests/interpretation/test_release_binding.py', 'tests/integration/test_host_transactions.py', '-q'], {'timeout':600, 'env':test_env})]
    stages = execute_stages(specifications)
    failed = [s for s in stages if s['exit_code'] != 0]
    pdf = ROOT/'docs/monograph/monograph.pdf'
    manifest = {
        'program': 'scripts/master_monograph_review.py',
        'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(started)),
        'finished_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'wall_seconds': time.time()-started,
        'git_commit': subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
        'environment': {'python':sys.executable, 'python_version':platform.python_version(), 'platform':platform.platform(), 'cpu_only':'GPU intentionally unused'},
        'plan': 'docs/plans/monograph-review-rewrite-program.md',
        'stages': stages, 'status': 'FAIL' if failed else 'PASS_WITH_LIMITS',
        'failed_stages': [s['name'] for s in failed],
        'skipped_stages': [s[0] for s in specifications[len(stages):]],
        'artifacts': {
            'pdf':'docs/monograph/monograph.pdf',
            'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest() if pdf.exists() else None,
            'citation_claims':'docs/monograph/review/revision/citation-claims.json',
            'occurrence_review':'docs/monograph/review/revision/citation-occurrence-review.json',
            'citation_validation':'docs/monograph/review/revision/citation-validation.json',
            'math_report':'docs/monograph/review/revision/mathdevmcp-final.json',
            'literature_assumption_audit':'docs/monograph/review/revision/mathdevmcp-prose-audit.json',
            'currentness':'docs/monograph/review/revision/regulator-currentness.json',
            'evidence_artifacts':'docs/monograph/review/revision/evidence-artifact-validation.json',
            'preservation':'docs/monograph/review/revision/verification.json'},
        'acceptance_boundary':'PASS_WITH_LIMITS means the staged checks completed. It does not establish legal correctness, regulatory approval, production security, statistical performance, or human-reader acceptance.'}
    (REVIEW/'master-execution-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({'status':manifest['status'], 'failed_stages':manifest['failed_stages'], 'pdf_sha256':manifest['artifacts']['pdf_sha256']}, indent=2))
    return bool(failed)


if __name__ == '__main__':
    raise SystemExit(main())
