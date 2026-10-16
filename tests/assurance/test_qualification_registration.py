from scripts import legal_integration_qualification_continuation as continuation
from scripts.legal_integration_acceptance_revision import historical_projection


def test_registration_preserves_historical_program_references_without_reprojecting_program():
    previous = {'path': str(continuation.PROGRAM), 'sha256': 'previous'}
    archived = {'path': 'before/program.json', 'sha256': 'previous'}
    baseline = {'projected_paths': [], 'archived': [{'previous': previous, 'archive': archived}]}
    mission = {'history': [{'result_evidence': [previous]}]}
    projected = historical_projection(mission, continuation.projected_archives(baseline, mission=True))
    assert projected['history'][0]['result_evidence'] == [archived]
    assert historical_projection(mission, continuation.projected_archives(baseline)) == mission


def test_program_details_do_not_replace_distinct_historical_registration():
    from copy import deepcopy
    historical = {'prior_detours': 19, 'additional_consolidated_revision': 1,
        'prior_charged_calls': 175, 'review': {'path': 'review.md', 'sha256': 'same'}}
    master = {'reviewed_reopening': deepcopy(historical),
        'repair': {'profile': 'same-profile', 'prior_state': 'old'}}
    program = {'reviewed_reopening': {'prior_state': 'details', 'prior_calls': 175},
        'repair': {'profile': 'same-profile', 'prior_state': 'archived'},
        continuation.KEY: {'profile': 'current-profile', 'prior_state': 'current'}}
    continuation.synchronize_revisions(master, program)
    assert master['reviewed_reopening'] == historical
    assert master['repair'] == program['repair']
    assert master[continuation.KEY] == program[continuation.KEY]
