"""Evidence actions, version-bound answer reuse and economical residual questions."""
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import re
from ...canonical import digest, loads
from ...errors import LegalMathError
from .monitor import immutable
from .semantics import check_quotes

# Relative work estimates, not monetary charges or probabilities. Evidence actions
# precede human questions and an unchanged failed action cannot receive more votes.
COSTS = {'REUSE_SUPPORTED_ANSWER': 1, 'ACQUIRE_AUTHORITY': 2, 'REEXTRACT': 2,
         'FORMAL_COUNTEREXAMPLE': 3, 'CHECK_SOURCE_CLAIM': 4, 'REPAIR_STAGE': 5,
         'INTERNAL_QUESTION': 20, 'EXTERNAL_QUESTION': 100}


def action_key(action, scope):
    return digest({'kind': action['kind'], 'issue_key': action['issue_key'],
                   'inputs': action.get('inputs', {}), 'scope': scope})


def choose_action(actions, attempted, scope, *, remaining_cost, allow_human=False):
    eligible = []
    for action in actions:
        if action['kind'] not in COSTS:
            raise LegalMathError('E_SCHEMA')
        cost = COSTS[action['kind']]
        if action_key(action, scope) in attempted or cost > remaining_cost:
            continue
        if action['kind'] in ('INTERNAL_QUESTION', 'EXTERNAL_QUESTION') and not allow_human:
            continue
        gain = action.get('separated_pairs', 1)
        if type(gain) is not int or gain < 0:
            raise LegalMathError('E_SCHEMA')
        eligible.append((Fraction(max(1, gain), cost), -cost, action_key(action, scope), action))
    if not eligible:
        return None
    return deepcopy(max(eligible, key=lambda item: item[:3])[3])


def scoped_question(question):
    return re.sub(r'\s+', ' ', question).strip().casefold()


class Answers:
    """Reuse diagnostic evidence; an answer is never a bank approval."""
    def __init__(self, directory):
        self.directory = Path(directory)

    def record(self, question, answer, scope, evidence, packet, *, evidence_class, limitations):
        if evidence_class not in ('PUBLIC_EXAMPLE', 'RECORDED_DECISION', 'MACHINE_DIAGNOSTIC'):
            raise LegalMathError('E_SCHEMA')
        if not question.strip() or not answer.strip() or not evidence or not limitations:
            raise LegalMathError('E_SCHEMA')
        check_quotes(evidence, packet)
        record = {'question': scoped_question(question), 'answer': answer, 'scope': deepcopy(scope),
                  'evidence': evidence, 'source_packet_hash': digest(packet), 'evidence_class': evidence_class,
                  'limitations': limitations, 'release_eligible': False}
        return immutable(self.directory, record)

    def lookup(self, question, scope, packet):
        matches = []
        for path in sorted(self.directory.glob('*.json')):
            record = loads(path.read_bytes())
            if digest(record) != path.stem:
                raise LegalMathError('E_INTEGRITY')
            if (record['question'] == scoped_question(question) and record['scope'] == scope
                    and record['source_packet_hash'] == digest(packet)):
                check_quotes(record['evidence'], packet); matches.append({'answer_hash': path.stem, **record})
        return matches


def residual_questions(findings, attempted=()):
    """Deduplicate questions while retaining all affected claims and candidates."""
    groups = {}
    for finding in findings:
        question = finding.get('question') or finding.get('details') or finding.get('title_or_locator')
        if not isinstance(question, str) or not question.strip():
            question = finding['kind'].replace('_', ' ').capitalize()
        identity = digest({'stage': finding.get('stage', 'DEPENDENCY'), 'question': scoped_question(question),
                           'unit_id': finding.get('unit_id'), 'claim_id': finding.get('claim_id')})
        row = groups.setdefault(identity, {'question_id': 'q.' + identity[:24], 'question': question,
            'stage': finding.get('stage', 'DEPENDENCY'), 'findings': [], 'candidate_ids': [],
            'evidence_actions_attempted': [], 'external_consultancy_required': False,
            'disposition': 'UNRESOLVED_AFTER_BOUNDED_AUTOMATION'})
        row['findings'].append(deepcopy(finding))
        if finding.get('candidate_id') and finding['candidate_id'] not in row['candidate_ids']:
            row['candidate_ids'].append(finding['candidate_id'])
    for row in groups.values():
        row['evidence_actions_attempted'] = [deepcopy(a) for a in attempted if any(
            a.get('candidate_id') == c for c in row['candidate_ids']) or a.get('stage') == row['stage']]
    return sorted(groups.values(), key=lambda r: (r['stage'], r['question_id']))
