"""Fixed reviewer controls; these are never production legal answers."""
from copy import deepcopy


def control_answers(records, *, mutation=False, missing=False):
    support = [{'record_id': r['id'], 'quote': r['text'], 'locator': ''}
               for r in (records[0], records[-1])]
    if missing:
        conclusion = (
            'DUTY_UNRESOLVED: The stipulated inability to reconcile activates the baseline '
            'reconciliation block. The stipulated court order to prevent imminent loss also '
            'engages the expressly incorporated Emergency Schedule Z priority rule. Its text '
            'is absent from the supplied material, so the ultimate blocking duty cannot yet '
            'be determined. If Schedule Z leaves the block controlling, or an override does '
            'not apply on its actual conditions, the custodian must block. If its applicable '
            'priority rule overrides the block for this transfer, this reconciliation rule '
            'does not require blocking. Such an override alone would not establish a positive '
            'duty to transfer, actual compliance, or any operational outcome. Obtain the '
            'operative Schedule Z text and then identify any additional facts required by '
            'its actual conditions. Its absence here does not establish that it is absent '
            'from the synthetic regime. The other delivered recordkeeping, retention, roster '
            'and archive rules supply no stated priority rule; no finding of compliance '
            'with those distinct duties follows from the stipulated facts.')
        alternatives = [
            {'condition': 'Schedule Z leaves the reconciliation block controlling or an applicable override condition fails.',
             'consequence': 'The custodian must block under the activated reconciliation rule.'},
            {'condition': 'Schedule Z overrides the block for this transfer and its actual applicability conditions hold.',
             'consequence': 'The reconciliation rule does not require blocking; a positive duty to transfer and actual compliance remain separate.'},
        ]
        unresolved = ['The operative Emergency Schedule Z text is absent from the supplied material; any further factual needs depend on its actual conditions.']
    else:
        conclusion = ('DUTY_REQUIRED: The stipulated reconciliation failure activates the block, '
            'and the emergency clause expressly retains it for this court-ordered emergency transfer.'
            if mutation else 'DUTY_NOT_REQUIRED: Although reconciliation failure activates the baseline block, '
            'the stipulated court-ordered transfer to prevent imminent loss falls within the express exemption.')
        alternatives, unresolved = [], []
    supported = {'conclusion': conclusion, 'support': support, 'contrary': [],
                 'assumptions': [], 'alternatives': alternatives, 'unresolved': unresolved}
    opposite = 'DUTY_NOT_REQUIRED' if mutation else 'DUTY_REQUIRED'
    unsupported = {'conclusion': opposite + ': Treat the reconciliation block as decisive without considering other clauses.',
                   'support': deepcopy(support), 'unresolved': deepcopy(unresolved)}
    return [('supported', supported), ('unsupported', unsupported)]
