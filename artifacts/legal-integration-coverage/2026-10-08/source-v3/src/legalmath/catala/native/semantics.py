"""Explicit native policy: finite conformance never implies RuleIR equivalence."""
from ...canonical import digest
from ...errors import LegalMathError

SEMANTICS = {
    'id': 'legalmath.catala.native-semantics.v2',
    'numbers': 'unbounded integer arithmetic; exact reduced rationals; boundary limit 1000 digits',
    'money': 'integer minor units; source-declared currency; Catala money conversion rounds ties away from zero',
    'rounding_location': 'explicit in candidate source; no host precomputation or silent intermediate rounding',
    'date': 'calendar date; candidate explicitly declares rounding for ambiguous duration addition',
    'required_evidence': 'all required inputs complete, nonconflicting and eligible at valid/known times or abstain',
    'optional_absence': 'known Catala Absent differs from unknown or incomplete evidence',
    'exceptions': 'pinned native default calculus; identical literal consequences may coalesce; distinct overlaps conflict',
    'interface': 'acyclic records, lists, optional values, enums with optional payloads; declared numeric bounds',
    'compatibility': 'RuleIR equivalence only on declared shared fragment and complete admissible inputs',
    'runtime_errors': 'explicit failure; never converted to a false legal predicate',
    'execution_evidence': 'actual source-position conditions, branches and selected enum/option arms plus scope outputs',
}


def profile(task):
    return task.get('native_profile', 'legalmath.catala.native.v1')


def commitment(task):
    return {'semantics': SEMANTICS, 'semantics_hash': digest(SEMANTICS)} if profile(task).endswith('.v2') else {}


def require_profile(task):
    if profile(task) != 'legalmath.catala.native.v2':
        raise LegalMathError('E_UNSUPPORTED_PROFILE', details='Optional/payload/import features require an explicit native.v2 task')
