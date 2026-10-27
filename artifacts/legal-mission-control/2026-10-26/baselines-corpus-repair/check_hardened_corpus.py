"""Check source attribution only; do not invent applicability/source-use reviews."""
from collections import Counter
from hashlib import sha256
from pathlib import Path
import importlib.util
import json
import sys
import tempfile

ROOT = Path('/home/chakwong/python/legalmath')
OUT = Path(__file__).resolve().parent
CANDIDATE = Path('/tmp/legalmath-baselines-corpus-hardened')
sys.path[:0] = [str(CANDIDATE / 'src'), str(CANDIDATE)]
from legalmath.interpretation.assurance import corpus_review as corpus
from legalmath.errors import LegalMathError

def read(p):
    return json.loads(p.read_text())

def ref(p):
    return {'path':str(p.relative_to(ROOT)), 'sha256':sha256(p.read_bytes()).hexdigest()}

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

fixtures = module('hardened_fixture', CANDIDATE/'tests/assurance/test_baseline_corpus_repairs.py')
with tempfile.TemporaryDirectory(prefix='hardened-corpus-negative-') as directory:
    temporary = Path(directory)
    expected, bundle = fixtures.corpus_setup(temporary)
    wrong = fixtures.put(temporary,'unrelated.txt','Unrelated document assertion.')
    for row in bundle['applicability']:
        for duty in ('applicability','later_treatment'):
            row[duty]['primary_evidence'][0].update(passage=wrong,quote='Unrelated document assertion.')
    for row in bundle['answer_use']:
        for proposition in row['propositions']:
            proposition['primary_evidence'][0].update(passage=wrong,quote='Unrelated document assertion.')
    try:
        corpus.evaluate(temporary,expected,fixtures.put(temporary,'bundle.json',bundle))
    except LegalMathError as exc:
        adverse = {'status':'REJECTED','reason':str(exc),'details':getattr(exc,'details',None)}
    else:
        raise AssertionError('Unrelated passage still qualifies')
fidelity_path = ROOT/'artifacts/legal-mission-control/2026-10-13/master/corpus-qualification/attempt-6/corpus-reconciliation.json'
fidelity = read(fidelity_path)
counts, references, legacy_rejections = Counter(), [ref(fidelity_path)], []
for region in ('2023','2025','handbook'):
    evidence_path = ROOT/f'artifacts/legal-mission-control/2026-10-13/master/ownership-{region}/attempt-3/evidence.json'
    evidence = read(evidence_path)
    pointer = evidence['ownership']
    ownership = corpus.read(ROOT,pointer)
    source = ownership['source']
    references.extend([ref(evidence_path),pointer,source])
    collections = ('clauses',) if region == 'handbook' else ('main_paragraphs','full_components','full_footnotes')
    for collection in collections:
        for position, item in enumerate(ownership[collection]):
            if collection == 'full_components' and (item.get('region') != 'reasons' or not item.get('owner')):
                continue
            locator = (item['section']+':'+item['label'] if collection == 'clauses' else
                'FN'+item['display'] if collection == 'full_footnotes' else
                item['owner'] if collection == 'full_components' else item['locator'])
            support = {'source_id':region,'source':source,'passage':pointer,
                'passage_pointer':f'/{collection}/{position}/text',
                'locator':locator,'quote':item['text']}
            if collection == 'main_paragraphs' and item.get('rendered_label_verified') is not True:
                try:
                    corpus.support(ROOT,[support],{region:source},{region},fidelity)
                except LegalMathError:
                    legacy_rejections.append({'region':region,'locator':locator,
                        'reason':'Legacy label flag remains false; use exact qualified full_components text with superscripts retained.'})
                    continue
                raise AssertionError('Unqualified legacy paragraph accepted')
            corpus.support(ROOT,[support],{region:source},{region},fidelity)
            counts[region+':'+collection] += 1
sys.path.insert(1,str(ROOT))
handler = module('hardened_actual_corpus_handler', CANDIDATE/'scripts/legal_integration_qualification_continuation.py')
directory = OUT/'corpus-handler-hardened'
directory.mkdir(exist_ok=True)
outcome = handler.corpus(directory)
assert outcome['_node_status'] == 'BLOCKED'
assert read(directory/'corpus-reconciliation.json') == fidelity
result = {'profile':'hardened-corpus-attribution-check.v1','unrelated_passage':adverse,
    'verified_actual_passages':dict(counts),'total_actual_passages':sum(counts.values()),
    'unqualified_legacy_rows_rejected':legacy_rejections,
    'references':references,'actual_handler':outcome,'fidelity_exactly_preserved':True,
    'provider_calls':0,'live_attempts':0,'legal_acceptance':False,
    'scope':'Exact source/ownership/passage attribution; no applicability, later-treatment or answer-use verdict.'}
destination = OUT/'corpus-attribution-hardened.json'
if destination.exists():
    assert read(destination) == result
else:
    destination.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({k:result[k] for k in ('unrelated_passage','verified_actual_passages','total_actual_passages','provider_calls','legal_acceptance')}))
