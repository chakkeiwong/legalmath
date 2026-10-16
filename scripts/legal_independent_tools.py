"""Optional product backend with independent, retained adapter outcomes."""
from copy import deepcopy
from itertools import combinations
from pathlib import Path

from legalmath.canonical import digest
from legalmath.errors import LegalMathError
from legalmath.interpretation.assurance.failure_policy import shared_failure
from scripts.legal_integration_tools import ProductToolBackend, effective_graph
from scripts.legal_gap_program import ref


def preferred_extensions(case):
    """Inclusion-maximal conflict-free sets defending each of their members."""
    nodes = sorted(case['ids'])
    if len(nodes) != len(set(nodes)) or len(nodes) > 12:
        raise ValueError('Preferred semantics requires at most 12 distinct nodes')
    edges = {tuple(e) for e in case['attacks']}
    if any(len(e) != 2 or not set(e) <= set(nodes) for e in edges):
        raise ValueError('Foreign graph endpoint')
    admissible = []
    for size in range(len(nodes) + 1):
        for members in combinations(nodes, size):
            chosen = set(members)
            if any(a in chosen and b in chosen for a, b in edges):
                continue
            defeated = {b for a, b in edges if a in chosen}
            if all(a in defeated for a, b in edges if b in chosen):
                admissible.append(chosen)
    return sorted(sorted(s) for s in admissible if not any(s < t for t in admissible))


class IndependentProductToolBackend(ProductToolBackend):
    """Use existing installed adapters, with no retry or change to legal inputs.

    Every selected adapter is attempted. A mixed result stays FAILED; neither a
    successful sibling nor this continuation policy turns a failure into PASS.
    """
    def identity(self):
        return {**super().identity(), 'profile': 'independent-product-tools.v1',
                'independence_implementation': ref(Path(__file__))}

    def _run_one(self, tool, kind, packet, inputs, work):
        return getattr(ProductToolBackend([tool]), kind)(packet, inputs, work)

    def retrieval(self, packet, inputs, work):
        if 'bm25' not in self.tools:
            return super().retrieval(packet, inputs, work)
        try:
            return self._run_one('bm25', 'retrieval', deepcopy(packet), deepcopy(inputs), work)
        except Exception as exc:
            if shared_failure(exc):
                raise
            return {'status': 'FAILED', 'tool': 'BM25', 'query': inputs['question'],
                    'error': getattr(exc, 'code', type(exc).__name__),
                    'reason': str(getattr(exc, 'details', None) or exc)[:1000],
                    'limit': 'Retrieval failed; no source or relevance conclusion.'}

    def _panel(self, selected, kind, packet, inputs, work):
        rows = []
        for tool in sorted(selected):
            try:
                row = self._run_one(tool, kind, deepcopy(packet), deepcopy(inputs), work / tool)
                if not isinstance(row, dict) or row.get('status') not in {'PASS', 'FAILED', 'UNSUPPORTED'}:
                    raise ValueError('Adapter returned no valid explicit status')
                if kind == 'criticism' and tool in {'pyarg', 'carneades'} and row['status'] != 'UNSUPPORTED':
                    case = effective_graph(inputs['proposal'], inputs['evaluation'])
                    check = row['checks'][tool]
                    check['preferred_reference'] = preferred_extensions(case)
                    check['preferred_agrees'] = sorted(sorted(e) for e in check['preferred']) == check['preferred_reference']
                    check['agrees'] = check['agrees'] and check['preferred_agrees']
                    if not check['agrees']:
                        row['status'] = 'FAILED'
            except Exception as exc:
                if shared_failure(exc):
                    raise
                # Only adapter execution is inside this boundary. ToolSession
                # checks authoritative bindings and identity outside it.
                row = {'status': 'FAILED', 'error': getattr(exc, 'code', type(exc).__name__),
                       'reason': str(getattr(exc, 'details', None) or exc)[:1000],
                       'limit': 'Adapter failed; do not use this result to corroborate an answer.'}
                if kind == 'criticism':
                    row.update(tool='Argument tools', selected_tools=[tool], checks={})
                else:
                    row['tool'] = {'legalruleml': 'LegalRuleML', 'logical-english': 'Logical English'}[tool]
            rows.append(row)
        return {'status': 'FAILED' if any(r['status'] == 'FAILED' for r in rows) else
                'PASS' if any(r['status'] == 'PASS' for r in rows) else 'UNSUPPORTED',
                'tool': 'Independent optional checks', 'results': rows,
                'candidate_bindings': {k: digest(v) for k, v in inputs.items()} if kind == 'candidates' else {},
                'limit': 'Individual outcomes retained; no legal warrant or full tool acceptance inferred.'}

    def candidates(self, packet, candidates, work):
        return self._panel(set(self.tools) & {'legalruleml', 'logical-english'}, 'candidates', packet, candidates, work)

    def criticism(self, packet, inputs, work):
        return self._panel(set(self.tools) & {'pyarg', 'carneades', 'clingo'}, 'criticism', packet, inputs, work)
