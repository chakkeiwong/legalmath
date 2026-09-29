"""Place authored teaching diagrams beside their source-unit discussion.

The TSV is the authored concept/example map, not generated semantic judgments.
Insertions are reversible and hash registered. No baseline paragraph is removed.
"""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / 'docs/monograph'
TEACH = BOOK / 'teaching'
REG = BOOK / 'review/revision/text-edits.json'


def escape(text):
    return ''.join({'&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#',
                    '_': r'\_', '^': r'\textasciicircum{}', '~': r'\textasciitilde{}'}.get(c, c) for c in text)


def main():
    data = json.loads(REG.read_text())
    mapping = []
    chapters = {p: p.read_text() for p in (BOOK/'chapters').glob('*.tex')}
    for line in (TEACH/'teaching.tsv').read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        unit, shape, a, b, c, caption, example = line.split('|')
        ident = 'teach-' + re.sub(r'[^A-Za-z0-9-]', '-', unit)
        matches = [(p, m) for p, raw in chapters.items() for m in re.finditer(
            r'% BEGIN SOURCE UNIT '+re.escape(unit)+r'\n(.*?)% END SOURCE UNIT '+re.escape(unit)+r'\n', raw, re.S)]
        assert len(matches) == 1, (unit, len(matches))
        path, match = matches[0]
        fields = [escape(s) for s in (a,b,c,caption,example)]
        figure = '\\begin{figure}[H]\n\\centering\n\\Teaching'+shape+'{'+fields[0]+'}{'+fields[1]+'}{'+fields[2]+'}\n'
        figure += '\\caption{'+fields[3]+'}\\label{fig:'+ident+'}\n\\end{figure}\n'
        if example:
            figure += '\n'+fields[4]+'\n\n'
        target = TEACH / (ident+'.tex')
        target.write_text(figure)
        insertion = '\\input{\\LegalMathRoot teaching/'+ident+'}\n'
        registered = '% BEGIN REVISION ADDITION '+ident+'\n'+insertion+'% END REVISION ADDITION '+ident+'\n'
        if ident not in data['additions']:
            body = match[1]
            # A paragraph boundary outside every environment is a safe insertion.
            boundaries=[]
            depth=0
            for event in re.finditer(r'\\begin\{[^}]+\}|\\end\{[^}]+\}|\n\n', body):
                if event[0].startswith('\\begin'):
                    depth += 1
                elif event[0].startswith('\\end'):
                    depth -= 1
                elif depth == 0 and len(body[:event.end()].split()) >= 90:
                    boundaries.append(event.end())
            if not boundaries:
                boundaries = [len(body)]
            pos = min(boundaries, key=lambda p: abs(p-len(body)*0.48))
            raw = chapters[path]
            at = match.start(1)+pos
            chapters[path] = raw[:at]+registered+raw[at:]
            data['additions'][ident] = {'path': str(path.relative_to(ROOT)),
                'sha256': hashlib.sha256(insertion.encode()).hexdigest(),
                'reason': caption, 'source_unit': unit, 'content_file': str(target.relative_to(ROOT))}
        mapping.append({'unit': unit, 'figure': 'fig:'+ident, 'diagram_type': shape,
            'teaching_point': caption, 'added_example': example or None,
            'file': str(target.relative_to(ROOT)), 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
            'review_status': 'authored_requires_rendered_review'})
    for p, raw in chapters.items():
        if p.read_text() != raw:
            p.write_text(raw)
    REG.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n')
    (BOOK/'review/revision/concept-teaching-map.json').write_text(json.dumps(mapping, indent=2, ensure_ascii=False)+'\n')
    print(f'Placed {len(mapping)} authored diagrams.')


if __name__ == '__main__':
    main()
