"""Recheck retained, actually augmented inputs after exact transport corrections.

Uses the unchanged installed-tool results from verification 2. It does not
execute tools, answer prompts, increase their action limit, or qualify a live run.
"""
from datetime import datetime, timezone
from pathlib import Path
import time

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.assurance.transport import CompactProvider
from legalmath.interpretation.assurance import source_references, evidence_tables
from legalmath.interpretation.assurance.route_admission import admission, workload
from scripts.legal_mission_route_target import LocalBoundary, Captured, LIMITS, ROOT, RUN, REPAIR, read, ref, require

PRIOR = REPAIR/'verification-2/retained-target'


def retained_summary():
    """Recover reporting only after canonical JSON rejected a float wall time."""
    path = PRIOR/'recovered-summary.json'
    if path.exists():return read(path)
    arms = {}
    for arm in ('baseline','candidate'):
        rows = read(PRIOR/arm/'requests.json')
        require(len(rows) == 189, 'Original diagnostic did not finish all declared inputs')
        arms[arm] = {'requests':ref(PRIOR/arm/'requests.json'),
            'delivered':sum(r['status'] != 'REFUSED' for r in rows),
            'refused':sum(r['status'] == 'REFUSED' for r in rows),
            'tool_report':ref(PRIOR/arm/'tool-report.json')}
    required = workload(pieces=5,reader_claims=[39,39],selected_claims=67,all_claims=78,
        candidates=12,formalized_candidates=6,tool_enabled=True)
    eligibility = admission(required,{'core':23,'question_assignment':3,'scoped':82,
        'dossier_reviews':64,'interaction':1,'synthesis':1},deadline_utc='2026-10-12T04:28:01+00:00')
    require(not eligibility['admitted'], 'Unexpected allocation result')
    result = {'status':'DIAGNOSTIC_ROWS_COMPLETE_FINAL_REPORT_SERIALIZATION_FAILED',
        'report_failure':'Canonical JSON disallows float wall_seconds. Recovered from all retained rows; no rerun.',
        'arms':arms,'original_allocation_check':eligibility,'source_units':55,
        'actual_partial_claims':78,'historical_readings':12,'new_live_calls':0,
        'source_snapshot':ref(REPAIR/'verification-2/source-snapshot.json'),
        'input_classification':ref(PRIOR/'input-classification.json')}
    save(path,result)
    return result


def qualify(directory):
    start = time.monotonic()
    directory = Path(directory)
    directory.mkdir(parents=True,exist_ok=False)
    previous = retained_summary()
    context = read(RUN/'qualified-source-context.json')
    deadline = datetime.fromisoformat(read(REPAIR/'admission.json')['expires_utc'])
    arms = {}
    for arm in ('baseline','candidate'):
        out = directory/arm
        local = LocalBoundary(out/'transport',context)
        provider = CompactProvider(local,local.directory,reference_protocol=source_references.PROTOCOL,
            input_profile=evidence_tables.PROFILE)
        records = []
        for old in sorted((PRIOR/arm/'transport').glob('call-*')):
            require(datetime.now(timezone.utc) < deadline, 'Original attempt deadline exhausted')
            transport = old/'source-references'
            if not (transport/'encoding-validation.json').exists():
                records.append({'status':'NOT_REPLAYED','reason':'No validated original prepared input', 'path':str(old.relative_to(ROOT))})
                continue
            request,schema = read(old/'original-request.json'),read(old/'schema.json')
            prior = read(transport/'encoding-validation.json')
            require(digest(read(transport/'expanded-wire-request.json')) == prior['expanded_request_hash'], 'Prepared input changed')
            local.last = None
            row = {'task':request['task'],'original_request':ref(old/'original-request.json'),
                'original_schema':ref(old/'schema.json'),'prior_wire_bytes':prior['encoded_bytes'],
                'prior_prepared_hash':prior['expanded_request_hash']}
            try:
                provider.complete(request,schema,LIMITS)
                raise RuntimeError('Capture must not provide a response')
            except Captured:
                require(local.last['prepared_hash'] == prior['expanded_request_hash'], 'Re-encoding changed original source or tool feedback')
                row.update(status='EXACT_INPUT_DELIVERED_NO_RESPONSE',**local.last)
            except LegalMathError as exc:
                row.update(status='REFUSED',error=exc.code,details=exc.details)
            records.append(row)
            save(out/'requests.json',records)
        delivered = [r for r in records if r['status'] == 'EXACT_INPUT_DELIVERED_NO_RESPONSE']
        old_records = read(PRIOR/arm/'requests.json')
        unprepared = len(old_records)-len(records)
        require(unprepared >= 0, 'Unexpected prior transport population')
        arms[arm] = {'retained_prepared_requests':len(records),'delivered_exactly':len(delivered),
            'unprepared_requests_not_qualified':unprepared,
            'refusals':[r for r in records if r['status'] != 'EXACT_INPUT_DELIVERED_NO_RESPONSE'],
            'maximum_prior_wire_bytes':max((r['prior_wire_bytes'] for r in records if 'prior_wire_bytes' in r),default=0),
            'maximum_current_wire_bytes':max((r['encoded_bytes'] for r in delivered),default=0),
            'records':ref(out/'requests.json')}
    result = {'status':'PREPARED_INPUT_RECHECK_COMPLETE_LIVE_REFUSED','arms':arms,
        'original_target_diagnostic':ref(PRIOR/'recovered-summary.json'),
        'original_allocation_check':previous['original_allocation_check'],
        'source_units':previous['source_units'],'actual_partial_claims':previous['actual_partial_claims'],
        'historical_readings':previous['historical_readings'],'inventory_still_incomplete':True,
        'full_target_capacity_qualified':False,'actual_response_qualification':False,
        'legal_quality_evaluated':False,'tool_benefit_evaluated':False,'new_live_calls':0,
        'installed_tools_reexecuted':False,
        'scope':'Exact unchanged source and tool feedback through current transport. Prior tool-action refusals remain; no complete legal dossier or response-quality finding.',
        'method':ref(Path(__file__)), 'plan':ref(ROOT/'docs/plans/legal-mission-route-repair.md'),
        'command':'.venv/bin/python scripts/legal_mission_route_repair.py run',
        'finished_utc':datetime.now(timezone.utc).isoformat(),'wall_milliseconds':round(1000*(time.monotonic()-start))}
    save(directory/'result.json',result)
    return result
