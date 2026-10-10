"""Bounded BASF status/pledge consumer and exact missing-definition effect."""
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
REL = 'docs/implementation/prospectus-integration-closure/basf-status-pledge'
PLAN = 'docs/plans/prospectus-basf-status-pledge-execution-2026-10-10.md'


def prepared_request(root, graph=None, packet=None):
    from scripts.prospectus_closure_basf_amount_holder import prepared_request as amount_request
    from legalmath.prospectus.successor import basf, basf_status_pledge, jobs, source_graph
    from legalmath.prospectus.successor.contracts import digest, read
    root = Path(root)
    packet = read(root / REL / 'review.json') if packet is None else packet
    for path, sha in packet['images'].items():
        if digest((root / path).read_bytes()) != sha:
            raise ValueError('Pledge reviewed source image changed')
    graph = source_graph.build(jobs.basf_request(root)['bundle'], root) if graph is None else graph
    request = amount_request(root, graph)
    construction = basf.construct(graph, read(root / jobs.BASF))
    assembly = basf.as_assembly(graph, construction, request['construction']['scalar_admission'])
    return basf_status_pledge.prepare(graph, construction, assembly, request, packet)


def check_report(report, request, packet, *, amount_packet=None, amount_check=None, **prior_checks):
    if amount_check is None:
        from scripts.prospectus_closure_basf_amount_holder import check_report as amount_check
    from legalmath.prospectus.successor import basf_status_pledge
    from legalmath.prospectus.successor.contracts import read
    if amount_packet is None:
        amount_packet = read(ROOT / 'docs/implementation/prospectus-integration-closure/basf-amount-holder/review.json')
    pledge = basf_status_pledge.check_meanings(report, request, packet)
    outcome = amount_check(report, request, amount_packet, **prior_checks)
    return {**outcome, 'status_pledge': pledge}


def main():
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    python = ROOT / '.venv/bin/python'
    if Path(sys.executable).absolute() != python.absolute():
        os.execv(str(python), [str(python), '-m', 'scripts.prospectus_closure_basf_status_pledge', *sys.argv[1:]])
    sys.path.insert(0, str(ROOT / 'src'))
    from legalmath.prospectus.successor import basf_status_pledge, service
    from legalmath.prospectus.successor.contracts import digest, read, write
    folder = ROOT / REL / f'attempt-{len(list((ROOT / REL).glob("attempt-*"))) + 1:03d}'
    folder.mkdir()
    paths = [ROOT / PLAN, ROOT / REL / 'review.json', Path(__file__),
             ROOT / 'scripts/author_basf_status_pledge_packet.py', ROOT / REL / 'SOURCE-REVIEW.md',
             ROOT / REL / 'OPTION-COMPARISON-CORRECTION.md',
             ROOT / 'scripts/prospectus_closure_basf.py', ROOT / 'scripts/prospectus_closure_basf_notices.py',
             ROOT / 'scripts/prospectus_closure_basf_agent_notices.py', ROOT / 'scripts/prospectus_closure_basf_agent_capacity.py',
             ROOT / 'scripts/prospectus_closure_basf_global_exchange.py', ROOT / 'scripts/prospectus_closure_basf_global_records.py',
             ROOT / 'scripts/prospectus_closure_basf_amount_holder.py',
             *sorted((ROOT / 'src/legalmath/prospectus/successor').glob('*.py')),
             *[ROOT / 'docs/implementation/prospectus-integration-closure' / name / 'review.json'
               for name in ('basf-notices', 'basf-agent-notices', 'basf-agent-capacity', 'basf-global-exchange', 'basf-global-records', 'basf-amount-holder', 'basf-consumer', 'basf-scalars')]]
    method = {str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in paths}
    tick = time.monotonic()
    command = [str(python), '-m', 'scripts.prospectus_closure_basf_status_pledge']
    write(folder / 'started.json', {'command': command, 'plan': PLAN, 'method': method,
                                   'cpu_gpu': 'CPU; CUDA_VISIBLE_DEVICES=-1', 'timeout_seconds': 1200,
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
        matched = {}
        definition_effect = None
        for node in packet['clauses']:
            omitted = service.interpretation_product(p1, p2, {
                'clauses': basf_status_pledge.omitted_clauses(report['assembly'], request, node['id'])})['payload']
            matched[node['id']] = basf_status_pledge.matched_omission(
                report['assembly'], report['clause_graph'], omitted['clauses'], [node])
            retained_ids = set(basf_status_pledge.PRIOR_IDS) | (set(basf_status_pledge.PARAGRAPHS) - {node['id']})
            if ([n for n in omitted['clauses']['nodes'] if n['id'] in retained_ids] !=
                    [n for n in report['clause_graph']['nodes'] if n['id'] in retained_ids] or
                    [omitted['questions'][q]['status'] for q in ('Q1', 'Q2', 'Q3')] != ['UNKNOWN', 'UNKNOWN', 'PARTIAL']):
                raise ValueError('Pledge omission changed other meanings or promoted incomplete questions')
            if node['id'] == basf_status_pledge.DEFINITION:
                definition_effect = basf_status_pledge.matched_missing_definition(report, omitted)
        if definition_effect is None:
            raise ValueError('Missing required real definition omission')
        write(folder / 'meaning-evidence.json', {'packet_sha256': digest(packet), 'clauses': packet['clauses'],
            'prior_clauses_sha256': packet['prior_clauses_sha256'], 'matched_omission': matched,
            'matched_missing_definition': definition_effect,
            'scope': 'Three complete German Option I development readings and supplied definition edge; actual priority/compliance/recovery not evaluated'})
        write(folder / 'consumer.json', {'outcome': outcome, 'dependencies': report['dependencies'],
            'report_sha256': digest(report), 'assembly_sha256': digest(report['assembly']),
            'clause_graph_sha256': digest(report['clause_graph']), 'matched_omission': matched,
            'matched_missing_definition': definition_effect})
        if method != {str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in paths}:
            raise ValueError('Pledge method changed during execution')
        if time.monotonic() - tick > 1200:
            raise TimeoutError('Pledge consumer exceeded 1200 seconds')
        size = sum(path.stat().st_size for path in folder.rglob('*') if path.is_file())
        if size + 1_048_576 > 20_000_000:
            raise ValueError('Pledge evidence exceeded budget')
        result = {'status': 'PASS', 'outcome': outcome, 'matched_omission': matched,
                  'matched_missing_definition': definition_effect,
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
