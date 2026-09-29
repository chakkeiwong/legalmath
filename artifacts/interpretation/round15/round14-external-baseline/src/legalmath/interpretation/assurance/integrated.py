"""One resumable source-to-tree-to-binary investigation over public sources."""
from pathlib import Path
import json
import os
import subprocess

from ...canonical import digest, raw_digest, loads
from ...errors import LegalMathError
from ..search.formal import bundle, Comparisons, snapshots, RULE
from ..search.models import Settings
from .engine import Assurance, AssuranceSettings
from .workflow import EvidenceJournal, CachedEvidenceProvider
from .diversity import save, identity
from .transport import CompactProvider
from .regions import reconcile_page
from .sources import extract_document


def implementation_identity():
    root = Path(__file__).parents[2]
    return identity({str(p.relative_to(root)): raw_digest(p.read_bytes())
                     for p in sorted(root.rglob('*')) if p.is_file() and p.suffix in ('.py', '.java', '.json')})


def source_processing_identity(tool_python):
    package = Path(__file__).parent; root = package.parents[3]
    paths = [package/name for name in ('sources.py', 'regions.py', 'region_actions.py', 'sidecar.py')]
    paths += [root/'scripts/assurance_source_routes.py']
    paths += [root/'.localresources/assurance-tools'/name for name in
              ('tool-lock.json', 'model-lock.json', 'requirements.lock')]
    return {'profile': 'source-processing.v2', 'tool_python': str(Path(tool_python).resolve()),
            'files': {str(p): raw_digest(p.read_bytes()) for p in paths if p.is_file()}}


class IntegratedInvestigation:
    def __init__(self, directory, provider, jdk, at, *, settings=None, tool_python=None,
                 maximum_actions=100, deadline_seconds=7200):
        self.directory = Path(directory); self.directory.mkdir(parents=True, exist_ok=True)
        self.provider, self.jdk, self.at = provider, Path(jdk), at
        self.settings = settings or AssuranceSettings(investigate_abstractions=True, total_model_calls=30,
            max_derived_comparisons=0, semantic_repair_rounds=1,
            search=Settings(max_model_calls=6, max_rounds=2, scheduler='bfs', reconstruction_required=False,
                            timeout_seconds=180, max_input_bytes=200000, max_output_bytes=200000))
        self.tool_python = Path(tool_python) if tool_python else Path(__file__).parents[4]/'.localresources/assurance-tools/venv/bin/python'
        self.journal = EvidenceJournal(self.directory/'actions', {'case_directory': str(self.directory.resolve())},
            maximum_actions=maximum_actions, deadline_seconds=deadline_seconds)
        self.cache = CachedEvidenceProvider(provider, self.directory/'model-evidence',
            {'at': at, 'settings': self.settings.model_dump()}, maximum_actions=self.settings.total_model_calls,
            deadline_seconds=deadline_seconds)

    def _sidecar(self, kind, request, work):
        request_path = work/'input.json'; output = work/'output.json'
        save(request_path, request)
        argv = [str(self.tool_python), '-m', 'legalmath.interpretation.assurance.sidecar',
                kind, '--input', str(request_path), '--output', str(output)]
        env = {**os.environ, 'CUDA_VISIBLE_DEVICES': '-1',
               'PYTHONPATH': str(Path(__file__).parents[3])}
        with (work/'execution.log').open('w') as log:
            proc = subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, env=env, timeout=600)
        if proc.returncode: raise LegalMathError('E_DEPENDENCY', details='Sidecar failed; see '+str(work/'execution.log'))
        result = json.loads(output.read_text())
        return {'command': argv, 'result': result, 'request_hash': identity(request)}

    def run(self, roots, selected_slice, *, retained=(), authority_registry=None):
        source_binding = [{'url': d['url'], 'media_type': d['media_type'], 'hash': raw_digest(d['data'])}
                          for d in [*roots, *retained]]
        inputs = {'sources': source_binding, 'scope': selected_slice, 'at': self.at,
                  'implementation': implementation_identity(), 'settings': self.settings.model_dump(),
                  'authority_registry': authority_registry.hash if authority_registry else None}
        def inspect_sources(work):
            rows = []
            for i, document in enumerate([*roots, *retained]):
                if document['media_type'] == 'application/pdf':
                    path = work/f'source-{i}.pdf'; path.write_bytes(document['data'])
                    route = self._sidecar('source', {'path': str(path), 'sha256': raw_digest(document['data'])}, work/f'pdf-{i}')
                    rows.append({'source': source_binding[i], **route})
                else:
                    extracted = extract_document(document)
                    rows.append({'source': source_binding[i], 'result': {
                        'status': 'TEXT_SOURCE_EXTRACTED', 'primary_sha256': identity(extracted['text']),
                        'extraction': {k: v for k, v in extracted.items() if k != 'data'},
                        'visual_pdf_route': 'NOT_APPLICABLE_TO_THIS_MEDIA'}})
            return {'sources': rows, 'release_eligible': False}
        source_inputs = {'sources': source_binding, 'processing': source_processing_identity(self.tool_python)}
        source, source_receipt = self.journal.execute('source', source_inputs, inspect_sources,
            issue='source.'+identity(source_inputs))
        def interpret(work):
            provider = CompactProvider(self.cache, work/'transport')
            engine = Assurance(work/'interpretation', provider, self.jdk, self.at, self.settings)
            result = engine.drive(roots, selected_slice, retained=retained, authority_registry=authority_registry)
            if result.get('status') == 'FAILED_INTEGRITY':
                raise LegalMathError('E_INTEGRITY', details={'interpretation_report': str(work/'interpretation/report.json'),
                                                           'failures': result.get('failures', [])})
            return {'report': result, 'directory': str(work/'interpretation')}
        interpreted, interpretation_receipt = self.journal.execute('interpretation', inputs, interpret,
            dependencies=[source_receipt['result_hash']], issue='interpretation.'+identity(inputs),
            retry_if=lambda previous: not previous['report'].get('execution_complete', False))
        directory = Path(interpreted['directory'])
        report = interpreted['report']; candidates_path = directory/'candidates.json'
        candidates = loads(candidates_path.read_bytes()) if candidates_path.exists() else {}
        packet_path = directory/'packet.json'
        packet = loads(packet_path.read_bytes()) if packet_path.exists() else None
        def independent(work):
            checker = Comparisons(work/'java', self.jdk, self.at)
            cases = []; binaries = []; unsupported = []
            for cid, reading in candidates.items():
                try:
                    compiled = bundle(reading, packet, self.at)
                    built = checker.build(compiled)
                    probes = list(snapshots([compiled], self.at, maximum=24))
                    for i, snapshot in enumerate(probes):
                        cases.append({'id': cid+'.'+str(i), 'bundle': compiled, 'snapshot': snapshot,
                            'rule_id': RULE, 'valid_at': self.at, 'known_at': self.at,
                            'jar': built['jar'], 'class_name': built['class_name']})
                    binaries.append({'candidate_id': cid, 'build': built})
                except LegalMathError as exc:
                    unsupported.append({'candidate_id': cid, 'error': exc.code})
            result = self._sidecar('formal-cases', {'cases': cases, 'jdk': str(self.jdk)}, work/'formal')
            criticism = loads((directory/'criticism.json').read_bytes()) if (directory/'criticism.json').exists() else None
            argument = self._sidecar('arguments', {'criticism': criticism}, work/'arguments') if criticism else None
            return {'formal': result, 'arguments': argument, 'binaries': binaries,
                    'unsupported': unsupported, 'release_eligible': False}
        checks, check_receipt = self.journal.execute('independent', {**inputs, 'candidates': identity(candidates)}, independent,
            dependencies=[interpretation_receipt['result_hash']], issue='independent.'+identity(candidates))
        source_issues = [s for s in source['sources'] if s['result'].get('status') in ('UNCERTAINTY_RETAINED', 'UNAVAILABLE')]
        formal_ok = checks['formal']['result']['status'] == 'PASS'
        argument_ok = checks['arguments'] is not None and checks['arguments']['result']['status'] == 'PASS'
        unresolved = list(report.get('findings', []))
        if source_issues: unresolved.append({'kind': 'SOURCE_REGION_UNRESOLVED', 'sources': source_issues})
        if not formal_ok or not argument_ok or checks['unsupported']:
            unresolved.append({'kind': 'INDEPENDENT_CHECK_INCOMPLETE'})
        result = {'status': 'UNCERTAINTY_RETAINED' if unresolved else 'NO_DISCREPANCY_IN_SUPPORTED_PROFILE',
            'execution_complete': report.get('execution_complete', False) and formal_ok and argument_ok,
            'source': source, 'interpretation': interpreted, 'independent': checks,
            'receipts': [source_receipt, interpretation_receipt, check_receipt],
            'residual_questions': unresolved, 'release_eligible': False,
            'legal_correctness_established': False, 'probability_of_legal_correctness': None,
            'model_actions': self.cache.journal.report()['consumed_actions'],
            'evidence_basis': 'Conditional source support and engineering checks; no independent legal adjudication'}
        save(self.directory/'report.json', result)
        return result


def execute_cli(args):
    from .cli import read_documents
    from .authorities import AuthorityCatalog
    from ..search.providers import Allowance, CodexProvider
    path = Path(args.manifest).resolve(); config = loads(path.read_bytes())
    roots, errors = read_documents(config['roots'], path.parent)
    retained, more = read_documents(config.get('retained', []), path.parent)
    if errors or more: raise LegalMathError('E_DEPENDENCY', details=errors+more)
    ledger = loads(Path(args.allowance).read_bytes())
    if args.ceiling > ledger['maximum']: raise LegalMathError('E_RESOURCE_LIMIT')
    provider = CodexProvider(allowance=Allowance(args.allowance, ledger['maximum'], reservation_ceiling=args.ceiling))
    registry = AuthorityCatalog.load(path.parent/config['authority_registry']) if config.get('authority_registry') else None
    return IntegratedInvestigation(args.out, provider, args.jdk, args.at).run(
        roots, config['selected_slice'], retained=retained, authority_registry=registry)
