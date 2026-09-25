"""Check inclusion, explicit editorial deltas and identities of the unified book.

This validates preservation evidence, not legal truth or reader comprehension.
Run after building the canonical PDF and synchronizing the proposal PDF alias.
"""
from collections import Counter
from pathlib import Path
import hashlib
import json
import re
import fitz
from monograph_revision_support import restore_revision

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / '.localresources/unification/baseline'
BOOK = ROOT / 'docs/monograph'
REVIEW = BOOK / 'review/unification'
HEADING = re.compile(r'^\\(section|subsection|subsubsection)(?:\[[^\]]*\])?\{([^\n]+)\}', re.M)
INPUT = re.compile(r'\\(?:input|include)\{(?:\\LegalMathRoot\s*)?([^}]+)\}')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def citations(text):
    return {key.strip() for group in re.findall(
        r'\\cite\w*\*?(?:\[[^\]]*\])*\{([^}]+)\}', text)
        for key in group.split(',')}


def expand(path):
    return INPUT.sub(lambda m: expand(BOOK / (m[1] + '.tex')), path.read_text())


def retained_features(text, environment):
    return Counter(re.sub(r'\s+', ' ', value).strip() for value in re.findall(
        r'\\begin\{' + environment + r'\}(.*?)\\end\{' + environment + r'\}',
        text, re.S))


def main():
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    frozen = json.loads((BASE / 'manifest.json').read_text())
    for name, record in frozen['files'].items():
        require(sha(BASE / name) == record['sha256'], 'Changed protected baseline: ' + name)
    record = json.loads((REVIEW / 'source-retention.json').read_text())
    units = record['source_units']
    ids = [u['id'] for u in units]
    require(len(ids) == len(set(ids)), 'Duplicate preservation unit')
    expected = set()
    for folder, group in [('docs/proposal', 'P'), ('docs/monograph/chapters', 'M')]:
        for path in sorted((BASE / folder).glob('*.tex')):
            if path.name == 'proposal.tex':
                continue
            pattern = HEADING if group == 'P' else re.compile(r'^\\section\{[^\n]+\}', re.M)
            count = max(1, len(list(pattern.finditer(path.read_text()))))
            prefix = 'P-' + path.stem if group == 'P' else 'M' + path.name[:2]
            expected.update(f'{prefix}:{i:02}' for i in range(count))
    require(set(ids) == expected, 'Missing or unexpected source units')
    aux = (BOOK / 'monograph.aux').read_text()
    label_pages = {key: page for key, page in re.findall(
        r'\\newlabel\{(merge:[^}]+)\}\{\{[^}]*\}\{([^}]+)\}', aux)}
    report_units = []
    for unit in units:
        path = BASE / unit['source']
        lines = path.read_text().splitlines(keepends=True)
        raw = ''.join(lines[unit['source_start_line'] - 1:unit['source_end_line'] - 1])
        require(digest(raw) == unit['source_sha256'], 'Baseline unit identity: ' + unit['id'])
        body = re.sub(r'^\\input\{[^}]+\}\s*$', '', raw, flags=re.M)
        for edit in unit['editorial_updates']:
            require(edit['old'] in body, 'Unapplicable editorial update: ' + unit['id'])
            require(bool(edit['reason'].strip()), 'Unexplained update: ' + unit['id'])
            body = body.replace(edit['old'], edit['new'], 1)
        heading = HEADING.match(body)
        if unit['heading_level']:
            body = ('\\' + unit['heading_level'] + '{' +
                    (unit['heading_title'] or unit['title']) + '}' +
                    (body[heading.end():] if heading else '\n\n' + body))
        heading = HEADING.match(body)
        at = heading.end() if heading else 0
        body = body[:at] + '\n\\label{' + unit['destination_label'] + '}\n' + body[at:]
        if unit['added_bridge']:
            heading = HEADING.match(body)
            at = heading.end() if heading else 0
            body = body[:at] + '\n\n' + unit['added_bridge'] + body[at:]
        body = body.strip() + '\n'
        destination = restore_revision((ROOT / unit['destination']).read_text(), ROOT / unit['destination'])
        marker = re.search(r'% BEGIN SOURCE UNIT ' + re.escape(unit['id']) +
                           r'\n(.*?)% END SOURCE UNIT ' + re.escape(unit['id']) + r'\n',
                           destination, re.S)
        require(marker is not None, 'Missing destination block: ' + unit['id'])
        require(digest(body) == unit['destination_sha256'], 'Unexplained stored delta: ' + unit['id'])
        if marker:
            require(marker[1] == body, 'Actual destination differs from recorded transformation: ' + unit['id'])
        require(unit['destination_label'] in label_pages, 'No built destination page: ' + unit['id'])
        report_units.append({
            'id': unit['id'], 'source': unit['source'], 'title': unit['title'],
            'destination_chapter': unit['destination_chapter'],
            'printed_page': label_pages.get(unit['destination_label']),
            'explicit_updates': len(unit['editorial_updates']),
            'exact_transformation_matched': marker is not None and marker[1] == body,
        })

    old_text = '\n'.join((BASE / u['source']).read_text() for u in
                         {u['source']:u for u in units}.values())
    full = expand(BOOK / 'monograph.tex')
    missing_citations = sorted(citations(old_text) - citations(full))
    require(not missing_citations, 'A cited source disappeared')
    old_labels = set(re.findall(r'\\label\{([^}]+)\}', old_text))
    final_labels = set(re.findall(r'\\label\{([^}]+)\}', full))
    require(old_labels <= final_labels, 'Original equation/figure/table/section labels were lost')
    # Equations and program listings are mechanically preserved. Table wording
    # may have explicit status/API corrections already checked at unit level.
    feature_results = {}
    for env in ['equation', 'lstlisting', 'figure']:
        old = retained_features(old_text, env)
        current = retained_features(full, env)
        missing = old - current
        require(not missing, 'Changed or missing original ' + env)
        feature_results[env] = {'original': sum(old.values()), 'unified': sum(current.values()),
                                'missing_original': sum(missing.values())}
    pdf = fitz.open(BOOK / 'monograph.pdf')
    proposal_pdf = ROOT / 'docs/proposal/proposal.pdf'
    require(sha(proposal_pdf) == sha(BOOK / 'monograph.pdf'), 'Proposal PDF is not the unified PDF')
    wrapper = (ROOT / 'docs/proposal/proposal.tex').read_text()
    require('\\input{../monograph/monograph.tex}' in wrapper, 'Proposal source is not a canonical entry point')
    require(len(re.findall(r'\\chapter(?:\[[^\]]*\])?\{', full)) == 10, 'Expected ten substantive chapters')
    require(full.count('\\bibliography{') == 1, 'Expected one bibliography')
    require(full.count('\\begin{titlepage}') == 1, 'Expected one title page')
    require(len(pdf) >= 153, 'Page count suggests truncation; inspect inclusion')

    accepted = json.loads((ROOT / 'artifacts/runs/acceptance/run-manifest.json').read_text())
    repair = json.loads((ROOT / 'artifacts/runs/acceptance/final-artifacts.json').read_text())['browser_harness_repair']
    runtime = dict(accepted['input_sha256'])
    # E01–E09 was accepted after the original T00–T22 snapshot. Use that
    # immutable acceptance for the four runtime files it deliberately extended.
    extension_path = ROOT / 'artifacts/interpretation/round1/P4/attempt-03/run-manifest.json'
    require(sha(extension_path) == '57db782787f9bf6e45ba643dcc6e35b9d064021455b6aa86dbd8f36119c17ef4',
            'Interpretation acceptance manifest identity changed')
    extension = json.loads(extension_path.read_text())
    require(extension['status'] == 'PASSED', 'Interpretation acceptance did not pass')
    extended_paths = {'src/legalmath/api/app.py', 'src/legalmath/review/lifecycle.py',
                      'src/legalmath/review/releases.py', 'src/legalmath/storage/archive.py'}
    concurrent_path = ROOT / 'docs/monograph/review/revision/concurrent-runtime-change.json'
    concurrent = json.loads(concurrent_path.read_text()) if concurrent_path.exists() else None
    concurrent_api_path = ROOT / 'docs/monograph/review/revision/concurrent-api-change.json'
    concurrent_api = json.loads(concurrent_api_path.read_text()) if concurrent_api_path.exists() else None
    for path, value in runtime.items():
        expected_hash = repair['after_sha256'] if value == repair['before_sha256'] else value
        if path in extended_paths:
            expected_hash = extension['input_sha256'][path]
        current_hash = sha(ROOT / path)
        if concurrent_api and path == concurrent_api['path'] and current_hash != expected_hash:
            require(current_hash == concurrent_api['current_sha256'], 'Concurrent API changed beyond reviewed diff')
        elif concurrent and path == concurrent['path'] and current_hash != expected_hash:
            require(current_hash == concurrent['after_sha256'], 'Concurrent CLI changed beyond reviewed diff')
            restored = (ROOT / path).read_text()
            for edit in concurrent['inverse_edits']:
                require(restored.count(edit['old']) == 1, 'Concurrent CLI inverse edit is ambiguous')
                restored = restored.replace(edit['old'], edit['new'], 1)
            require(hashlib.sha256(restored.encode()).hexdigest() == expected_hash,
                    'Concurrent CLI change did not preserve accepted commands')
        else:
            require(current_hash == expected_hash, 'Accepted runtime input changed: ' + path)

    chapter_pages = [(title, page) for level, title, page in pdf.get_toc()
                     if level == 1 and title != 'The decision this book supports']
    with fitz.open(BASE / 'docs/proposal/proposal.pdf') as original:
        original_proposal_pages = len(original)
    with fitz.open(BASE / 'docs/monograph/monograph.pdf') as original:
        original_monograph_pages = len(original)
    original_total = original_proposal_pages + original_monograph_pages
    result = {
        'status': 'PASSED' if not errors else 'FAILED', 'errors': errors,
        'page_comparison': {'original_proposal': original_proposal_pages,
                            'original_monograph': original_monograph_pages,
                            'original_total': original_total, 'unified': len(pdf),
                            'change_from_original_total': len(pdf)-original_total,
                            'interpretation': 'Different original typography and shared front matter; source-unit checks establish inclusion, not page arithmetic.'},
        'chapter_starts_pdf': chapter_pages, 'chapters': 10,
        'proposal_units': len([i for i in ids if i.startswith('P-')]),
        'monograph_sections': len([i for i in ids if i.startswith('M')]),
        'total_retained_units': len(units), 'unmapped_units': sorted(expected-set(ids)),
        'source_unit_locations': report_units,
        'original_cited_entries': len(citations(old_text)),
        'unified_cited_entries': len(citations(full)),
        'missing_original_citations': missing_citations,
        'original_labels_retained': len(old_labels), 'features': feature_results,
        'protected_runtime_inputs': len(runtime), 'application_tests_rerun': False,
        'canonical_tex_sha256': sha(BOOK/'monograph.tex'),
        'canonical_pdf_sha256': sha(BOOK/'monograph.pdf'),
        'proposal_pdf_identical': sha(proposal_pdf)==sha(BOOK/'monograph.pdf'),
        'independent_reader_acceptance':'PENDING',
        'limits':['Exact mapped transformations establish inclusion and explicit changes, not legal validity or prose quality.',
                  'Duplicate front matter is consolidated and recorded separately; original documents remain frozen.',
                  'No full application, live-model or legal-adjudication study was run for this merge.'],
    }
    (REVIEW/'preservation-check.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','page_comparison','total_retained_units',
                                          'unified_cited_entries','features','errors']}, indent=2))
    if errors:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
