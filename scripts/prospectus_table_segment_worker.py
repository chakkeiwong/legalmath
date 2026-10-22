"""Sealed CPU experiment: two predetermined crop presentations, no text repair."""
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
os.environ['OMP_THREAD_LIMIT'] = '1'
import base64
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import fitz


def hashed(data):
    return hashlib.sha256(data).hexdigest()


def crop(source, bbox, scale):
    factor = 300 / 72
    l, t = [math.floor(v * factor) for v in bbox[:2]]
    r, b = [math.ceil(v * factor) for v in bbox[2:]]
    assert source.n == 3 and 0 <= l < r <= source.width and 0 <= t < b <= source.height
    original = source.samples
    rows = [original[(y * source.width + l) * 3:(y * source.width + r) * 3] for y in range(t, b)]
    pad = 10 * scale
    width, height = (r - l) * scale + 2 * pad, (b - t) * scale + 2 * pad
    border = b'\xff' * width * 3
    output = [border] * pad
    for row in rows:
        expanded = b''.join(row[i:i+3] * scale for i in range(0, len(row), 3))
        padded = b'\xff' * (pad * 3) + expanded + b'\xff' * (pad * 3)
        output.extend([padded] * scale)
    output.extend([border] * pad)
    pix = fitz.Pixmap(fitz.csRGB, width, height, b''.join(output), False)
    pix.set_dpi(300, 300)
    return pix, {'source_pixel_rect': [l, t, r, b], 'source_dpi': 300,
        'scale': scale, 'pad_pixels': pad, 'output_dpi': 300, 'output_pixels': [width, height],
        'original_crop_rgb_sha256': hashed(b''.join(rows)), 'processed_rgb_sha256': hashed(pix.samples),
        'interpolation': 'EXACT_PIXEL_REPLICATION', 'text_correction': False}


def contact_sheet(pixmaps):
    width = max(p.width for p in pixmaps)
    height = sum(p.height + 8 for p in pixmaps)
    rows = []
    for pix in pixmaps:
        samples = pix.samples
        for y in range(pix.height):
            rows.append(samples[y * pix.width * 3:(y + 1) * pix.width * 3] + b'\xff' * ((width - pix.width) * 3))
        rows.extend([b'\xcc' * width * 3] * 8)
    return fitz.Pixmap(fitz.csRGB, width, height, b''.join(rows), False).tobytes('png')


def main():
    spec = json.load(sys.stdin)
    assert spec['mode'] in {'crops', 'ocr'}
    assert hashed(Path(spec['image_path']).read_bytes()) == spec['image_sha256']
    assert hashed(Path(spec['source_path']).read_bytes()) == spec['source_sha256']
    assert hashed((Path(spec['tessdata']) / 'eng.traineddata').read_bytes()) == spec['model_sha256']
    assert len(spec['regions']) == 20 and len({r['id'] for r in spec['regions']}) == 20
    assert all(set(r) == {'id', 'bbox'} for r in spec['regions'])
    source = fitz.Pixmap(spec['image_path'])
    assert (source.width, source.height) == (3300, 2550)
    output = []
    scaled = []
    for region in spec['regions']:
        for scale in (1, 3):
            tick = time.monotonic()
            pix, transform = crop(source, region['bbox'], scale)
            png = pix.tobytes('png')
            row = {'id': region['id'], 'scale': scale, 'bbox': region['bbox'], 'transform': transform,
                'crop_sha256': hashed(png)}
            if spec['mode'] == 'crops':
                row['image_base64'] = base64.b64encode(png).decode('ascii')
                if scale == 3:
                    scaled.append(pix)
            else:
                with fitz.open(stream=pix.pdfocr_tobytes(language='eng', tessdata=spec['tessdata']), filetype='pdf') as document:
                    page = document[0]
                    row.update(raw_text=page.get_text(sort=True), raw_words=page.get_text('words'))
                mapped = []
                left, top, _, _ = transform['source_pixel_rect']
                pad = transform['pad_pixels']
                for word in row['raw_words']:
                    box = [(left + (word[0] * 300/72 - pad)/scale)*72/300,
                           (top + (word[1] * 300/72 - pad)/scale)*72/300,
                           (left + (word[2] * 300/72 - pad)/scale)*72/300,
                           (top + (word[3] * 300/72 - pad)/scale)*72/300]
                    mapped.append({'text': word[4], 'bbox': box, 'crop_bbox': word[:4]})
                row['mapped_words'] = mapped
            row['wall_seconds'] = time.monotonic() - tick
            output.append(row)
    result = {'mode': spec['mode'], 'source_sha256': spec['source_sha256'],
        'image_sha256': spec['image_sha256'], 'model_sha256': spec['model_sha256'],
        'runtime': {'pymupdf': fitz.VersionBind, 'mupdf': fitz.VersionFitz,
                    'cpu_gpu': 'CPU only; CUDA_VISIBLE_DEVICES=-1'}, 'rows': output,
        'ocr_operations': 40 if spec['mode'] == 'ocr' else 0}
    if spec['mode'] == 'crops':
        result['contact_sheets'] = [base64.b64encode(contact_sheet(scaled[i:i+10])).decode('ascii') for i in (0, 10)]
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
