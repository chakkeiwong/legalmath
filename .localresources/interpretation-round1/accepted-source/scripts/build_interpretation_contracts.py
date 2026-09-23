"""Build proposed interpretation.v1 document contracts; does not change runtime v0.1."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/monograph/contracts'
OUT.mkdir(parents=True, exist_ok=True)


def obj(properties, required=None):
    return {'type': 'object', 'properties': properties,
            'required': list(properties) if required is None else required,
            'additionalProperties': False}


def arr(item, minimum=0):
    return {'type': 'array', 'items': item, 'minItems': minimum, 'uniqueItems': True}


def enum(*values):
    return {'enum': list(values)}


ID = {'type': 'string', 'pattern': '^[a-z][a-z0-9_.:-]{0,127}$'}
HASH = {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}
TEXT = {'type': 'string', 'minLength': 1, 'maxLength': 20000}
TIME = {'type': 'string', 'format': 'date-time', 'pattern': '^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d{6}Z$'}
COUNT = {'type': 'integer', 'minimum': 0}
POS = {'type': 'integer', 'minimum': 1}
NULL = {'type': 'null'}
VER = {'const': 'interpretation.v1'}

def nullable(s): return {'anyOf': [s, NULL]}
def ids(): return arr(ID)
def base(fields): return obj({'schema_version': VER, **fields})

schemas = {}
schemas['policy'] = base({
    'policy_id': ID,
    'use': enum('DETERMINISTIC_FIXTURE_ONLY', 'PAID_RUN'),
    'max_initial_actions': POS, 'max_resolution_rounds': POS,
    'max_actions_per_issue_root': POS, 'max_actions_total': POS,
    'max_no_progress_rounds': POS, 'action_timeout_seconds': POS,
    'run_deadline_seconds': POS, 'max_candidates': POS,
    'max_argument_nodes': POS, 'max_dependency_depth': POS,
    'token_cap': nullable(POS), 'cost_cap_minor_units': nullable(POS),
    'billing_currency': nullable({'type': 'string', 'pattern': '^[A-Z]{3}$'}),
    'required_initial_roles': arr(ID, 1), 'mandatory_checks': arr(ID, 1),
    'unknown_materiality_blocks': {'const': True},
    'provider_retries': {'const': 'DISABLED_OR_SEPARATELY_RESERVED'},
    'production_default': {'const': False},
})
schemas['policy']['allOf'] = [{
    'if': {'properties': {'use': {'const': 'PAID_RUN'}}},
    'then': {'properties': {'token_cap': POS, 'cost_cap_minor_units': POS,
                            'billing_currency': {'type': 'string', 'pattern': '^[A-Z]{3}$'}}}
}]

schemas['run'] = base({
    'run_id': ID, 'predecessor_run_id': nullable(ID), 'source_packet_hash': HASH,
    'profile_id': ID, 'policy_id': ID, 'policy_hash': HASH,
    'created_at': TIME, 'deadline': TIME,
    'status': enum('INITIALIZING', 'INITIAL_PROPOSALS', 'RESOLVING',
                   'READY_FOR_REVIEW', 'BLOCKED_UNRESOLVED', 'CANCELLED', 'FAILED_INTEGRITY'),
    'rounds_issued': COUNT, 'actions_issued': COUNT, 'no_progress_rounds': COUNT,
    'candidate_ids': ids(), 'issue_ids': ids(), 'action_ids': ids(),
    'completed_initial_roles': ids(), 'passed_mandatory_checks': ids(),
    'coverage_id': ID, 'report_id': nullable(ID), 'revision': COUNT,
})

assumption = obj({'assumption_id': ID, 'statement': TEXT, 'provenance_refs': ids(),
                  'status': enum('SOURCE_SUPPORTED', 'FACT_REQUIRED', 'PROVISIONAL', 'DISPUTED', 'REJECTED')})
argument = obj({'argument_id': ID, 'conclusion': TEXT, 'premise_refs': ids(),
                'inference': TEXT, 'inference_kind': enum('STRICT', 'DEFEASIBLE', 'NOT_FORMALIZED'),
                'source_refs': ids(), 'opposes_argument_ids': ids()})
schemas['candidate'] = base({
    'candidate_id': ID, 'run_id': ID, 'parent_id': nullable(ID),
    'source_packet_hash': HASH, 'source_unit_ids': arr(ID, 1),
    'family_ids': arr(ID, 1), 'subject_unit': TEXT, 'controlled_language': TEXT,
    'bundle_hash': nullable(HASH), 'assumptions': arr(assumption),
    'arguments': arr(argument), 'issue_ids': ids(),
    'status': enum('ACTIVE', 'DEFERRED', 'DEFEATED', 'UNSUPPORTED', 'SELECTED_FOR_REVIEW'),
    'disposition_reason': TEXT, 'scheduling_priority': COUNT,
    'score_purpose': {'const': 'INVESTIGATION_PRIORITY_ONLY'},
    'probability_of_legal_correctness': NULL,
    'generation_phase': enum('BLIND_INITIAL', 'SHARED_RESOLUTION', 'HUMAN_AUTHORED'),
    'action_id': nullable(ID), 'revision_reason': TEXT,
})

schemas['issue'] = base({
    'issue_id': ID, 'root_id': ID, 'parent_issue_id': nullable(ID), 'run_id': ID,
    'source_unit_ids': ids(), 'candidate_ids': ids(),
    'kind': enum('SOURCE_COVERAGE', 'DEPENDENCY', 'SCOPE', 'DEFINITION', 'EXCEPTION',
                 'MODALITY', 'TIME', 'FACT_MAPPING', 'FORMAL_MISMATCH', 'JAVA_MISMATCH',
                 'MEMBER_FAILURE', 'SEARCH_INCOMPLETE', 'INTEGRITY'),
    'question': TEXT, 'observed_difference': TEXT,
    'materiality': enum('MATERIAL', 'UNKNOWN', 'IMMATERIAL_REVIEWED'),
    'processing_state': enum('OPEN', 'INVESTIGATING', 'AWAITING_EVIDENCE', 'HUMAN_REQUIRED', 'TERMINAL'),
    'resolution_state': enum('UNRESOLVED', 'RESOLVED_EVIDENCE', 'RESOLVED_ADJUDICATION', 'RESOLVED_EQUIVALENCE'),
    'terminal_reason': nullable(enum('RESOLVED', 'BUDGET_EXHAUSTED', 'ROUND_LIMIT', 'DEADLINE_REACHED',
                                     'NO_PROGRESS', 'DEPENDENCY_UNAVAILABLE', 'CANCELLED', 'INTEGRITY_FAILURE')),
    'resolution_evidence_refs': ids(), 'attempted_action_ids': ids(),
    'evidence_needed': TEXT, 'affected_decisions': arr(TEXT), 'revision': COUNT,
})
schemas['issue']['allOf'] = [
    {'if': {'properties': {'resolution_state': {'not': {'const': 'UNRESOLVED'}}}},
     'then': {'properties': {'resolution_evidence_refs': arr(ID, 1)}}},
    {'if': {'properties': {'processing_state': {'const': 'TERMINAL'}}},
     'then': {'properties': {'terminal_reason': {'type': 'string'}}}},
]

schemas['action'] = base({
    'action_id': ID, 'run_id': ID, 'issue_root_id': nullable(ID),
    'initial_role': nullable(ID), 'round': COUNT,
    'kind': enum('INITIAL_PROPOSAL', 'RETRIEVE', 'ARGUMENT', 'REPAIR', 'COMPARE', 'REVIEW_QUESTION'),
    'question': TEXT, 'success_criterion': TEXT, 'input_hashes': arr(HASH, 1),
    'adapter_id': ID, 'idempotency_key': ID,
    'state': enum('RESERVED', 'DISPATCHED', 'SUCCEEDED', 'FAILED', 'TIMED_OUT', 'RESULT_UNKNOWN'),
    'issued_at': TIME, 'timeout_seconds': POS, 'fencing_token': COUNT,
    'lease_owner': nullable(ID), 'result_ref': nullable(ID),
    'substantive_outcome': enum('PENDING', 'PROGRESS', 'NO_PROGRESS', 'INVALID', 'UNAVAILABLE'),
    'issued_charge': {'const': 1}, 'token_reservation': nullable(COUNT),
    'cost_reservation_minor_units': nullable(COUNT),
    'remote_idempotency': enum('SUPPORTED', 'UNSUPPORTED', 'NOT_APPLICABLE'),
})
schemas['action']['allOf'] = [{
    'if': {'properties': {'kind': {'const': 'INITIAL_PROPOSAL'}}},
    'then': {'properties': {'initial_role': ID, 'issue_root_id': NULL, 'round': {'const': 0}}},
    'else': {'properties': {'initial_role': NULL, 'issue_root_id': ID, 'round': POS}}
}]

unit = obj({'unit_id': ID, 'locator': TEXT,
            'disposition': enum('IMPLEMENTED', 'CONTEXT', 'DEFINITION_DEPENDENCY',
                                'SEPARATE_OBLIGATION', 'OUT_OF_SCOPE_REVIEWED', 'UNRESOLVED'),
            'reason': TEXT, 'target_refs': ids()})
schemas['coverage'] = base({
    'coverage_id': ID, 'run_id': ID, 'source_packet_hash': HASH,
    'inventory_unit_ids': arr(ID, 1), 'dispositions': arr(unit, 1),
    'required_dependency_ids': ids(), 'acquired_dependency_ids': ids(),
    'identified_family_ids': ids(), 'explored_family_ids': ids(),
    'inventory_review_status': enum('UNREVIEWED', 'SYNTHETIC_FIXTURE', 'REVIEWED'),
    'review_decision_id': nullable(ID),
})

schemas['report'] = base({
    'report_id': ID, 'run_id': ID, 'source_packet_hash': HASH, 'profile_id': ID,
    'run_status': enum('READY_FOR_REVIEW', 'BLOCKED_UNRESOLVED', 'CANCELLED', 'FAILED_INTEGRITY'),
    'selected_slice': TEXT, 'candidate_ids': ids(), 'all_issue_ids': ids(),
    'material_unresolved_issue_ids': ids(), 'coverage_id': ID,
    'unexplored_family_ids': ids(), 'missing_dependency_ids': ids(),
    'missing_initial_roles': ids(), 'incomplete_mandatory_checks': ids(),
    'processing_stop': enum('COMPLETE_FOR_REVIEW', 'ROUND_LIMIT', 'ACTION_LIMIT', 'DEADLINE',
                            'NO_PROGRESS', 'HUMAN_REQUIRED', 'CANCELLED', 'INTEGRITY_FAILURE'),
    'rounds_issued': COUNT, 'actions_issued': COUNT,
    'probability_of_legal_correctness': NULL,
    'release_eligible': {'const': False},
    'next_decision': TEXT, 'next_decision_owner_role': ID,
    'evidence_limitations': arr(TEXT, 1), 'created_at': TIME,
})
schemas['report']['allOf'] = [{
    'if': {'properties': {'run_status': {'const': 'READY_FOR_REVIEW'}}},
    'then': {'properties': {k: {'maxItems': 0} for k in
                           ('material_unresolved_issue_ids', 'unexplored_family_ids',
                            'missing_dependency_ids', 'missing_initial_roles', 'incomplete_mandatory_checks')}}
}]

schemas['review-decision'] = base({
    'decision_id': ID, 'run_id': ID, 'reviewer_principal': ID,
    'reviewer_role': enum('LEGAL_INTERPRETATION_REVIEWER', 'DATA_OWNER', 'ENGINEERING_REVIEWER'),
    'authority': enum('LOCAL_SYNTHETIC', 'ENTERPRISE_AUTHENTICATED'),
    'candidate_hash': HASH, 'report_hash': HASH, 'source_packet_hash': HASH,
    'decision': enum('ACCEPT_MEANING', 'REJECT', 'REQUIRE_EVIDENCE', 'RECORD_BANK_POLICY'),
    'proposition': TEXT, 'rationale': TEXT, 'strongest_objection_response': TEXT,
    'conditions': arr(TEXT), 'evidence_refs': arr(ID, 1), 'recorded_at': TIME,
})

schemas['issue-decision'] = base({
    'decision_id': ID, 'run_id': ID, 'issue_id': ID, 'issue_revision': COUNT,
    'candidate_hash': HASH, 'source_packet_hash': HASH,
    'reviewer_principal': ID, 'reviewer_role': {'const': 'LEGAL_INTERPRETATION_REVIEWER'},
    'authority': enum('LOCAL_SYNTHETIC', 'ENTERPRISE_AUTHENTICATED'),
    'decision': enum('RESOLVE_MEANING', 'REJECT_CANDIDATE', 'REQUIRE_EVIDENCE', 'RECORD_BANK_POLICY'),
    'proposition': TEXT, 'rationale': TEXT, 'strongest_objection_response': TEXT,
    'conditions': arr(TEXT), 'evidence_refs': arr(ID, 1), 'recorded_at': TIME,
})

schemas['evidence'] = base({
    'evidence_id': ID, 'run_id': ID, 'source_packet_hash': HASH,
    'kind': enum('SOURCE_SPAN', 'FACT_RECORD', 'VALIDATED_REPAIR', 'FORMAL_COMPARISON', 'HUMAN_ADJUDICATION'),
    'content_hash': HASH, 'statement': TEXT, 'source_unit_ids': ids(),
    'validation_status': enum('UNVERIFIED', 'VALIDATED', 'REJECTED'),
    'authority': enum('SYNTHETIC_FIXTURE', 'RETAINED_SOURCE', 'AUTHENTICATED_REVIEW'),
    'validator_id': nullable(ID), 'action_id': nullable(ID),
    'review_decision_id': nullable(ID), 'domain_hash': nullable(HASH),
    'comparison_result': nullable(enum('EQUIVALENT_WITHIN_DOMAIN', 'DIFFERENT', 'UNKNOWN', 'INCONSISTENT_DOMAIN')),
    'legal_source_commitment_resolved': {'type': 'boolean'},
})
schemas['evidence']['allOf'] = [{
    'if': {'properties': {'kind': {'const': 'FORMAL_COMPARISON'}}},
    'then': {'properties': {'domain_hash': HASH, 'comparison_result': {'type': 'string'}}}
}]

for name, schema in schemas.items():
    schema = {'$schema': 'https://json-schema.org/draft/2020-12/schema',
              '$id': f'https://legalmath.invalid/interpretation/v1/{name}',
              'title': f'Proposed interpretation.v1 {name}', **schema}
    (OUT / f'{name}.schema.json').write_text(json.dumps(schema, indent=2)+'\n')

policy = dict(schema_version='interpretation.v1', policy_id='fixture-policy.v1',
              use='DETERMINISTIC_FIXTURE_ONLY', max_initial_actions=4,
              max_resolution_rounds=3, max_actions_per_issue_root=3, max_actions_total=12,
              max_no_progress_rounds=2, action_timeout_seconds=30, run_deadline_seconds=600,
              max_candidates=24, max_argument_nodes=200, max_dependency_depth=6,
              token_cap=None, cost_cap_minor_units=None, billing_currency=None,
              required_initial_roles=['inventory','normative','controlled-language','alternatives'],
              mandatory_checks=['source-coverage','dependencies','candidate-validity','argument-register',
                                'reference-check','java-check','report-integrity'],
              unknown_materiality_blocks=True, provider_retries='DISABLED_OR_SEPARATELY_RESERVED',
              production_default=False)
(OUT / 'reference-policy.json').write_text(json.dumps(policy,indent=2)+'\n')
print(json.dumps({'schemas_written': len(schemas), 'policy': policy['policy_id'],
                  'application_runtime_modified': False}))
