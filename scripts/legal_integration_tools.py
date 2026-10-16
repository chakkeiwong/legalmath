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
    TOOL_IDS = frozenset({'bm25', 'legalruleml', 'pyarg', 'carneades', 'clingo', 'logical-english'})
    DEFAULT_TOOLS = ('bm25', 'legalruleml', 'pyarg', 'carneades', 'clingo')

    def __init__(self, tools=None):
        selected = tuple(self.DEFAULT_TOOLS if tools is None else tools)
        if not selected or len(set(selected)) != len(selected) or not set(selected) <= self.TOOL_IDS:
            raise LegalMathError('E_SCHEMA', details='Invalid explicit tool selection')
        self.tools = tuple(sorted(selected))

    def identity(self):
        from scripts.legal_native_identity import selected_content
        paths = [Path(__file__), ROOT/'scripts/legal_gap_worker.py', ROOT/'scripts/legal_tool_worker.py',
                 ROOT/'scripts/legal_gap_program.py', RES/'venv/bin/python',
                 OLD/'T2/attempt-1/carneades-adapter/trial',
                 ROOT/'.localresources/assurance-tools/venv/bin/python',
                 ROOT/'src/legalmath/interpretation/assurance/sidecar.py',
                 ROOT/'src/legalmath/interpretation/assurance/diversity.py']
        paths += sorted(RES.glob('*.json'))
        paths.append(ROOT / 'scripts/legal_native_identity.py')
        result = {'profile': 'retained-product-tool-backend.v3', 'files': [ref(p) for p in paths],
                'package_content': selected_content(self.tools, RES, ROOT),
                'selected_tools': list(self.tools),
                'semantics': 'source-bound retrieval, Boolean AST preservation, effective grounded/preferred/stable graphs',
                'unsupported': ['general English equivalence', 'legal warrant', 'case analogy', 'unformalized and non-Boolean meanings']}
        if 'logical-english' in self.tools:
            from scripts.legal_mission_logical_english import identity
            result['logical_english'] = identity()
        return result

    def retrieval(self, packet, inputs, work):
        if 'bm25' not in self.tools:
            return {'status': 'UNSUPPORTED', 'tool': 'BM25', 'reason': 'DISABLED_BY_PROFILE',
                    'limit': 'Explicitly disabled; no retrieval result supplied.'}
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
        results = []
        if 'legalruleml' in self.tools:
            results.append(self._legalruleml(packet, candidates, work))
        if 'logical-english' in self.tools:
            from scripts.legal_mission_logical_english import check
            results.append(check(packet, candidates, work / 'logical-english'))
        if len(results) == 1: return results[0]
        return {'status': 'FAILED' if any(r['status']=='FAILED' for r in results) else 'PASS' if any(r['status']=='PASS' for r in results) else 'UNSUPPORTED',
                'tool': 'Candidate tools', 'results': results,
                'candidate_bindings': {cid:digest(r) for cid,r in candidates.items()},
                'limit': 'Independent selected representation checks; no legal warrant established.'}

    def _legalruleml(self, packet, candidates, work):
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
                declared = {f['name'] for f in formal['facts']}
                if len(declared) != len(formal['facts']):
                    raise LegalMathError('E_REFERENCE', details='DUPLICATE_FACT')
                units = {u['unit_id']:u['text'] for u in packet['units']}
                if any(not set(f['source_unit_ids']) <= units.keys() for f in formal['facts']):
                    raise LegalMathError('E_REFERENCE', details='FOREIGN_FACT_SOURCE')
                if not r['citations'] or any(not c['quote'] or
                        units.get(c['unit_id'],'').count(c['quote']) != 1 for c in r['citations']):
                    raise LegalMathError('E_REFERENCE', details='INVALID_CITATION')
                trees = {k:expression(formal[k],k) for k in ('scope','result')}
                def facts(value):
                    if isinstance(value,dict):
                        if value.get('op') == 'fact': yield value['name']
                        for item in value.values(): yield from facts(item)
                    elif isinstance(value,list):
                        for item in value: yield from facts(item)
                if not set(facts(trees)) <= declared:
                    raise LegalMathError('E_REFERENCE', details='UNDECLARED_FACT')
                encoded.append({'id': cid, **trees})
            except LegalMathError as exc:
                unsupported.append({'candidate_id': cid, 'reason': exc.details or exc.code})
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
        selected = set(self.tools) & {'pyarg','carneades','clingo'}
        if not selected:
            return {'status':'UNSUPPORTED','tool':'Argument tools','reason':'DISABLED_BY_PROFILE',
                    'limit':'No argument engine selected.'}
        proposal, evaluation = inputs['proposal'], inputs['evaluation']
        try: case = effective_graph(proposal, evaluation)
        except ValueError as exc:
            return {'status':'UNSUPPORTED','tool':'Argument tools','reason':'GRAPH_PROFILE_CAPACITY',
                    'selected_tools':sorted(selected),'limit':str(exc)}
        if case is None:
            return {'status': 'UNSUPPORTED', 'tool': 'PyArg/Carneades',
                    'selected_tools':sorted(selected),'reason': evaluation['status'], 'limit': 'No complete effective product graph supplied.'}
        save(work/'effective-graph.json', case)
        checks = {}
        if 'pyarg' in selected:
            external = worker('pyarg', {'cases': [case]}, work/'pyarg')
            row = external['cases'][0]
            checks['pyarg'] = {'grounded':row['grounded'],'preferred':row['preferred'],
                'agrees':row['grounded']==[evaluation['semantics']['grounded']],
                'evidence':ref(work/'pyarg/output.json')}
        if 'carneades' in selected:
            native = work/'carneades'
            save(native/'input.json', {'cases': [case]})
            command([OLD/'T2/attempt-1/carneades-adapter/trial', native/'input.json', native/'output.json'], native, 'run')
            row=read(native/'output.json')['cases'][0]
            checks['carneades']={'grounded':row['grounded'],'preferred':row['preferred'],
                'agrees':row['grounded']==[evaluation['semantics']['grounded']],
                'evidence':ref(native/'output.json')}
        if {'pyarg','carneades'} <= selected:
            checks['preferred_agreement']={'agrees':checks['pyarg']['preferred']==checks['carneades']['preferred']}
        if 'clingo' in selected:
            stable=work/'normalized-stable'
            save(stable/'input.json',{'criticism':{'proposal':{
                'arguments':[{'argument_id':i} for i in case['ids']],
                'attacks':[{'attacker':a,'target':b} for a,b in case['attacks']]}}})
            command([ROOT/'.localresources/assurance-tools/venv/bin/python','-m',
                     'legalmath.interpretation.assurance.sidecar','arguments','--input',stable/'input.json',
                     '--output',stable/'output.json'],stable,'run',env={'PYTHONPATH':str(ROOT/'src')})
            checked=read(stable/'output.json')
            checks['clingo']={'extensions':checked.get('clingo',{}).get('extensions'),
                'agrees':checked['status']=='PASS' and sorted(checked['clingo']['extensions'])==sorted(evaluation['semantics']['stable_extensions']),
                'evidence':ref(stable/'output.json')}
        return {'status':'PASS' if all(c['agrees'] for c in checks.values()) else 'FAILED',
            'tool':'Argument tools','selected_tools':sorted(selected),'graph_hash':digest(case),
            'eligible_arguments':case['ids'],'defeats':case['attacks'],
            'blocked_arguments':evaluation['blocked_arguments'],
            'conditional_arguments':evaluation['conditional_arguments'],
            'unaccepted_preference_proposals':evaluation['preference_proposals'],
            'checks':checks,'evidence':ref(work/'effective-graph.json'),
            'limit':'Effective graph computation on supplied premises; source-to-warrant correctness unassessed.'}
