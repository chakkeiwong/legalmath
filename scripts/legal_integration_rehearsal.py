"""Original-input product rehearsal with explicitly scripted unresolved answers."""
from pathlib import Path
from legalmath.canonical import digest
from legalmath.interpretation.assurance.bounded_context import tokenizer
from legalmath.interpretation.assurance.bounded_product import PROFILE
from legalmath.interpretation.assurance.monitor import save
from legalmath.interpretation.search.providers import Completion
from scripts.legal_product_completion import run_product


class UnresolvedProvider:
    live = False
    def __init__(self): self.requests = []
    def complete(self, request, schema, settings):
        self.requests.append({"task": request["task"], "request_hash": digest(request)})
        properties = schema['properties']
        if 'records' in properties:
            result = {'records': [{'id': row['id'], 'status': 'UNRESOLVED', 'findings': [],
                                  **({'observations': []} if request['task'] == 'REVIEW_REQUIREMENTS' else {}),
                                  'open_dependencies': ['Scripted mechanics only; no source interpretation.']}
                                 for row in request['records']]}
        elif 'readings' in properties:
            units = request['source_packet']['units']; first = units[0]
            result = {'readings': [{'local_id': 'candidate.scope', 'family': 'scope', 'subject': 'Conditional source reading',
                'statement': 'The governing legal standard remains unresolved.', 'distinction': 'Facts and standards are separate.',
                'citations': [{'unit_id': first['unit_id'], 'quote': first['text']}],
                'assumptions': [], 'questions': ['Which standard applies?'], 'formalization': None}],
                'dimensions': [{'dimension': d, 'status': 'AMBIGUOUS', 'source_unit_ids': [first['unit_id']],
                                'explanation': 'Unresolved scripted control.'} for d in
                               ('scope','definitions','exceptions','modality','time','dependencies')],
                'coverage': [{'unit_id': u['unit_id'], 'status': 'UNCERTAIN', 'reason': 'No live reading.'} for u in units],
                'questions': ['Source review is still required.']}
        elif 'arguments' in properties:
            result = {'arguments': [], 'attacks': [], 'preferences': [], 'cases': [], 'case_queries': [],
                      'questions': ['No warranted argument was supplied by this scripted control.']}
        else:
            sources = [r for r in request['records'] if r['kind'] == 'source']
            quotes = [{'record_id': r['id'], 'quote': r['text'], 'locator': ''} for r in sources[:1]]
            if 'verdict' in properties:
                result = {'verdict': 'UNRESOLVED', 'considered': request['required_considered'],
                    'reason': 'Scripted source review establishes no legal result.', 'support': quotes,
                    'issues': ['Live semantic preservation remains untested.']}
            else:
                result = {'conclusion': 'The stated conclusion depends on an applicable legal standard and facts.',
                    'support': quotes, 'contrary': [], 'assumptions': [], 'unresolved': ['Applicable standard and facts.'],
                    'alternatives': [{'condition': 'The required premise is established',
                                      'consequence': 'Reassess the conditional conclusion against the source.'}],
                    'considered': request['required_considered']}
            if 'source_gaps' in properties: result['source_gaps'] = []
            if 'assertion_bindings' in properties: result['assertion_bindings'] = []
        return Completion(result, {'provider': 'SCRIPTED_UNRESOLVED', 'live': False})


def rehearse(root, directory, envelope, token_path):
    from scripts.legal_mission_execution import ref
    provider = UnresolvedProvider()
    result = run_product(root, directory, provider, Path('/unused-jdk'), '2026-10-13T00:00:00Z',
        sources=[], questions=envelope['original_questions'], acceptance_ref=None, qualification={},
        required={'maximum_calls': 4096}, deadline_utc='2030-01-01T00:00:00+00:00', selected_tools=[],
        settings=None, consumer_profile=PROFILE, bounded_envelope=envelope, bounded_encode=tokenizer(token_path))
    save(Path(directory) / 'rehearsal-summary.json', {
        'scripted_calls': len(provider.requests), 'live_calls': 0,
        'original_input_hash': digest(envelope), 'trace': result['trace'],
        'question_outcomes': {q: {'status': v.get('status', 'EXECUTED'),
                                  'review_accepted': v.get('review_accepted', False),
                                  'reason': v.get('reason')} for q,v in result['answers'].items()},
        'legal_acceptance': False,
        'implementation': [ref(root, root/p) for p in (
            'src/legalmath/interpretation/assurance/bounded_product.py',
            'src/legalmath/interpretation/assurance/dossier_answer.py',
            'src/legalmath/interpretation/assurance/complete_investigation.py',
            'scripts/legal_product_completion.py')]})
    return result


if __name__ == '__main__':
    import os
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    import json
    root = Path(__file__).resolve().parents[1]
    base = root / 'artifacts/legal-mission-control/2026-10-13/master'
    result = rehearse(root, base / 'original-rehearsal-final',
        json.loads((base / 'combined-envelope.json').read_text()),
        root / '.localresources/legal-context-methods-2026-10-12/cl100k_base.tiktoken')
    print((base / 'original-rehearsal-final/rehearsal-summary.json').read_text())
