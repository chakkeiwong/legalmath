"""Distinguish unusable finite OCR positions from corrupt word records."""
import math


def hybrid_word_issue(word, page, *, allow_unknown=False):
    if (not isinstance(word, (list, tuple)) or len(word) != 8 or
            any(type(v) not in (int, float) or not math.isfinite(v) for v in word[:4]) or
            not isinstance(word[4], str) or
            any(type(v) is not int or v < 0 for v in word[5:]) or
            not word[0] < word[2] or not word[1] < word[3]):
        raise ValueError("Hybrid word outside original rendered page geometry: malformed word")
    if (-1e-3 <= word[0] < word[2] <= page['width_points'] + 1e-3 and
            -1e-3 <= word[1] < word[3] <= page['height_points'] + 1e-3):
        return None
    if not allow_unknown:
        raise ValueError("Hybrid word outside original rendered page geometry")
    return {"kind": "OCR_WORD_OUTSIDE_PAGE", "raw_bbox": list(word[:4]),
        "page": page['page'], "image_sha256": page['image_sha256'],
        "page_bounds": [0, 0, page['width_points'], page['height_points']],
        "status": "UNKNOWN_GEOMETRY; raw text retained; spatial use requires independent review"}
