"""Read-only diagnosis of the final rejected model-to-candidate binding."""
import sys

sys.path.insert(0, '/home/chakwong/python/legalmath')
from scripts.legal_integration_coverage import OUT, read, ref, immutable
from scripts import legal_coverage_aliases as aliases

base = OUT / 'batches/combined/17/attempt-02'
rows = []
for folder in (base / 'response-aliases').iterdir():
    request = read(folder / 'original-request.json')
    schema = read(folder / 'original-schema.json')
    references = read(folder / 'references.json')
    raw = read(folder / 'raw-response.json')['value']
    expanded = read(folder / 'expanded-response.json')
    assert aliases.resolve(raw, request, schema, references) == expanded
    for row in raw['checks']:
        ci, ri = references['pairs'][row['pair']]
        candidate = request['candidates'][ri]
        if (candidate['candidate_id'] != 'deferred.7cda521da78c24227e5a7440' or
                row['executable_correspondence']['status'] != 'PRESERVES'):
            continue
        executable = {s['span_id']: s for s in request['executable_references']['spans']}
        selected = [references['executable_spans'][int(k[1:])]
                    for k in row['executable_correspondence']['representation_quotes']]
        rows.append({'request': ref(folder / 'original-request.json'),
            'raw_reply': ref(folder / 'raw-response.json'),
            'expanded_reply': ref(folder / 'expanded-response.json'),
            'alias_table': ref(folder / 'references.json'), 'pair_key': row['pair'],
            'claim': request['claims'][ci], 'candidate': candidate,
            'selected_executable_spans': [executable[k] for k in selected],
            'raw_judgment': row, 'alias_expansion_exact': True})
assert len(rows) == 1
assert rows[0]['candidate']['representation'].startswith('UNAVAILABLE_EXECUTABLE_MEANING:')
assert all(s['candidate_id'] != rows[0]['candidate']['candidate_id']
           for s in rows[0]['selected_executable_spans'])
immutable(OUT / 'final-rejection-trace.json', {
    'status': 'RETURNED_CANDIDATE_CONFUSION_REJECTED',
    'receipt': ref(base / 'receipt.json'), 'result': ref(base / 'scoped/result.json'),
    'findings': rows, 'codec_expansion_changed_identity': False,
    'legal_judgment_locally_rewritten': False,
    'cause_limit': 'The raw response selected another candidate\'s expressions and reasoned about its trigger question. The evidence does not isolate the model\'s reason for confusing the candidates.'})
print({'status': 'RETURNED_CANDIDATE_CONFUSION_REJECTED', 'alias_expansion_exact': True,
       'foreign_executable_selections': len(rows[0]['selected_executable_spans'])})
