"""Fresh BASF agent-change consumer with exact-source and omission evidence."""
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
REL = 'docs/implementation/prospectus-integration-closure/basf-agent-notices'
PLAN = 'docs/plans/prospectus-basf-agent-notices-2026-10-10.md'


def prepared_request(root, graph=None, packet=None):
    from scripts.prospectus_closure_basf_notices import prepared_request as notice_request
    from legalmath.prospectus.successor import basf, basf_agents, jobs, source_graph
    from legalmath.prospectus.successor.contracts import digest, read
    root = Path(root)
    packet = read(root / REL / 'review.json') if packet is None else packet
    for path, sha in packet['images'].items():
        if digest((root / path).read_bytes()) != sha:
            raise ValueError('Agent reviewed source image changed')
    graph = source_graph.build(jobs.basf_request(root)['bundle'], root) if graph is None else graph
    request = notice_request(root, graph)
    construction = basf.construct(graph, read(root / jobs.BASF))
    assembly = basf.as_assembly(graph, construction, request['construction']['scalar_admission'])
    return basf_agents.prepare(graph, construction, assembly, request, packet)


def check_report(report, request, packet, scalar_check=None, notice_packet=None):
    if scalar_check is None:
        from scripts.prospectus_closure_basf import check_report as scalar_check
    from legalmath.prospectus.successor.basf_agents import check_meanings
    from legalmath.prospectus.successor import basf_notices
    from legalmath.prospectus.successor.contracts import read, digest
    if notice_packet is None:
        notice_packet = read(ROOT / 'docs/implementation/prospectus-integration-closure/basf-notices/review.json')
    if digest(notice_packet['clauses']) != packet['notice_clauses_sha256']:
        raise ValueError('Prior notice meanings changed')
    outcome = scalar_check(report, request)
    if request['reference_admission']['references'][-1:] != packet['references']:
        raise ValueError('Agent request lost its reviewed complete reference')
    return {**outcome, 'reviewed_references': len(request['reference_admission']['references']),
            'notices': basf_notices.check_meanings(report, request, notice_packet['clauses']),
            'agents': check_meanings(report, request, packet['clauses'])}


def main():
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    python = ROOT / '.venv/bin/python'
    if Path(sys.executable).absolute() != python.absolute():
        os.execv(str(python), [str(python), '-m', 'scripts.prospectus_closure_basf_agent_notices', *sys.argv[1:]])
    sys.path.insert(0, str(ROOT / 'src'))
    from legalmath.prospectus.successor import basf_agents, service
    from legalmath.prospectus.successor.contracts import digest, read, write
    folder = ROOT / REL / f'attempt-{len(list((ROOT / REL).glob("attempt-*"))) + 1:03d}'
    folder.mkdir()
    paths = [ROOT / PLAN, ROOT / REL / 'review.json', Path(__file__), ROOT / 'scripts/prospectus_closure_basf.py',
             ROOT / 'scripts/prospectus_closure_basf_notices.py', ROOT / 'scripts/author_basf_agents_packet.py',
             *sorted((ROOT / 'src/legalmath/prospectus/successor').glob('*.py')),
             *[ROOT / 'docs/implementation/prospectus-integration-closure' / name / 'review.json'
               for name in ('basf-notices', 'basf-consumer', 'basf-scalars')]]
    method = {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in paths}
    tick = time.monotonic()
    write(folder / 'started.json', {'command': ['python3', '-m', 'scripts.prospectus_closure_basf_agent_notices'],
        'plan': PLAN, 'method': method, 'cpu_gpu': 'CPU; CUDA_VISIBLE_DEVICES=-1', 'timeout_seconds': 600,
        'evidence_limit_bytes': 20_000_000, 'metadata_reserve_bytes': 1_048_576})
    try:
        packet = read(ROOT / REL / 'review.json')
        write(folder / 'review.json', packet)
        request = prepared_request(ROOT, packet=packet)
        request_bytes = json.dumps(request, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()
        (folder / 'request.json.gz').write_bytes(gzip.compress(request_bytes, mtime=0))
        report = service.assess(request, ROOT)
        outcome = check_report(report, request, packet)
        p1 = service.seal('P1', request['bundle'], {'request': digest(request)}, {'request': request, 'graph': report['source_map']})
        p2 = service.seal('P2', request['bundle'], {'P1': p1['sha256']}, {'assembly': report['assembly'], 'selected_contract': report['selected_contract']})
        omitted = service.interpretation_product(p1, p2, {
            'clauses': basf_agents.omitted_clauses(report['assembly'], request)})['payload']
        matched = basf_agents.matched_omission(report['assembly'], report['clause_graph'], omitted['clauses'], packet['clauses'])
        if [omitted['questions'][q]['status'] for q in ('Q1', 'Q2', 'Q3')] != ['UNKNOWN', 'UNKNOWN', 'PARTIAL']:
            raise ValueError('Agent omission control promoted incomplete BASF interpretation')
        write(folder / 'meaning-evidence.json', {'packet_sha256': digest(packet), 'clauses': packet['clauses'],
            'matched_omission': matched, 'scope': 'Development agent reading preserved; actual change validity not evaluated'})
        write(folder / 'consumer.json', {'outcome': outcome, 'dependencies': report['dependencies'],
            'report_sha256': digest(report), 'assembly_sha256': digest(report['assembly']),
            'clause_graph_sha256': digest(report['clause_graph']), 'matched_omission': matched})
        if method != {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in paths}:
            raise ValueError('Agent method changed during execution')
        if time.monotonic() - tick > 600:
            raise TimeoutError('Agent consumer exceeded 600 seconds')
        size = sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())
        if size + 1_048_576 > 20_000_000:
            raise ValueError('Agent evidence exceeded budget')
        result = {'status': 'PASS', 'outcome': outcome, 'matched_omission': matched,
                  'request_sha256': digest(request), 'request_storage': 'lossless JSON gzip; mtime=0',
                  'evidence_payload_bytes': size, 'evidence_limit_bytes': 20_000_000}
    except Exception as exc:
        result = {'status': 'FAIL', 'error': type(exc).__name__ + ': ' + str(exc)}
    result.update(plan=PLAN, command=['python3', '-m', 'scripts.prospectus_closure_basf_agent_notices'], method=method,
        git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        environment={'python': sys.executable, 'version': sys.version, 'source': str(ROOT / 'src')},
        cpu_gpu='CPU; GPU intentionally hidden with CUDA_VISIBLE_DEVICES=-1',
        seeds='N/A; deterministic source/meaning controls', wall_seconds=time.monotonic() - tick)
    write(folder / 'result.json', result)
    write(folder / 'manifest.json', {'files': {str(p.relative_to(folder)): digest(p.read_bytes()) for p in folder.rglob('*') if p.is_file()}})
    print({'directory': str(folder.relative_to(ROOT)), 'status': result['status'], 'error': result.get('error')})
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
