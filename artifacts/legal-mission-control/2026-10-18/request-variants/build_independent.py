"""One bounded source repair; never overwrite retained source or active P10."""
from pathlib import Path

WORK = Path(__file__).resolve().parent
source = (WORK / 'probe.py').read_text()


def replace(before, after, count=1):
    global source
    assert source.count(before) == count, (before, source.count(before))
    source = source.replace(before, after)


replace('from contextlib import contextmanager, ExitStack\n', '')
replace("PLAN = ROOT / 'docs/plans/legal-request-variants-2026-10-18.md'",
        "PLAN = ROOT / 'docs/plans/legal-request-variants-independent-2026-10-18.md'")
replace("AUTH = WORK / 'authorization-final.json'", "AUTH = WORK / 'authorization-independent.json'")
replace("PREFLIGHT = WORK / 'preflight-final.json'", "PREFLIGHT = WORK / 'preflight-independent.json'")
replace("for field in ('grant', 'binding', 'source', 'plan', 'review', 'ledger_before', 'service_scope'):",
        "for field in ('grant', 'binding', 'source', 'plan', 'review', 'ledger_before', 'service_scope', 'original_plan', 'stop_receipt'):")
replace("        before = read(verify(authorization['ledger_before']))", """        stage = read(verify(read(allowance.grant_path.with_name('current-stage.json'))))
        need(stage.get('profile') == 'integration-current-stage.v2'
             and stage['grant_hash'] == state['grant_hash']
             and stage['binding_hash'] == digest(read(verify(authorization['binding']))),
             'Concurrent diagnostic requires authenticated v2 stage accounting')
        before = read(verify(authorization['ledger_before']))""")
replace("    elif classification == 'VALID_STRUCTURED_RESPONSE':\n        allowance.service_circuit(success=True)\n",
        '    # Diagnostic success owns no recovery and must not clear another probe.\n')
replace("entry_id = 'request-variants-20261018-final'",
        "entry_id = 'request-variants-20261018-independent'")
replace('mission-refresh-final', 'mission-refresh-independent', count=2)
replace("with ExitStack() as master_locks, (WORK / 'worker.lock').open('a') as worker_lock:",
        "with (WORK / 'worker.lock').open('a') as worker_lock:")
replace("""        owner_wait_deadline = time.monotonic() + remaining - 305
        print(json.dumps(dict(waiting_for_owners=True, deadline_utc=grant_deadline.isoformat())), flush=True)
        save(WORK / 'progress.json', dict(status='WAITING_FOR_MASTER_OWNER',""",
        """        print(json.dumps(dict(independent_diagnostic=True, deadline_utc=grant_deadline.isoformat())), flush=True)
        save(WORK / 'progress.json', dict(status='RUNNING_INDEPENDENT_DIAGNOSTIC',""")
replace("""                    directory = ROOT / authorization['service_directory']
                    with service_lock(directory / 'service-worker.lock', deadline, qid + '/' + form):
                        result = dispatch(provider, allowance, authorization, row, deadline)""",
        '                    result = dispatch(provider, allowance, authorization, row, deadline)')
start = source.index('@contextmanager\ndef service_lock(')
end = source.index('def reserve(', start)
source = source[:start] + source[end:]
start = source.index('            wait_for_master_owners(authorization,')
end = source.index('            deadline = min(', start)
source = (source[:start] + '            # No master, supervisor or retry-worker lock ownership.\n'
          + source[end:])
# Preparation cannot be rerun: the exact six inputs and old authorities already exist.
start = source.index('def prepare():')
end = source.index('def reserve(', start)
source = source[:start] + source[end:]
source = source.replace("sys.argv[1] in ('prepare', 'run', 'status'), 'Use prepare, run or status'",
                        "sys.argv[1] in ('run', 'status'), 'Use run or status'")
replace("    if sys.argv[1] == 'prepare':\n        prepare()\n    elif sys.argv[1] == 'run':",
        "    if sys.argv[1] == 'run':")
compile(source, str(WORK / 'probe-independent.py'), 'exec')
with (WORK / 'probe-independent.py').open('x') as output:
    output.write(source)
print('Created independent runner; retained source untouched')
