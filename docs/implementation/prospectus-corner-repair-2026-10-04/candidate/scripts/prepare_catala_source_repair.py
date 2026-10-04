#!/usr/bin/env python3
"""Retain omitted context without rewriting the frozen development study."""
from copy import deepcopy
from pathlib import Path
from legalmath.canonical import canonical, digest, loads
from legalmath.catala.native.source_review import validate_packet
from legalmath.sources.anchors import make_span

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'artifacts/catala/gap-closure/source-review'
OUT = ROOT / 'artifacts/catala/gap-closure/source-review-successor'


def repair(packet, blobs):
    successor = deepcopy(packet)
    successor['repair_of'] = digest(packet)
    successor['repair_findings'] = [
        'Include footnotes omitted from selected excerpts; external authorities remain unreviewed.',
        'Material changes must concern tokenised SFC-authorised investment products.',
        'Source dates and evidence timestamps do not establish legal commencement dates.']
    for row in successor['corpus']:
        task = row['task']; name = task['task_id'].split('.')[-1]
        if name == 'netassets':
            continue
        unit = task['packet']['units'][0]; span = unit['span']
        text = blobs[span['text_sha256']].decode(); raw = blobs[span['raw_sha256']]
        number = {'gifts': '3', 'network': '4', 'consultation': '8'}[name]
        line = next(line for line in text.splitlines() if line.startswith(number) and line[1].isspace())
        start = text.index(line)
        footnote = {'unit_id': 'footnote.' + number, 'locator': span['source_id'] + ' footnote ' + number,
                    'text': line, 'normative': True,
                    'span': make_span('span.' + name + '.footnote', span['source_id'], raw, text, start, start + len(line))}
        task['packet']['units'].append(footnote)
        task['packet']['selected_slice'] += '\n\n' + line
        task['question'] += (' Included footnotes must receive an explicit interpretation. '
                             'Cross-referenced authorities have not been reviewed; abstain if they '
                             'are needed to determine this selected control. Assessment timestamps '
                             'do not assert a legal commencement date.')
        if name == 'consultation':
            field = next(f for f in task['inputs'] if f['name'] == 'materialchange')
            field['meaning'] = ('The proposal makes a material change to the tokenisation '
                                'arrangements of a tokenised SFC-authorised investment product')
            row['selected_reading'] = ('Consultation applies to a new tokenised product seeking '
                                       'authorisation, tokenisation of an existing SFC-authorised '
                                       'product, or a material change to a tokenised SFC-authorised '
                                       'product arrangement.')
            row['scope_qualifications'] = task['question']
        row['adjudication'] = {'status': 'PENDING_HUMAN', 'reviewer': None}
    return successor


def main():
    packet = loads((SOURCE / 'packet.json').read_bytes())
    blobs = {p.stem: p.read_bytes() for p in (SOURCE / 'sources').glob('*.bin')}
    successor = repair(packet, blobs)
    report = validate_packet(successor, list(blobs.values()))
    OUT.mkdir(parents=True, exist_ok=False)
    (OUT / 'sources').mkdir()
    for h, value in blobs.items():
        (OUT / 'sources' / (h + '.bin')).write_bytes(value)
    (OUT / 'packet.json').write_bytes(canonical(successor))
    (OUT / 'validation.json').write_bytes(canonical(report))
    (OUT / 'review.md').write_text(
        '# Successor source review packet\n\n'
        'The original four-task study is unchanged. This successor includes the '
        'three omitted footnotes and repairs the material-change classification. '
        'Its Boolean reference rows retain their values under the narrower input '
        'meaning; they are provisional examples, not legally adjudicated answers. '
        'The referred-to FAQ and Tokenised Securities Circular provisions still '
        'require source review before a complete legal conclusion.\n\n'
        'Independent reviewers should assess each packet.json task, footnote, '
        'classification, rival reading and witness against the retained source '
        'bytes, record any missing authority, and sign a reference-hash attestation '
        'only after resolving those issues. Prior exposure excludes this corpus '
        'from a heldout evaluation.\n')
    print(canonical(report).decode())


if __name__ == '__main__':
    main()
