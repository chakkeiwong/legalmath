"""Sealed native inventory and original-page renders; no OCR or language truth."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
import base64
import hashlib
import json
from pathlib import Path
import sys
import fitz


def sha(data):
    return hashlib.sha256(data).hexdigest()


def binary(value):
    if isinstance(value, bytes):
        return {'binary_sha256': sha(value), 'bytes': len(value)}
    raise TypeError(type(value).__name__)


def main():
    spec = json.load(sys.stdin)
    out = []
    for source in spec['sources']:
        path = Path(source['path'])
        assert sha(path.read_bytes()) == source['sha256']
        with fitz.open(path) as document:
            rows = []
            for index in range(min(len(document), 400)):
                page = document[index]
                data = page.get_text('dict')
                text = page.get_text()
                lines = [line for block in data['blocks'] if block['type'] == 0 for line in block['lines']]
                rows.append({'page': index+1, 'rotation': page.rotation, 'text_sha256': sha(text.encode()),
                    'nonspace_characters': sum(not c.isspace() for c in text),
                    'cjk_characters': sum('\u3040' <= c <= '\u30ff' or '\u3400' <= c <= '\u9fff' for c in text),
                    'writing_mode_1_lines': sum(line['wmode'] == 1 for line in lines),
                    'native_lines': len(lines)})
            vertical = [r['page'] for r in rows if r['writing_mode_1_lines']]
            beyond = [r['page'] for r in rows if r['page'] > 1 and r['cjk_characters']]
            selected = list(dict.fromkeys([1] + (vertical[:1] if vertical else beyond[:1])))
            observations = []
            for number in selected:
                page = document[number-1]
                pix = page.get_pixmap(dpi=120, colorspace=fitz.csRGB)
                png = pix.tobytes('png')
                observations.append({'page': number, 'rotation': page.rotation,
                    'display_rect': list(page.rect), 'media_box': list(page.mediabox),
                    'rotation_matrix': list(page.rotation_matrix), 'text': page.get_text(),
                    'words': page.get_text('words'), 'native_dict': page.get_text('dict'),
                    'image_sha256': sha(png), 'pixels': [pix.width, pix.height],
                    'image_base64': base64.b64encode(png).decode('ascii')})
            out.append({'id': source['id'], 'source_sha256': source['sha256'], 'page_count': len(document),
                'inspected_pages': len(rows), 'inspection_cap': 400, 'metadata': document.metadata,
                'vertical_nomination_pages': vertical, 'inventory': rows, 'observations': observations})
    print(json.dumps({'sources': out, 'pymupdf': fitz.VersionBind, 'mupdf': fitz.VersionFitz,
        'cpu_gpu': 'CPU only;CUDA_VISIBLE_DEVICES=-1', 'ocr_calls': 0,
        'independent_reading': False}, ensure_ascii=False, default=binary))


if __name__ == '__main__':
    main()
