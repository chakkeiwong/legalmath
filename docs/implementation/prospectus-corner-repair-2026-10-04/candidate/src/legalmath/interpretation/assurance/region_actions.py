"""Bounded, evidenced recovery actions shared by live and retained PDF work."""
from pathlib import Path

from ...canonical import raw_digest
from .workflow import EvidenceJournal
from .regions import choose_region_action
from .diversity import identity


def investigate(regions, raster, layout, directory, ocr, *, maximum_actions=3):
    from PIL import Image
    raster = Path(raster)
    if raw_digest(raster.read_bytes()) != regions['raster_sha256']:
        raise ValueError('Page raster changed')
    journal = EvidenceJournal(directory, {'regions': identity(regions)},
                              maximum_actions=maximum_actions, maximum_per_issue=3)
    issue = next((i for i in regions['issues'] if i['kind'] != 'TEXT_OR_ORDER'),
                 regions['issues'][0] if regions['issues'] else None)
    attempted, evidence = [], []
    if issue:
        for _ in range(maximum_actions):
            action = choose_region_action(issue, attempted)
            if action is None:
                break
            attempted.append(action)

            def perform(work, action=action):
                if action == 'COMPARE_OFFICIAL_TEXT':
                    return {'status': 'NO_DISTINCT_OFFICIAL_TEXT_AVAILABLE',
                            'question': 'Only this retained PDF is available; parser votes cannot settle the text.'}
                with Image.open(raster) as image:
                    tokens = issue['change']['left_tokens']
                    hits = [w for w in layout['words'] if w['text'] in tokens]
                    box = ([max(0, min(w['x0'] for w in hits)-8),
                            max(0, min(w['top'] for w in hits)-8),
                            min(layout['width'], max(w['x1'] for w in hits)+8),
                            min(layout['height'], max(w['bottom'] for w in hits)+8)]
                           if hits else [0, 0, layout['width'], layout['height']])
                    sx, sy = image.width/layout['width'], image.height/layout['height']
                    crop = work/'region.png'
                    image.crop((int(box[0]*sx), int(box[1]*sy), int(box[2]*sx), int(box[3]*sy))).save(crop)
                result = {'bbox': box, 'sha256': raw_digest(crop.read_bytes()),
                          'semantic_resolution': False,
                          'matching': 'Token-located enclosing region; layout relation remains unverified'}
                if action == 'INSPECT_REGION':
                    return {**result, 'status': 'LOCATED_FOR_INSPECTION'}
                return {**result, 'status': 'NEW_OCR_EVIDENCE',
                        'ocr': ocr(crop, work/'regional-ocr', 6), 'shared_engine': 'Tesseract'}

            result, receipt = journal.execute('evidence.'+action.lower().replace('_', '-'),
                {'issue': issue, 'action': action}, perform, issue='page')
            evidence.append({'action': action, 'result': result, 'receipt': receipt})
    return {'actions': evidence, 'target_issue': issue,
            'remaining_issues': regions['issues'], 'resolution_established': False,
            'limit': maximum_actions, 'release_eligible': False}
