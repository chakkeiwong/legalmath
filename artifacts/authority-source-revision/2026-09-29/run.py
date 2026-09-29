"""Attach retained official bytes without closing any legal question or issue."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]; OUT = Path(__file__).parent
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
rel = lambda p: str(Path(p).relative_to(ROOT))
def save(p, value):
    p.parent.mkdir(parents=True, exist_ok=True); p.write_text(json.dumps(value, indent=2, sort_keys=True)+'\n')


def main():
    work = OUT/'attempt-01'; work.mkdir(exist_ok=False); started = time.monotonic()
    os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
    snapshot_path = ROOT/'artifacts/executable-reference-assurance/2026-09-29/verify/attempt-01/snapshot.json'
    snapshot = read(snapshot_path); frozen = Path(snapshot['path'])
    sys.path[:0] = [str(frozen/'src'), str(frozen)]
    from legalmath.canonical import digest
    from legalmath.interpretation.assurance.sources import acquire_context, packet_from_context, audit_packet
    from legalmath.interpretation.assurance.grants import GrantedAllowance
    def frozen_check():
        if any(sha(frozen/p) != h for p, h in snapshot['inputs'].items()): raise RuntimeError('Changed frozen implementation')
    frozen_check()
    oldroot = ROOT/'artifacts/assurance-successor/2026-09-28/live-backlog/authority'
    files = {rel(p): sha(p) for p in oldroot.rglob('*') if p.is_file()}
    grant = GrantedAllowance(ROOT/'artifacts/assurance-successor/2026-09-28/grant.json').verify()
    manifest = {'status': 'RUNNING', 'plan': 'docs/plans/authority-source-revision.md',
        'plan_sha256': sha(ROOT/'docs/plans/authority-source-revision.md'), 'script_sha256': sha(__file__),
        'command': [sys.executable, *sys.argv], 'environment': sys.executable, 'snapshot': str(frozen),
        'snapshot_manifest_sha256': sha(snapshot_path), 'git_commit': snapshot['commit'],
        'cpu_gpu': 'CPU only; CUDA_VISIBLE_DEVICES=-1', 'seeds': 'N/A: deterministic retained-byte attachment',
        'live_calls': 0, 'downloads': 0, 'grant': grant}
    save(work/'manifest.json', manifest)
    try:
        prior = read(ROOT/'artifacts/interpretation/round15/execution/action-0005/authority-gap-register.json')
        inherited = read(ROOT/'artifacts/assurance-continuation/2026-09-29/final-report.json')['authority_questions']
        refs = [read(ROOT/'artifacts/interpretation/round14/sources-official/23ec52.json.receipt.json'),
            read(ROOT/'artifacts/interpretation/round15/execution/action-0005/sources/23ec52-appendix.pdf.receipt.json')]
        roots = []; acquired = []
        for ref, media in zip(refs, ('application/json', 'application/pdf')):
            original = ROOT/ref['path']
            if sha(original) != ref['sha256']: raise RuntimeError('Changed original source bytes')
            destination = work/'sources'/original.name; destination.parent.mkdir(exist_ok=True)
            destination.write_bytes(original.read_bytes())
            roots.append({'url': ref['url'], 'media_type': media, 'data': destination.read_bytes()})
            acquired.append({'path': rel(destination), 'sha256': sha(destination), 'original_receipt': ref,
                'edition_identity': 'EXACT_ARCHIVED_BYTES', 'currentness': 'NOT_ESTABLISHED', 'applicability': 'UNASSESSED'})
        context = acquire_context(roots, max_documents=2, max_depth=0,
            fetcher=lambda _: (_ for _ in ()).throw(RuntimeError('Network prohibited in this offline revision')))
        if len(context['documents']) != 2: raise RuntimeError('Main circular or appendix missing')
        packet = packet_from_context(context, 'Original 23EC52 authority question; full main circular and appendix, with applicability unresolved')
        if audit_packet(packet, context): raise RuntimeError('Extracted source characters lost')
        # Raw bytes have their own archived identities; JSON context retains both
        # extractions and every unresolved reference/visual finding.
        serial = {**context, 'documents': [{k:v for k,v in d.items() if k != 'data'} for d in context['documents']]}
        save(work/'context.json', serial); save(work/'packet.json', packet)
        register = []
        for question in inherited:
            historical = next(q for q in prior['register'] if q['id'] == question['id'])
            sources = []
            for ref in historical['related_official_files']:
                if sha(ROOT/ref['path']) != ref['sha256']: raise RuntimeError('Retained authority changed')
                receipt = ROOT/(ref['path']+'.receipt.json')
                sources.append({**ref, 'acquisition_receipt': read(receipt) if receipt.is_file() else None,
                    'availability': 'ARCHIVED_BYTES_VERIFIED', 'question_relevance': 'UNASSESSED',
                    'currentness': 'NOT_ESTABLISHED', 'applicable_edition': 'NOT_ESTABLISHED'})
            row = {'question': question, 'status': 'NOT_ESTABLISHED', 'archived_sources': sources,
                'prior_evidence': {p:h for p,h in files.items() if '/'+question['id']+'/' in p},
                'original_issue_history_reset': False, 'new_model_calls': 0}
            if question['id'] == '23ec52-appendix':
                row.update(new_source_revision={'packet_hash': digest(packet), 'sources': acquired},
                    source_availability='MAIN_AND_APPENDIX_ATTACHED',
                    dependent_semantic_checks='REASSESSMENT_REQUIRED',
                    incorporated_legislation='EDITION_AND_APPLICABILITY_NOT_ESTABLISHED')
            if question['id'] == 'xml-schema': row['actual_schema_bytes_and_version'] = 'MISSING'
            register.append(row)
        if len(register) != 6 or {r['question']['id'] for r in register} != {q['id'] for q in inherited}:
            raise RuntimeError('Question denominator changed')
        if any(sha(ROOT/p) != h for p,h in files.items()): raise RuntimeError('Historical authority evidence changed')
        if GrantedAllowance(ROOT/'artifacts/assurance-successor/2026-09-28/grant.json').verify() != grant:
            raise RuntimeError('Grant changed')
        frozen_check()
        result = {'status': 'SOURCE_ATTACHED_LEGAL_QUESTIONS_REMAIN', 'packet_hash': digest(packet),
            'documents': 2, 'units': len(packet['units']), 'questions': register,
            'extraction_findings': context['findings'], 'semantic_reference_completeness': False,
            'old_model_judgments_reused': False, 'original_history_unchanged': True, 'live_calls': 0,
            'legal_correctness': 'NOT_ESTABLISHED', 'eDDA_authentication_inventories': 'INCOMPLETE',
            'required_next_processing': 'Eligible original-issue continuation with official missing sources and explicit live authorization'}
        save(work/'result.json', result); save(work/'historical-files.json', files)
        manifest['status'] = 'PASSED'
    except BaseException as exc: manifest.update(status='FAILED', error=type(exc).__name__, details=str(exc))
    manifest['wall_seconds'] = round(time.monotonic()-started, 3)
    manifest['outputs'] = {rel(p): sha(p) for p in work.rglob('*') if p.is_file() and p.name != 'manifest.json'}
    save(work/'manifest.json', manifest)
    save(OUT/'next-phase-plan.json', {'status': manifest['status'], 'D4': 'SOURCE_REVISION_ONLY; LEGAL_QUESTIONS_OPEN',
        'D5': 'NO_REMAINING_LIVE_AUTHORIZATION', 'D6': 'NO_FUTURE_OBSERVATIONS', 'live_calls': 0})
    print(json.dumps({'status': manifest['status'], 'manifest': rel(work/'manifest.json'), 'details': manifest.get('details')}))
    if manifest['status'] != 'PASSED': raise SystemExit(1)


if __name__ == '__main__': main()
