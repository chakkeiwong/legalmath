"""Closed reviewed configuration profiles sharing the original grant and clock."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import sys

from legalmath.errors import LegalMathError
from legalmath.canonical import canonical, digest
from scripts import legal_mission_live_pilot as pilot

OUT = pilot.OUT / 'source-spans'
PLAN = pilot.ROOT / 'docs/plans/legal-mission-live-pilot-source-spans.md'
ENABLING_END = '2026-10-10T06:35:00+00:00'
REVISION = 'source-spans'
PARENT = pilot.OUT
CALLS_BEFORE = 4
CORE_CALLS = 32
PIECE_CHARACTERS = 0
PIECE_UNITS = 16
REVIEW = pilot.ROOT / 'docs/implementation/legal-mission-control/live-pilot-source-spans-review.md'


def select(name):
    """CLI permits these two reviewed profiles only; no arbitrary overrides."""
    global OUT, PLAN, ENABLING_END, REVISION, PARENT, CALLS_BEFORE, CORE_CALLS
    global PIECE_CHARACTERS, PIECE_UNITS, REVIEW
    pilot.require(name in ('source-spans', 'decomposed'), 'Unreviewed revision', 'E_AUTHORITY')
    REVISION = name
    OUT = pilot.OUT / name
    PLAN = pilot.ROOT / ('docs/plans/legal-mission-live-pilot-' + name + '.md')
    REVIEW = pilot.ROOT / ('docs/implementation/legal-mission-control/live-pilot-' + name + '-review.md')
    PARENT = pilot.OUT / 'source-spans' if name == 'decomposed' else pilot.OUT
    CALLS_BEFORE, CORE_CALLS = (5, 31) if name == 'decomposed' else (4, 32)
    PIECE_CHARACTERS, PIECE_UNITS = (20000, 32) if name == 'decomposed' else (0, 16)
    ENABLING_END = '2026-10-10T06:00:00+00:00' if name == 'decomposed' else '2026-10-10T06:35:00+00:00'


class SpanAllowance(pilot.PilotAllowance):
    def stage_limit(self, stage):
        # Original baseline calls stay spent; candidate receives equal new effort.
        return CORE_CALLS if self.arm == 'candidate' and stage == 'core' else super().stage_limit(stage)


def runner_for(arm, provider, directory=OUT):
    from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation
    from legalmath.interpretation.assurance.source_references import PROTOCOL
    from scripts.legal_integration_tools import ProductToolBackend
    spec = pilot.read(pilot.SPEC)
    settings = pilot.PilotSettings.model_validate({**spec['arms'][arm]['settings'],
        'deadline_seconds': 10800, 'total_model_calls': CORE_CALLS,
        'inventory_piece_characters': PIECE_CHARACTERS, 'inventory_piece_units': PIECE_UNITS})
    return CompleteInvestigation(pilot.ROOT, directory / arm / 'product', provider,
        pilot.ROOT / '.localresources/java-toolchain/jdk-17.0.20.1+1', '2026-10-10T00:00:00Z',
        settings=settings, maximum_scoped_actions=82, scoped_rounds=1, scoped_batch_size=12,
        reference_protocol=PROTOCOL, input_profile='readable-tables.v1',
        optional_tool_backend=ProductToolBackend(sorted(ProductToolBackend.TOOL_IDS)) if arm == 'candidate' else None)


def qualify():
    """Actual failing request sizes and unchanged integrity controls; no model."""
    from legalmath.interpretation.assurance import source_references as spans, readable_tables
    from legalmath.interpretation.assurance.semantics import validate_inventory
    rows = []
    for directory in sorted((pilot.OUT / 'provider-evidence').glob('000[1-4]-*')):
        request = pilot.read(directory / 'request.json')
        schema = pilot.read(directory / 'schema.json')
        wire, wire_schema, references = spans.prepare(request, schema)
        encoded = readable_tables.encode(wire)
        decoded = readable_tables.decode(encoded, expected_request_hash=digest(wire))
        pilot.require(canonical(decoded) == canonical(wire), 'Reference request round trip changed')
        pilot.require(len(canonical(encoded)) <= 200000, 'Actual inventory exceeds input cap')
        response = pilot.read(directory / 'result.json')
        try:
            validate_inventory(response, request['source_packet'])
            validation = {'status': 'VALIDATED_CONTRACT_ONLY'}
        except LegalMathError as exc:
            validation = {'status': 'REJECTED', 'error': exc.code, 'details': exc.details}
        rows.append({'call': directory.name, 'request': pilot.ref(directory / 'request.json'),
            'response': pilot.ref(directory / 'result.json'),
            'literal_bytes': len(canonical(request)), 'span_literal_bytes': len(canonical(wire)),
            'span_readable_bytes': len(canonical(encoded)), 'schema_bytes': len(canonical(wire_schema)),
            'round_trip_exact': True, 'spans': len(references['spans']), 'original_validation': validation})
    pilot.require(len(rows) == 4 and [r['original_validation']['status'] for r in rows]
                  == ['REJECTED', 'VALIDATED_CONTRACT_ONLY', 'REJECTED', 'REJECTED'],
                  'First pilot failure pattern not reproduced')
    packet = request['source_packet']
    unit = next(u for u in packet['units'] if u['unit_id'] == 'd996fc27b2d2e.u20.3965')
    source_span = next(s for s in references['spans'] if s['unit_id'] == unit['unit_id']
        and s['start_codepoint'] == 0 and s['end_codepoint'] == len(unit['text']))
    selected = spans.resolve({'span_ids': [source_span['span_id']]}, references, packet, references['request_hash'])
    pilot.require(selected == {'unit_id': unit['unit_id'], 'quote': unit['text']}
                  and 'public-permissionless\u00a0blockchain' in selected['quote'],
                  'Exact original NBSP source was not preserved')
    try:
        spans.resolve({'span_ids': ['span.foreign']}, references, packet, references['request_hash'])
    except LegalMathError as exc:
        pilot.require(exc.code == 'E_REFERENCE', 'Wrong foreign-span rejection')
    else:
        raise AssertionError('Foreign source reference accepted')
    result = {'status': 'LOCAL_REFERENCE_CHECKS_PASS', 'rows': rows,
        'nbsp_preserved': True, 'foreign_span_rejected': True,
        'omission_and_wrong_link_still_rejected': True, 'new_calls': 0,
        'complete_workflow_capacity': 'NOT_ESTABLISHED', 'legal_support': 'NOT_ESTABLISHED'}
    if PIECE_CHARACTERS:
        from legalmath.interpretation.assurance import decomposition, source_context
        from legalmath.interpretation.assurance.semantics import Inventory
        _, qualified, spec = pilot.roots_and_inputs()
        full = pilot.read(pilot.checked(spec['source_packet']))
        pieces = decomposition.partition(full, PIECE_CHARACTERS, PIECE_UNITS)
        pilot.require([u for part in pieces for u in part['units']] == full['units'],
                      'Decomposition changed source order or content')
        result['pieces'] = []
        for role in ('atomic-reader', 'qualification-reader'):
            for index, piece in enumerate(pieces):
                request = decomposition.piece_request(piece, role, index, len(pieces), digest(full))
                request = source_context.augment(request, qualified)
                compact = decomposition.compact_request(request, profile='v2')
                source_context.before_cache(compact, qualified)
                wire, _, _ = spans.prepare(compact, Inventory.model_json_schema())
                encoded = readable_tables.encode(wire)
                pilot.require(readable_tables.decode(encoded, expected_request_hash=digest(wire)) == wire,
                              'Piece encoding lost context')
                pilot.require(len(canonical(encoded)) <= 200000, 'Piece request exceeds original cap')
                result['pieces'].append({'role': role, 'index': index,
                    'unit_ids': [u['unit_id'] for u in piece['units']],
                    'characters': sum(len(u['text']) for u in piece['units']),
                    'wire_bytes': len(canonical(encoded)), 'source_qualification_preserved': True,
                    'round_trip_exact': True})
        result['minimum_inventory_calls'] = 2 * (len(pieces) + 1)
        result['cross_piece_review_required'] = True
        result['all_55_units_preserved_in_order'] = len(full['units']) == 55
    return result


def prepare():
    from scripts.legal_mission_control import admit, BASE
    from legalmath.interpretation.assurance.investigation_observations import method
    from legalmath.interpretation.assurance.integrated import implementation_identity
    pilot.require(datetime.now(timezone.utc) < datetime.fromisoformat(ENABLING_END),
                  'Reviewed enabling window expired', 'E_RESOURCE_LIMIT')
    pilot.require(not (OUT / 'protocol.json').exists() and not (OUT / 'execution-started.json').exists(),
                  'Source-span revision already frozen or executed', 'E_JOB_STATE')
    admission = admit(pilot.read(pilot.ROOT / BASE / 'mission.json'), pilot.read(pilot.ROOT / BASE / 'tools.json'))
    pilot.require(admission['task']['id'] == 'product-contribution', 'Wrong admitted task')
    allowance = SpanAllowance('baseline')
    pilot.require(allowance.verify()['used'] == CALLS_BEFORE and allowance.remaining_seconds() > 5,
                  'Revision requires its exact terminal predecessor spending')
    prefix = pilot.read(allowance.path)
    pilot.require(all(r['arm'] == 'baseline' and r['stage'] == 'core' for r in prefix['calls']),
                  'Unexpected predecessor allocation')
    parent_result = pilot.read(PARENT / 'result.json')
    pilot.require(parent_result['status'] == 'PAIR_UNAVAILABLE' and parent_result['used_calls'] == CALLS_BEFORE
                  and set(parent_result['arms']) == {'baseline'}, 'Different terminal parent result')
    parent = pilot.read(PARENT / 'protocol.json')
    for item in parent['files']:
        pilot.checked(item)
    for row in parent['source_snapshot']:
        pilot.checked(row['retained'])
    pilot.require(implementation_identity() == parent['implementation'],
                  'This configuration revision cannot change product source')
    roots, qualified, spec = pilot.roots_and_inputs()
    OUT.mkdir(parents=True, exist_ok=True)
    pilot.immutable(OUT / 'calls-before.json', prefix)
    pilot.save(OUT / 'qualification.json', qualify())
    pilot.save(OUT / 'mission-before.json', pilot.read(pilot.ROOT / BASE / 'mission.json'))
    pilot.save(OUT / 'qualified-source-context.json', qualified)
    arms = {arm: method(runner_for(arm, pilot.PilotProvider(allowance=SpanAllowance(arm),
                     protocol_directory=OUT))) for arm in pilot.ARMS}
    baseline, candidate = deepcopy(arms['baseline']), deepcopy(arms['candidate'])
    baseline.pop('optional_tools'); candidate.pop('optional_tools')
    pilot.require(baseline == candidate, 'Source-span methods are unmatched')
    paths = [pilot.ROOT / row['current']['path'] for row in parent['source_snapshot']]
    paths += [PLAN, Path(__file__), REVIEW,
        pilot.ROOT / 'tests/tooling/test_legal_mission_control.py']
    snapshots = []
    for path in sorted(set(paths)):
        target = OUT / 'source' / path.relative_to(pilot.ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        snapshots.append({'current': pilot.ref(path), 'retained': pilot.ref(target)})
    evidence = [PARENT / 'result.json', PARENT / 'protocol.json',
                OUT / 'calls-before.json', OUT / 'qualification.json']
    evidence += sorted(p for d in (pilot.OUT / 'provider-evidence').iterdir()
                       if d.is_dir() and int(d.name.split('-')[0]) <= CALLS_BEFORE
                       for p in d.iterdir() if p.is_file())
    freeze = {'profile': 'legalmath.mission-pilot-source-spans.v1', 'arms': arms,
        'arm_order': list(pilot.ARMS), 'implementation': implementation_identity(),
        'route': pilot.CodexProvider().routing, 'source_inputs': spec['source_inputs'],
        'questions': spec['questions'], 'source_snapshot': snapshots,
        'files': parent['files'] + [pilot.ref(p) for p in evidence],
        'grant_prefix': pilot.ref(OUT / 'calls-before.json'),
        'shared_ledger': str(allowance.path.relative_to(pilot.ROOT)),
        'parent_protocol': pilot.ref(PARENT / 'protocol.json'), 'prior_calls': CALLS_BEFORE,
        'random_seeds': parent['random_seeds'], 'legal_question_reduced': False,
        'new_core_calls_per_arm': CORE_CALLS, 'revision': REVISION, 'prior_attempts_erased': False}
    pilot.save(OUT / 'protocol.json', freeze)
    pilot.save(OUT / 'run-manifest.json', {
        'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=pilot.ROOT, text=True).strip(),
        'command': '.venv/bin/python scripts/legal_mission_live_pilot.py execute --revision ' + REVISION,
        'environment': {'python': sys.version, 'executable': sys.executable, 'CUDA_VISIBLE_DEVICES': '-1'},
        'cpu_gpu': 'CPU only; GPU devices intentionally hidden.', 'plan': pilot.ref(PLAN),
        'protocol': pilot.ref(OUT / 'protocol.json'), 'authorization': pilot.ref(pilot.OUT / 'authorization.json'),
        'data_version': spec['source_inputs'], 'random_seeds': freeze['random_seeds'],
        'started_utc': pilot.START, 'deadline_utc': pilot.END, 'calls_before': CALLS_BEFORE,
        'wall_seconds': 'See terminal result', 'result_file': str((OUT / 'result.json').relative_to(pilot.ROOT))})
    pilot.check_frozen(OUT)
    new_pair_maximum = 2 * (sum(pilot.STAGES.values()) - 36 + CORE_CALLS)
    result = {'status': 'PREPARED', 'revision': REVISION, 'new_calls': 0, 'used_calls': CALLS_BEFORE,
        'maximum_pair_additional_calls': new_pair_maximum,
        'maximum_all_attempt_calls': CALLS_BEFORE + new_pair_maximum,
        'deadline_utc': pilot.END, 'methods_match_except_tools': True}
    pilot.save(OUT / 'preparation-result.json', result)
    return result


def check():
    from scripts.legal_mission_control import admit, BASE
    admission = admit(pilot.read(pilot.ROOT / BASE / 'mission.json'), pilot.read(pilot.ROOT / BASE / 'tools.json'))
    pilot.require(admission['task']['id'] == 'product-contribution', 'Wrong admitted task')
    pilot.require(admission['task'].get('live_method_revision') == {
        'id': REVISION, 'protocol': pilot.ref(OUT / 'protocol.json'), 'plan': pilot.ref(PLAN)},
        'Source-span continuation is not registered', 'E_AUTHORITY')
    pilot.check_frozen(OUT)
    pilot.roots_and_inputs()
    return {'check': 'PASS', 'revision': REVISION,
            'allowance': SpanAllowance('baseline').verify(), 'new_calls': 0}


def execute():
    return pilot.execute(OUT, checker=check, runner_factory=runner_for, allowance_factory=SpanAllowance)


def status():
    result = pilot.read(OUT / 'result.json') if (OUT / 'result.json').exists() else None
    return {'revision': REVISION, 'grant': SpanAllowance('baseline').verify(), 'result': result,
            'started': (OUT / 'execution-started.json').exists()}
