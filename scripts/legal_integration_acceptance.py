"""Separate scoped evaluation decisions from connection and legal acceptance."""
from pathlib import Path

from scripts.legal_mission_execution import require, verify, read, safe

TOOLS = ('bm25', 'legalruleml', 'pyarg', 'carneades', 'clingo', 'logical-english')
QUESTIONS = ('p10', 'p14', 'evidence', 'gatecoin')
PAIR_DECISIONS = {'applicable', 'target_required', 'not_applicable', 'unresolved'}
EVALUATION_DECISIONS = {'incomplete', 'evaluated', 'rejected', 'limited'}


def current_register(program, name):
    """Prefer an explicit current reviewed register without changing old evidence."""
    require(name in {'inventory', 'applicability'}, 'Unknown acceptance register')
    current = program.get('substantive_continuation_revision', {}).get('post_review', {}).get(name)
    current = current or program.get('remaining_work_revision', {}).get(name)
    return current or program.get('acceptance_revision', {}).get(name)


def evidence(root, refs):
    require(isinstance(refs, list) and bool(refs), 'Decision requires retained evidence')
    for item in refs:
        verify(Path(root), item)


def validate_applicability(document, root):
    require(document.get('profile') == 'legal-tool-applicability.v1', 'Unknown applicability profile')
    rows = document.get('pairs', [])
    ids = [(r.get('question'), r.get('tool')) for r in rows]
    require(len(ids) == len(set(ids)) and set(ids) ==
            {(q, t) for q in QUESTIONS for t in TOOLS}, 'Applicability lost original pairs')
    for row in rows:
        require(row.get('decision') in PAIR_DECISIONS, 'Unknown applicability decision')
        require(all(isinstance(row.get(k), str) and row[k].strip() for k in
                    ('mechanism', 'reason', 'required_target', 'question_impact', 'reopen_when')),
                'Applicability requires substantive scope and reopening condition')
        evidence(root, row.get('evidence'))
        if row['decision'] == 'not_applicable':
            require(row.get('reviewed') is True and row.get('boundary_evidence'),
                    'Unsupported input alone is not a reviewed scope rejection')
            evidence(root, row['boundary_evidence'])
        if row['decision'] == 'applicable':
            require(row.get('target_evidence') and row.get('warrant_review'),
                    'Applicable tool needs an actual target and source warrant')
            evidence(root, row['target_evidence'])
            evidence(root, row['warrant_review'])
    return {(r['question'], r['tool']): r for r in rows}


def validate_evaluation(tool, root):
    decision = tool.get('evaluation_completion')
    if decision is None:
        return {'status': 'evaluated' if tool['fully_integrated'] else 'incomplete',
                'closed': bool(tool['fully_integrated']),
                'effect_evaluated': bool(tool['fully_integrated'])}
    require(decision.get('status') in EVALUATION_DECISIONS, 'Unknown evaluation disposition')
    require(decision.get('scope') and decision.get('reason') and decision.get('reopen_when'),
            'Evaluation needs scope, reason and reopening condition')
    if decision['status'] == 'incomplete':
        require(not tool['fully_integrated'], 'Incomplete evaluation cannot be integrated')
        return {'status': 'incomplete', 'closed': False, 'effect_evaluated': False}
    matrix_ref = decision.get('applicability')
    require(matrix_ref, 'Closed disposition needs all original applicability decisions')
    verify(Path(root), matrix_ref)
    matrix = validate_applicability(read(safe(Path(root), matrix_ref['path'])), root)
    pairs = [matrix[q, tool['id']] for q in QUESTIONS]
    require(all(p['decision'] in {'applicable', 'not_applicable'} for p in pairs),
            'Unresolved applicability cannot complete evaluation')
    evidence(root, decision.get('evidence'))
    require(decision.get('reviewed') is True and decision.get('question_impact'),
            'Closed evaluation requires review and original-question impact')
    if decision['status'] in {'rejected', 'limited'}:
        require(not tool['fully_integrated'], 'Rejected/limited disposition is not full integration')
        evidence(root, decision.get('applicability_evidence'))
        evidence(root, decision.get('boundary_and_fallback_evidence'))
        require(decision.get('contribution_assessed') is False,
                'Scope decision does not establish matched answer contribution')
        require(all(p['decision'] == 'not_applicable' for p in pairs),
                'Scope-only closure cannot skip an applicable product trial')
    else:
        evaluation = tool.get('evaluation', {})
        require(evaluation.get('route') == 'actual_product' and evaluation.get('matched_inputs') is True
                and evaluation.get('finding') in {'helps', 'no_benefit', 'harmful', 'limited'},
                'Evaluated effect requires a valid actual-product matched comparison')
        for name in ('baseline', 'candidate', 'assessment'):
            evidence(root, evaluation.get(name))
        bindings = evaluation.get('input_bindings', {})
        require(bindings.get('baseline') and bindings['baseline'] == bindings.get('candidate'),
                'Evaluated comparison changes its inputs')
        applicable = {p['question'] for p in pairs if p['decision'] == 'applicable'}
        require(applicable and set(evaluation.get('questions', {})) == applicable,
                'Evaluation must cover every applicable original question')
        stages = tool.get('stages', {})
        require(all(stages.get(k, {}).get('level') == 'live'
                    for k in ('product_invocation', 'downstream_delivery')),
                'Evaluation lacks real product invocation/delivery')
        require(stages.get('negative_and_unsupported', {}).get('level') in {'controlled', 'live', 'evaluated'}
                and stages.get('answer_contribution', {}).get('level') == 'evaluated',
                'Evaluation lacks boundary or contribution evidence')
    return {'status': decision['status'], 'closed': True,
            'effect_evaluated': decision['status'] == 'evaluated'}


def validate_inventory(document, obligation_ids, reading_ids, root):
    """Retain inherited populations while allowing reviewed substantive dispositions."""
    require(document.get('profile') == 'legal-original-inventory-review.v1', 'Unknown inventory review')
    expected = {('obligation', i) for i in obligation_ids} | {('reading', i) for i in reading_ids}
    records = document.get('records', [])
    ids = [(r.get('kind'), r.get('id')) for r in records]
    require(len(ids) == len(set(ids)) and set(ids) == expected, 'Original inventory record lost')
    allowed = {'unreviewed', 'retained', 'duplicate', 'irrelevant', 'unsupported_demand', 'external_fact'}
    for row in records:
        require(row.get('disposition') in allowed and row.get('reason'), 'Invalid record disposition')
        evidence(root, row.get('evidence'))
        if row['disposition'] != 'unreviewed':
            require(row.get('reviewed') is True and row.get('question_impact')
                    and row.get('reopen_when'), 'Inventory disposition needs substantive review')
            evidence(root, row.get('review_evidence'))
        if row['disposition'] == 'duplicate':
            require((row['kind'], row.get('duplicate_of')) in expected
                    and row['duplicate_of'] != row['id'], 'Invalid duplicate target')
            target = next(r for r in records if (r['kind'], r['id']) == (row['kind'], row['duplicate_of']))
            require(target['disposition'] == 'retained', 'Duplicate must resolve to a retained record')
        if row['disposition'] == 'external_fact':
            require(row.get('conditional_answer') and row.get('evidence_request'),
                    'Missing facts require conditional analysis and a specific evidence request')
    return records


def evaluation_summary(tools, root):
    selected = [t for t in tools if t['id'] in TOOLS]
    decisions = {t['id']: validate_evaluation(t, root) for t in selected}
    return {'selected_tools_fully_integrated': sum(t['fully_integrated'] for t in selected),
            'selected_tools_fully_evaluated': sum(d['effect_evaluated'] for d in decisions.values()),
            'selected_tool_dispositions_complete': sum(d['closed'] for d in decisions.values()),
            'selected_tool_evaluation_decisions': decisions,
            'all_selected_tool_dispositions_complete': len(selected) == len(TOOLS) and
                all(d['closed'] for d in decisions.values())}
