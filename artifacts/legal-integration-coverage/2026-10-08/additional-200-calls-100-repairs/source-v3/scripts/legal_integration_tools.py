"""Installed tool backends for the product's optional validated checkpoints."""
from pathlib import Path

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.translation.expressions import expression
from scripts.legal_gap_program import ROOT, RES, OLD, worker, command, read, save, ref


def effective_graph(proposal, evaluation):
    if 'semantics' not in evaluation:
        return None
    eligible = sorted({a['argument_id'] for a in proposal['arguments']} - set(evaluation['blocked_arguments']))
    edges = sorted({tuple(e) for e in evaluation['defeats'] if set(e) <= set(eligible)})
    if len(eligible) > 12 or len(eligible) != len(set(eligible)):
        raise ValueError('Bounded product graph requires at most twelve unique arguments')
    return {'id': 'effective-product-defeats', 'ids': eligible, 'attacks': [list(e) for e in edges]}


class ProductToolBackend:
    def identity(self):
        paths = [Path(__file__), ROOT/'scripts/legal_gap_worker.py', ROOT/'scripts/legal_tool_worker.py',
                 ROOT/'scripts/legal_gap_program.py', RES/'venv/bin/python',
                 OLD/'T2/attempt-1/carneades-adapter/trial',
                 ROOT/'.localresources/assurance-tools/venv/bin/python',
                 ROOT/'src/legalmath/interpretation/assurance/sidecar.py',
                 ROOT/'src/legalmath/interpretation/assurance/diversity.py']
        paths += sorted(RES.glob('*.json'))
        return {'profile': 'retained-product-tool-backend.v1', 'files': [ref(p) for p in paths],
                'semantics': 'source-bound retrieval, Boolean AST preservation, effective grounded/preferred/stable graphs',
                'unsupported': ['general English equivalence', 'legal warrant', 'case analogy', 'unformalized and non-Boolean meanings']}

    def retrieval(self, packet, inputs, work):
        units = {u['unit_id']: u['text'] for u in packet['units']}
        result = worker('retrieval', {'corpus': {'units': [{'id': k, 'text': v} for k, v in units.items()]},
            'questions': [{'id': 'exact-product-question', 'question': inputs['question']}]}, work/'retrieval')
        selected = [r for r in result['rows'] if r['mode'] == 'passage_bm25']
        passages = []
        for row in selected:
            for index, p in enumerate(row['passages']):
                if p['unit_id'] not in units or units[p['unit_id']][p['start']:p['end']] != p['text']:
                    raise LegalMathError('E_INTEGRITY', details='Retrieved passage changed source text or offsets')
                passages.append({'rank': index+1, **{k: v for k, v in p.items() if k != 'score'}})
        return {'status': 'PASS', 'tool': 'BM25', 'query': inputs['question'], 'passages': passages,
                'target_question_hash':inputs.get('question_hash'),'target_candidate_id':inputs.get('candidate_id'),
                'evidence': ref(work/'retrieval/output.json'),
                'limit': 'Location assistance on the same packet; no source sufficiency or legal applicability judgment.'}

    def candidates(self, packet, candidates, work):
        encoded, unsupported = [], []
        for cid, r in candidates.items():
            formal = r.get('formalization')
            if not formal:
                unsupported.append({'candidate_id': cid, 'reason': 'UNFORMALIZED'})
                continue
            if formal['result_type'] != 'bool' or any(f['type'] != 'bool' for f in formal['facts']):
                unsupported.append({'candidate_id': cid, 'reason': 'NON_BOOLEAN_PROFILE'})
                continue
            try:
                encoded.append({'id': cid, 'scope': expression(formal['scope'], 'scope'),
                                'result': expression(formal['result'], 'result')})
            except LegalMathError as exc:
                unsupported.append({'candidate_id': cid, 'reason': exc.code})
        result = worker('boolean', {'readings': encoded}, work/'boolean') if encoded else {'readings': []}
        checked = []
        for row in result['readings']:
            if row['status'] == 'UNSUPPORTED':
                unsupported.append({'candidate_id': row['id'], 'reason': row['reason']})
            else:
                checked.append({'candidate_id': row['id'], 'status': row['status'],
                                'mutation_detected': row['mutation_detected']})
        if {r['candidate_id'] for r in checked + unsupported} != set(candidates):
            raise LegalMathError('E_INTEGRITY', details='Optional tool omitted a candidate')
        return {'status': 'FAILED' if any(r['status'] != 'PASS' for r in checked) else 'PASS' if checked else 'UNSUPPORTED',
                'tool': 'LegalRuleML', 'retained_candidates': len(candidates), 'checked': checked,
                'unsupported': unsupported,
                'candidate_bindings': {cid: digest(r) for cid, r in candidates.items()},
                'evidence': ref(work/'boolean/output.json') if encoded else None,
                'limit': 'Boolean AST preservation and mutation detection only. Runtime uncertainty and all legal premises remain outside XML validation.'}

    def criticism(self, packet, inputs, work):
        proposal, evaluation = inputs['proposal'], inputs['evaluation']
        case = effective_graph(proposal, evaluation)
        if case is None:
            return {'status': 'UNSUPPORTED', 'tool': 'PyArg/Carneades',
                    'reason': evaluation['status'], 'limit': 'No complete effective product graph supplied.'}
        save(work/'effective-graph.json', case)
        external = worker('pyarg', {'cases': [case]}, work/'pyarg')
        native = work/'carneades'
        save(native/'input.json', {'cases': [case]})
        command([OLD/'T2/attempt-1/carneades-adapter/trial', native/'input.json', native/'output.json'], native, 'run')
        other = read(native/'output.json')
        # The criticism product defines grounded/stable semantics. Compare its
        # grounded result directly; preferred agreement is an additional check
        # by two external engines, never a substitute for the product target.
        row = external['cases'][0]
        agree = (external['cases'] == other['cases'] and row['grounded'] == [evaluation['semantics']['grounded']])
        # The existing sidecar evaluates whatever abstract graph it receives.
        # Supply effective defeats explicitly here; sending the original raw
        # criticism would compare a different stable-extension target.
        stable=work/'normalized-stable'
        save(stable/'input.json',{'criticism':{'proposal':{
            'arguments':[{'argument_id':i} for i in case['ids']],
            'attacks':[{'attacker':a,'target':b} for a,b in case['attacks']]}}})
        command([ROOT/'.localresources/assurance-tools/venv/bin/python','-m',
                 'legalmath.interpretation.assurance.sidecar','arguments','--input',stable/'input.json',
                 '--output',stable/'output.json'],stable,'run',env={'PYTHONPATH':str(ROOT/'src')})
        checked=read(stable/'output.json')
        stable_agree=(checked['status']=='PASS' and sorted(checked['clingo']['extensions'])==
                      sorted(evaluation['semantics']['stable_extensions']))
        agree=agree and stable_agree
        return {'status': 'PASS' if agree else 'FAILED', 'tool': 'PyArg/Carneades',
                'graph_hash': digest(case), 'eligible_arguments': case['ids'], 'defeats': case['attacks'],
                'blocked_arguments': evaluation['blocked_arguments'],
                'conditional_arguments': evaluation['conditional_arguments'],
                'unaccepted_preference_proposals': evaluation['preference_proposals'],
                'product_grounded': evaluation['semantics']['grounded'], 'external': row,
                'product_stable':evaluation['semantics']['stable_extensions'],'clingo_stable_agree':stable_agree,
                'evidence': [ref(work/'effective-graph.json'), ref(work/'pyarg/output.json'), ref(native/'output.json'),ref(stable/'output.json')],
                'limit': 'Effective defeats after premise blocking and ancestor propagation; proposed priorities remain unaccepted. Grounded and stable product results are checked on this exact graph. Graph acceptance supplies no legal warrant.'}
