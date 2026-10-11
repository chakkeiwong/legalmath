"""Bounded BASF amount/form/holder consumer with exact matched omission."""
import gzip
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
REL = 'docs/implementation/prospectus-integration-closure/basf-amount-holder'
PLAN = 'docs/plans/prospectus-basf-amount-holder-execution-2026-10-10.md'


def prepared_request(root, graph=None, packet=None):
    from scripts.prospectus_closure_basf_global_records import prepared_request as records_request
    from legalmath.prospectus.successor import basf, basf_amount_holder, jobs, source_graph
    from legalmath.prospectus.successor.contracts import digest, read
    root = Path(root)
    packet = read(root / REL / 'review.json') if packet is None else packet
    for path, sha in packet['images'].items():
        if digest((root / path).read_bytes()) != sha:
            raise ValueError('Amount reviewed source image changed')
    graph = source_graph.build(jobs.basf_request(root)['bundle'], root) if graph is None else graph
    request = records_request(root, graph)
    construction = basf.construct(graph, read(root / jobs.BASF))
    assembly = basf.as_assembly(graph, construction, request['construction']['scalar_admission'])
    return basf_amount_holder.prepare(graph, construction, assembly, request, packet)


def check_report(report, request, packet, *, records_packet=None, records_check=None, **prior_checks):
    if records_check is None:
        from scripts.prospectus_closure_basf_global_records import check_report as records_check
    from legalmath.prospectus.successor import basf_amount_holder
    from legalmath.prospectus.successor.contracts import read
    if records_packet is None:
        records_packet = read(ROOT / 'docs/implementation/prospectus-integration-closure/basf-global-records/review.json')
    amount = basf_amount_holder.check_meanings(report, request, packet)
    # Validate the full request before making an explicit prior-reference view.
    # The real report and every prior meaning remain unchanged.
    references = request['reference_admission']['references']
    prior = {**request, 'reference_admission': {**request['reference_admission'], 'references': references[:5]}}
    outcome = records_check(report, prior, records_packet, ngn_reference=references[-1], **prior_checks)
    return {**outcome, 'reviewed_references': len(references),
            'target_occurrences': [len(row['targets']) for row in references], 'amount_holder': amount}


def main():
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    python = ROOT / '.venv/bin/python'
    if Path(sys.executable).absolute() != python.absolute():
        os.execv(str(python), [str(python), '-m', 'scripts.prospectus_closure_basf_amount_holder', *sys.argv[1:]])
    sys.path.insert(0, str(ROOT / 'src'))
    from legalmath.prospectus.successor import basf_amount_holder, service
    from legalmath.prospectus.successor.contracts import digest, read, write
    folder = ROOT / REL / f'attempt-{len(list((ROOT / REL).glob("attempt-*"))) + 1:03d}'
    folder.mkdir()
    paths = [ROOT / PLAN, ROOT / REL / 'review.json', Path(__file__),
             ROOT / 'scripts/author_basf_amount_holder_packet.py', ROOT / REL / 'SOURCE-REVIEW.md',
             ROOT / 'scripts/prospectus_closure_basf.py', ROOT / 'scripts/prospectus_closure_basf_notices.py',
             ROOT / 'scripts/prospectus_closure_basf_agent_notices.py', ROOT / 'scripts/prospectus_closure_basf_agent_capacity.py',
             ROOT / 'scripts/prospectus_closure_basf_global_exchange.py', ROOT / 'scripts/prospectus_closure_basf_global_records.py',
             *sorted((ROOT / 'src/legalmath/prospectus/successor').glob('*.py')),
             *[ROOT / 'docs/implementation/prospectus-integration-closure' / name / 'review.json'
               for name in ('basf-notices', 'basf-agent-notices', 'basf-agent-capacity', 'basf-global-exchange', 'basf-global-records', 'basf-consumer', 'basf-scalars')]]
    method = {str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in paths}
    tick = time.monotonic()
    command = [str(python), '-m', 'scripts.prospectus_closure_basf_amount_holder']
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
        for node in packet['clauses']:
            omitted = service.interpretation_product(p1, p2, {
                'clauses': basf_amount_holder.omitted_clauses(report['assembly'], request, node['id'])})['payload']
            matched[node['id']] = basf_amount_holder.matched_omission(
                report['assembly'], report['clause_graph'], omitted['clauses'], [node])
            retained_ids = set(basf_amount_holder.PRIOR_IDS) | (set(basf_amount_holder.PARAGRAPHS) - {node['id']})
            if ([n for n in omitted['clauses']['nodes'] if n['id'] in retained_ids] !=
                    [n for n in report['clause_graph']['nodes'] if n['id'] in retained_ids] or
                    [omitted['questions'][q]['status'] for q in ('Q1', 'Q2', 'Q3')] != ['UNKNOWN', 'UNKNOWN', 'PARTIAL']):
                raise ValueError('Amount omission changed other meanings or promoted incomplete questions')
        missing = {**request['reference_admission'], 'references': request['reference_admission']['references'][:5]}
        omitted_link = service.interpretation_product(p1, p2, {'reference_admission': missing})['payload']
        link_effect = basf_amount_holder.matched_missing_link(report, omitted_link)
        write(folder / 'meaning-evidence.json', {'packet_sha256': digest(packet), 'clauses': packet['clauses'],
            'prior_clauses_sha256': packet['prior_clauses_sha256'], 'matched_omission': matched, 'matched_missing_link': link_effect,
            'scope': 'Three contractual amount/form/holder development premises; complete selected NGN reference; actual balances/ownership/standing not evaluated'})
        write(folder / 'consumer.json', {'outcome': outcome, 'dependencies': report['dependencies'],
            'report_sha256': digest(report), 'assembly_sha256': digest(report['assembly']),
            'clause_graph_sha256': digest(report['clause_graph']), 'matched_omission': matched, 'matched_missing_link': link_effect})
        if method != {str(path.relative_to(ROOT)): digest(path.read_bytes()) for path in paths}:
            raise ValueError('Amount method changed during execution')
        if time.monotonic() - tick > 1200:
            raise TimeoutError('Amount consumer exceeded 1200 seconds')
        size = sum(path.stat().st_size for path in folder.rglob('*') if path.is_file())
        if size + 1_048_576 > 20_000_000:
            raise ValueError('Amount evidence exceeded budget')
        result = {'status': 'PASS', 'outcome': outcome, 'matched_omission': matched, 'matched_missing_link': link_effect,
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
