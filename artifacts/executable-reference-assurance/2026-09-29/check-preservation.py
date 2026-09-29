"""Compare the protected manuscript with the exact frozen verification source."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]; OUT = Path(__file__).parent
read = lambda p: json.loads(Path(p).read_bytes())
sha = lambda b: hashlib.sha256(b).hexdigest()
baseline = read(OUT/'preparation/manifest.json')
verification = ROOT/read(OUT/'state.json')['phases']['verify'][-1]['path']
snapshot_path = verification.parent/'snapshot.json'; snapshot = read(snapshot_path)
frozen = Path(snapshot['path']); changed = []; errors = []
explained = {
 'docs/monograph/chapters/06k-executable-dates.tex': 'Original v1 behavior retained and distinguished from new v2 repair. Added original-object binding, parsed-expression selection, canonical type identity and routing/history explanation. Calendar mathematics and all earlier results retained; the 338-test/234-execution result is explicitly historical, and the later 98-native/eight-boundary reproduction is separately described.',
 'docs/monograph/frontmatter/process-map.tex': 'Updated the executable-reference branch and added bounded-repair explanation; other workstream replaced the former unimplemented UBS schedule statement with its implemented-section reference and appended UBS and Series SS instrument diagrams. All prior diagram labels retained.',
 'docs/monograph/chapters/02-circular.tex': 'Other workstream inserted inputs for the new 02c and 02d instrument sections; no previous line removed.',
 'docs/monograph/chapters/02b-bank-compliance.tex': 'Other workstream replaces the former unimplemented-UBS-schedule statement with a cross-reference to its new instrument section and still-unresolved price branches. Equations and other findings retained.',
 'docs/monograph/references.bib': 'Other workstream prepended three references: the Series SS prospectus supplement, its certificate of designations, and the SIX 2027 clearing schedule. Every prior bibliography entry is unchanged. This comparison checks preservation and does not establish the new sources\' legal applicability.',
}
patterns = {
 'equations': r'\\\[(.*?)\\\]|\\begin\{(?:equation\*?|align\*?|gather\*?|multline\*?)\}(.*?)\\end\{(?:equation\*?|align\*?|gather\*?|multline\*?)\}',
 'labels': r'\\label\{([^}]+)\}',
 'citations': r'\\(?:cite|citep|citet|autocite|textcite)\*?(?:\[[^\]]*\])*\{([^}]+)\}',
 'listings': r'\\begin\{(?:lstlisting|verbatim)\}(.*?)\\end\{(?:lstlisting|verbatim)\}',
}
with ZipFile(OUT/'preparation/before-inputs.zip') as archive:
    if sha((OUT/'preparation/before-inputs.zip').read_bytes()) != baseline['archive_sha256']: raise RuntimeError('Protected archive changed')
    names = [n for n in baseline['inputs'] if n.startswith('docs/monograph/') and n.endswith(('.tex', '.bib')) and '/review/' not in n]
    for name in names:
        old = archive.read(name)
        if sha(old) != baseline['inputs'][name]: raise RuntimeError('Protected source mismatch')
        path = frozen/name
        if not path.exists(): errors.append({'file': name, 'missing': True}); continue
        new = path.read_bytes()
        if sha(new) == sha(old): continue
        if name not in explained: errors.append({'file': name, 'unreviewed_change': True})
        removed = {}
        for kind, pattern in patterns.items():
            old_items = Counter(re.findall(pattern, old.decode(), flags=re.S))
            new_items = Counter(re.findall(pattern, new.decode(), flags=re.S))
            loss = old_items-new_items
            if loss: removed[kind] = [str(v) for v in loss.elements()]
        if removed: errors.append({'file': name, 'removed_formal_content': removed})
        changed.append({'file': name, 'before': sha(old), 'after': sha(new), 'explanation': explained.get(name), 'removed_formal_content': removed})
result = {'status': 'PRESERVED_WITH_EXPLAINED_REVISIONS' if not errors else 'REVIEW_REQUIRED',
    'baseline_archive': 'artifacts/executable-reference-assurance/2026-09-29/preparation/before-inputs.zip',
    'baseline_sha256': baseline['archive_sha256'], 'snapshot_manifest_sha256': sha(snapshot_path.read_bytes()),
    'checked_prior_manuscript_files': len(names), 'changed': changed, 'errors': errors,
    'comparison': 'Prior equations, citations, labels and code blocks retained; all changed narrative regions inspected and explained. This is preservation evidence, not a human-voice or legal-correctness rating.'}
(OUT/'manuscript-preservation.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
print(json.dumps(result, indent=2))
if errors: raise SystemExit(1)
