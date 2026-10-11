"""Bounded BASF contractual-capacity consumer with exact matched omission."""
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
REL = 'docs/implementation/prospectus-integration-closure/basf-agent-capacity'
PLAN = 'docs/plans/prospectus-basf-agent-capacity-2026-10-10.md'


def prepared_request(root, graph=None, packet=None):
    from scripts.prospectus_closure_basf_agent_notices import prepared_request as agent_request
    from legalmath.prospectus.successor import basf, basf_agent_capacity, jobs, source_graph
    from legalmath.prospectus.successor.contracts import digest, read
    root = Path(root)
    packet = read(root / REL / 'review.json') if packet is None else packet
    for path, sha in packet['images'].items():
        if digest((root / path).read_bytes()) != sha:
            raise ValueError('Capacity reviewed source image changed')
    graph = source_graph.build(jobs.basf_request(root)['bundle'], root) if graph is None else graph
    request = agent_request(root, graph)
    construction = basf.construct(graph, read(root / jobs.BASF))
    assembly = basf.as_assembly(graph, construction, request['construction']['scalar_admission'])
    return basf_agent_capacity.prepare(graph, construction, assembly, request, packet)


def check_report(report, request, packet, *, scalar_check=None, notice_packet=None, agent_packet=None, agent_check=None):
    if agent_check is None:
        from scripts.prospectus_closure_basf_agent_notices import check_report as agent_check
    from legalmath.prospectus.successor import basf_agent_capacity
    from legalmath.prospectus.successor.contracts import read
    if agent_packet is None:
        agent_packet = read(ROOT / 'docs/implementation/prospectus-integration-closure/basf-agent-notices/review.json')
    outcome = agent_check(report, request, agent_packet, scalar_check=scalar_check, notice_packet=notice_packet)
    return {**outcome, 'capacity': basf_agent_capacity.check_meanings(report, request, packet)}


def main():
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    python = ROOT / '.venv/bin/python'
    if Path(sys.executable).absolute() != python.absolute():
        os.execv(str(python), [str(python), '-m', 'scripts.prospectus_closure_basf_agent_capacity', *sys.argv[1:]])
    sys.path.insert(0, str(ROOT / 'src'))
    from legalmath.prospectus.successor import basf_agent_capacity, service
    from legalmath.prospectus.successor.contracts import digest, read, write
    folder = ROOT / REL / f'attempt-{len(list((ROOT / REL).glob("attempt-*"))) + 1:03d}'
    folder.mkdir()
    paths = [ROOT / PLAN, ROOT / REL / 'review.json', Path(__file__),
             ROOT / 'scripts/author_basf_capacity_packet.py',
             ROOT / 'scripts/prospectus_closure_basf.py', ROOT / 'scripts/prospectus_closure_basf_notices.py',
             ROOT / 'scripts/prospectus_closure_basf_agent_notices.py',
             *sorted((ROOT / 'src/legalmath/prospectus/successor').glob('*.py')),
             *[ROOT / 'docs/implementation/prospectus-integration-closure' / name / 'review.json'
               for name in ('basf-notices', 'basf-agent-notices', 'basf-consumer', 'basf-scalars')]]
    method = {str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in paths}
    tick = time.monotonic()
    command = [str(python), '-m', 'scripts.prospectus_closure_basf_agent_capacity']
    write(folder / 'started.json', {'command': command, 'plan': PLAN, 'method': method,
                                   'cpu_gpu': 'CPU; CUDA_VISIBLE_DEVICES=-1', 'timeout_seconds': 600,
                                   'evidence_limit_bytes': 20_000_000, 'metadata_reserve_bytes': 1_048_576})
    try:
        packet = read(ROOT / REL / 'review.json')
        write(folder / 'review.json', packet)
        request = prepared_request(ROOT, packet=packet)
        data = json.dumps(request, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()
        (folder / 'request.json.gz').write_bytes(gzip.compress(data, mtime=0))
        report = service.assess(request, ROOT)
        outcome = check_report(report, request, packet)
        p1 = service.seal('P1', request['bundle'], {'request': digest(request)}, {'request': request, 'graph': report['source_map']})
        p2 = service.seal('P2', request['bundle'], {'P1': p1['sha256']},
                          {'assembly': report['assembly'], 'selected_contract': report['selected_contract']})
        omitted = service.interpretation_product(p1, p2, {
            'clauses': basf_agent_capacity.omitted_clauses(report['assembly'], request)})['payload']
        matched = basf_agent_capacity.matched_omission(report['assembly'], report['clause_graph'], omitted['clauses'], packet['clauses'])
        if (basf_agent_capacity.prior_readings(omitted['clauses']['nodes']) !=
                basf_agent_capacity.prior_readings(report['clause_graph']['nodes']) or
                [omitted['questions'][q]['status'] for q in ('Q1', 'Q2', 'Q3')] != ['UNKNOWN', 'UNKNOWN', 'PARTIAL']):
            raise ValueError('Capacity omission changed earlier readings or promoted incomplete questions')
        write(folder / 'meaning-evidence.json', {'packet_sha256': digest(packet), 'clauses': packet['clauses'],
            'prior_clauses_sha256': packet['prior_clauses_sha256'], 'matched_omission': matched,
            'scope': 'Contractual capacity supplied development premise; statutory duties and actual disputes not evaluated'})
        write(folder / 'consumer.json', {'outcome': outcome, 'dependencies': report['dependencies'],
            'report_sha256': digest(report), 'assembly_sha256': digest(report['assembly']),
            'clause_graph_sha256': digest(report['clause_graph']), 'matched_omission': matched})
        if method != {str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in paths}:
            raise ValueError('Capacity method changed during execution')
        if time.monotonic() - tick > 600:
            raise TimeoutError('Capacity consumer exceeded 600 seconds')
        size = sum(path.stat().st_size for path in folder.rglob('*') if path.is_file())
        if size + 1_048_576 > 20_000_000:
            raise ValueError('Capacity evidence exceeded budget')
        result = {'status': 'PASS', 'outcome': outcome, 'matched_omission': matched,
                  'request_sha256': digest(request), 'request_storage': 'lossless JSON gzip; mtime=0',
                  'evidence_payload_bytes': size, 'evidence_limit_bytes': 20_000_000}
    except Exception as exc:
        result = {'status': 'FAIL', 'error': type(exc).__name__ + ': ' + str(exc)}
    result.update(plan=PLAN, command=command, method=method,
        git_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        environment={'python': sys.executable, 'version': sys.version, 'source': str(ROOT / 'src')},
        cpu_gpu='CPU; GPU intentionally hidden with CUDA_VISIBLE_DEVICES=-1',
        seeds='N/A; deterministic source/meaning controls', wall_seconds=time.monotonic() - tick)
    write(folder / 'result.json', result)
    write(folder / 'manifest.json', {'files': {str(path.relative_to(folder)): digest(path.read_bytes())
                                            for path in folder.rglob('*') if path.is_file()}})
    print({'directory': str(folder.relative_to(ROOT)), 'status': result['status'], 'error': result.get('error')})
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
