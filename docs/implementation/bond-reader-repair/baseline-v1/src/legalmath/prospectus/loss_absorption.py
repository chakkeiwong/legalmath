"""Prospectus feature decisions under explicit, qualified source premises.

This question is separate from product complexity and regulatory eligibility.
No issuer name, country, seniority or expected classification is an input.
"""
from itertools import product

FACTS = ('debt', 'principal_write_down', 'mandatory_common_conversion', 'coverage_complete')
LABELS = {True: 'loss absorption', False: 'non loss absorption'}
POLICY = 'prospectus-loss-absorption.v1'


def total(facts):
    """Complete formal premises: a negative additionally requires coverage."""
    loss = facts['principal_write_down'] or facts['mandatory_common_conversion']
    return {'positive': facts['debt'] and loss,
            'negative': facts['debt'] and facts['coverage_complete'] and not loss}


def decide(facts):
    if set(facts) != set(FACTS):
        raise ValueError('Exactly the declared feature premises are required')
    if any(v is not None and v != 'conflict' and type(v) is not bool for v in facts.values()):
        raise ValueError('Premises must be Boolean, unknown or conflict')
    if 'conflict' in facts.values():
        return {'answer': None, 'classification': None, 'status': 'conflicting evidence'}
    if facts['debt'] is False:
        return {'answer': None, 'classification': None, 'status': 'excluded security'}
    missing = [k for k in FACTS if facts[k] is None]
    worlds = [total({**facts, **dict(zip(missing, values))})
              for values in product((False, True), repeat=len(missing))]
    answer = True if all(w['positive'] for w in worlds) else False if all(w['negative'] for w in worlds) else None
    return {'answer': answer, 'classification': LABELS.get(answer) if answer is not None else None,
            'status': 'qualified source reading' if answer is not None else 'needs evidence'}


def explain(decision, evidence, *, issues=(), ordinary_features=()):
    """Render the actual decision/evidence; never supply a prewritten issue answer."""
    if decision['status'] == 'excluded security':
        return 'Excluded: the selected security is not a debt instrument; preferred shares are outside this classification.'
    if decision['status'] == 'conflicting evidence':
        return 'No supported yes/no answer: applicable evidence conflicts. ' + '; '.join(issues)
    if decision['answer'] is None:
        return 'No supported yes/no answer: ' + ('; '.join(issues) or 'the required mechanism or document-coverage premises are unresolved.')
    def cite(item):
        return item['document'] + ', PDF p.' + str(item['page'])
    if decision['answer']:
        clauses = []
        for mechanism in ('principal_write_down', 'mandatory_common_conversion'):
            candidates = [e for e in evidence if e['kind'] == mechanism and e.get('disposition') == 'applicable']
            if not candidates:
                continue
            text = ('the principal can be reduced or cancelled' if mechanism == 'principal_write_down'
                    else 'the bond can be compulsorily converted into common/ordinary shares')
            item = candidates[0]
            origin = (' under a disclosed statutory resolution power' if item.get('origin') == 'statutory-disclosed'
                      else ' under the contractual terms' if item.get('origin') == 'contractual'
                      else ' under the disclosed mechanism (its contractual/statutory origin remains unresolved)')
            clauses.append(text + origin + ' (' + cite(item) + ')')
        if not clauses:
            raise ValueError('A positive explanation requires a supporting mechanism witness')
        return 'Yes: ' + '; '.join(clauses) + '. The power need not have been exercised.'
    repayment = [e for e in evidence if e['kind'] == 'cash_repayment' and e.get('disposition') == 'applicable']
    if not repayment:
        raise ValueError('A negative explanation requires affirmative repayment evidence')
    text = ('No within the examined offering terms: the debt provides for cash principal repayment (' +
            cite(repayment[0]) + '); the declared operative document set has been examined and no applicable '
            'principal write-down or compulsory common-share conversion was identified.')
    if ordinary_features:
        text += ' Separately recorded: ' + ', '.join(sorted(set(ordinary_features))) + '.'
    return text


def specification():
    return {'facts': [(name, 'bool') for name in FACTS],
            'outputs': [
                ('positive', 'bool', '(and debt (or principal_write_down mandatory_common_conversion))'),
                ('negative', 'bool', '(and debt coverage_complete (not principal_write_down) (not mandatory_common_conversion))')],
            'meaning': 'Declared prospectus feature only. Statutory principal loss counts; creditor-approved restructuring is separate. Coverage is an explicit source-analysis premise. No English entailment or trading permission is proved.'}
