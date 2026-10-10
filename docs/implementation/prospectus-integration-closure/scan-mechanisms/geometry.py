"""Compare two explicit supplied-region rules on unchanged original OCR words."""
import sys

from common import ROOT, SCAN, start, finish, read, save


def project(target, graph, page, oracle, *, intersection):
    x0, y0, x1, y1 = target['region']
    width, height = page['image_width'] * 72 / 300, page['image_height'] * 72 / 300
    sources, words = [], []
    for unit in graph['units']:
        if unit['page'] != target['page']:
            continue
        runs = []
        for word in unit.get('words', []):
            left, top, right, bottom = word['bbox']
            left, right = [x / width * oracle['images']['width'] for x in (left, right)]
            top, bottom = [y / height * oracle['images']['height'] for y in (top, bottom)]
            inside = (min(right, x1) > max(left, x0) and min(bottom, y1) > max(top, y0)) if intersection else (
                x0 <= (left + right) / 2 < x1 and y0 <= (top + bottom) / 2 < y1)
            if not inside:
                continue
            a, b = word['start'], word['end']
            if unit['raw'][a:b] != word['text']:
                raise ValueError('Original word changed')
            if runs and a == runs[-1][1] + 1 and unit['raw'][runs[-1][1]:a] == ' ':
                runs[-1][1] = b
            else:
                runs.append([a, b])
            words.append({'unit': unit['id'], 'start': a, 'end': b, 'raw': word['text'],
                          'original_bbox': word['bbox'], 'review_image_box': [left, top, right, bottom]})
        for a, b in runs:
            sources.append({'unit': unit['id'], 'document': unit['document'], 'source_sha256': unit['source_sha256'],
                            'start': a, 'end': b, 'quote': unit['raw'][a:b]})
    text = ' '.join(s['quote'] for s in sources)
    return {'text': text, 'exact': ' '.join(text.split()) == ' '.join(target['text'].split()),
            'sources': sources, 'words': words}


def main():
    if len(sys.argv) != 1:
        raise ValueError('Use the exact diagnostic command')
    folder, frozen, tick, oracle, raw = start('geometry',
        ['timeout', '60', '.venv/bin/python', str(__file__).removeprefix(str(ROOT) + '/')])
    try:
        original = read(SCAN / 'analysis/attempt-001/critical-occurrences.json')
        graph = read(SCAN / 'baseline/attempt-001/service-report.json')['source_map']
        rows = []
        if [r['id'] for r in original] != [t['id'] for t in oracle['targets']]:
            raise ValueError('Critical denominator/order changed')
        for target, prior in zip(oracle['targets'], original):
            page = raw['pages'][target['page'] - 1]
            centre = project(target, graph, page, oracle, intersection=False)
            overlap = project(target, graph, page, oracle, intersection=True)
            if (centre['text'] != prior['supplied_region_text'] or centre['exact'] != prior['supplied_region_exact'] or
                    centre['sources'] != prior['raw_sources']):
                raise ValueError('Baseline centre rule does not reproduce: ' + target['id'])
            keys = lambda records: {(r['unit'], r['start'], r['end']) for r in records}
            centre_keys, overlap_keys = keys(centre['words']), keys(overlap['words'])
            rows.append({'id': target['id'], 'page': target['page'], 'expected': target['text'],
                'centre': centre, 'intersection': overlap,
                'added_words': [w for w in overlap['words'] if (w['unit'], w['start'], w['end']) not in centre_keys],
                'removed_words': [w for w in centre['words'] if (w['unit'], w['start'], w['end']) not in overlap_keys]})
        save(folder / 'comparisons.json', rows)
        if len(rows) != 23 or sum(r['centre']['exact'] for r in rows) != 16:
            raise ValueError('Reviewed baseline changed')
        lost = [r['id'] for r in rows if r['centre']['exact'] and not r['intersection']['exact']]
        gained = [r['id'] for r in rows if not r['centre']['exact'] and r['intersection']['exact']]
        result = {'status': 'PASS', 'target_denominator': len(rows), 'centre_exact': 16,
            'intersection_exact': sum(r['intersection']['exact'] for r in rows),
            'lost_passing_targets': lost, 'gained_exact_targets': gained,
            'changed_selections': [r['id'] for r in rows if r['added_words'] or r['removed_words']],
            'candidate_screen': 'PASS' if not lost else 'FAIL',
            'all_critical_text': 'PASS' if all(r['intersection']['exact'] for r in rows) else 'FAIL',
            'scope': 'Supplied-region geometry diagnostic; no OCR call or semantic adoption'}
    except Exception as exc:
        result = {'status': 'FAIL', 'error': type(exc).__name__ + ': ' + str(exc)}
    finish(folder, frozen, tick, result)


if __name__ == '__main__':
    main()
