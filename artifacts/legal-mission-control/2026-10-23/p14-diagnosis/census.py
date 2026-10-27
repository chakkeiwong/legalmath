"""Read retained P14 failures; never dispatch, alter results or decide acceptance."""
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import time

from jsonschema import Draft202012Validator

ROOT = Path('/home/chakwong/python/legalmath')
OUT = Path(__file__).resolve().parent
ARM = ROOT/'artifacts/legal-mission-control/2026-10-21/review-repair/recovered-live/arms/p14/baseline'
CALLS = ARM/'calls'

def read(path):
    return json.loads(path.read_text())

def reference(path):
    return {'path': str(path.relative_to(ROOT)), 'sha256': sha256(path.read_bytes()).hexdigest()}

def counts(rows):
    return dict(Counter(rows))

def schema_errors(value, schema):
    def concise(error):
        return {'path': list(error.absolute_path), 'validator': error.validator,
                'expected': error.validator_value if error.validator != 'additionalProperties' else False,
                'actual_type': type(error.instance).__name__,
                'actual_length': len(error.instance) if isinstance(error.instance, (dict,list,str)) else None}
    errors = []
    for err in Draft202012Validator(schema).iter_errors(value):
        if not err.context:
            errors.append(concise(err))
            continue
        # Keep all leaf paths/rules, not multi-kilobyte schema/prose renderings.
        pending = list(err.context)
        while pending:
            child = pending.pop()
            if child.context:
                pending.extend(child.context)
            else:
                item = concise(child)
                if item not in errors:
                    errors.append(item)
    return errors

start = time.monotonic()
journal = read(CALLS/'dispatch.json')
rows, wire_shapes = [], []
for key, entry in journal['calls'].items():
    family = next((p for p in ('audit-group-', 'repair-review-', 'audit-context-') if key.startswith(p)), None)
    if family is None:
        continue
    folder = CALLS/key
    result = read(folder/'result.json')
    item = {'key': key, 'family': family, 'status': entry['status'],
            'result': reference(folder/'result.json'), 'error': result.get('error'),
            'reason': result.get('reason', '').split('\n')[0][:240]}
    if family != 'audit-context-':
        binding = read(folder/'reference-binding.json')
        required = binding['request']['required_considered']
        schema_keys = list(binding['schema']['properties']['assignments']['properties'])
        assignment_ids = [r['id'] for r in binding['request']['payload']['assignments']]
        contract = {'key':key, 'family':family, 'binding':reference(folder/'reference-binding.json'),
                    'same_request_and_response_ids': set(required)==set(schema_keys),
                    'required_count':len(required), 'context_assignment_count':len(assignment_ids),
                    'required_aliases':required, 'schema_keys':schema_keys,
                    'original_ids':binding['original_request']['required_considered']}
        wire_shapes.append(contract)
        if result.get('error') == 'ValidationError':
            wire = read(folder/'wire-response.json')['value']
            item['wire_schema_errors'] = schema_errors(wire, binding['schema'])
            item['wire_response'] = reference(folder/'wire-response.json')
            item['wire_shape'] = {
                'analyses_count':len(wire.get('analyses', [])),
                'assignments_type':type(wire.get('assignments')).__name__,
                'decisions':[{'verdict':r['decision'].get('review', {}).get('verdict'),
                    'support':len(r['decision'].get('review', {}).get('support', [])),
                    'issues':len(r['decision'].get('review', {}).get('issues', [])),
                    'source_gaps':len(r['decision'].get('source_gaps', [])),
                    'context_needs':len(r['decision'].get('context_needs', []))}
                    for r in wire.get('analyses', []) if isinstance(r, dict) and isinstance(r.get('decision'),dict)],
                'malformed_analysis_keys':[list(r) if isinstance(r,dict) else type(r).__name__
                    for r in wire.get('analyses', []) if not isinstance(r,dict) or 'decision' not in r]}
        if entry['status']=='FAILED' and (folder/'raw.json').exists():
            raw = read(folder/'raw.json')['value']
            assigned = raw.get('assignments', {})
            analyses = raw.get('analyses', [])
            if isinstance(assigned,dict):
                used = {r['analysis_id'] for r in assigned.values()}
                actual = {r['analysis_id'] for r in analyses}
                item['rationale_membership'] = {'missing':sorted(used-actual), 'unassigned':sorted(actual-used)}
            item['assertion_paths'] = [b['path'] for r in analyses
                for b in r['decision'].get('assertion_bindings', [])]
    rows.append(item)

assembled = read(ARM/'contextual-group-review-p14.json')
reviews = assembled['reviews']
failed_groups = {r['key'] for r in rows if r['family']=='audit-group-' and r['status']=='FAILED'}
failed_ids = set()
for key in failed_groups:
    failed_ids.update(read(CALLS/key/'request.json')['required_considered'])
repair_valid_ids = {identity for r in reviews if r['status']=='VALIDATED' and r.get('repair_evidence')
                    for identity in r['value']['considered']}
salvaged_ids = {identity for r in reviews if r['status']=='VALIDATED'
    and r.get('group_evidence',{}).get('key') in failed_groups
    for identity in r['value']['considered']}
summary = {'at_utc':datetime.now(timezone.utc).isoformat(),
    'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'family_counts':{p:counts(r['status'] for r in rows if r['family']==p)
        for p in ('audit-group-','repair-review-','audit-context-')},
    'failure_categories':{p:counts((r['error']+': '+(r['reason'] if r['error']!='ValidationError' else 'invalid response schema'))
        for r in rows if r['family']==p and r['status']=='FAILED')
        for p in ('audit-group-','repair-review-','audit-context-')},
    'contract_mismatches':sum(not x['same_request_and_response_ids'] for x in wire_shapes),
    'contracts_checked':len(wire_shapes),
    'assembled':{'assignments':len(assembled['assigned_ids']),
        'statuses':counts(r['status'] for r in reviews),
        'verdicts':counts(r['value']['verdict'] for r in reviews if r['status']=='VALIDATED'),
        'failed_group_assignments':len(failed_ids), 'salvaged_without_repair':len(salvaged_ids),
        'validated_repairs_of_failed_groups':len(repair_valid_ids & failed_ids)},
    'inputs':[reference(CALLS/'dispatch.json'),reference(ARM/'contextual-group-review-p14.json')],
    'provider_calls':0, 'legal_acceptance':False, 'seconds':time.monotonic()-start}
(OUT/'census.json').write_text(json.dumps({'summary':summary, 'calls':rows, 'wire_contracts':wire_shapes},indent=2)+'\n')
print(json.dumps(summary,indent=2))
