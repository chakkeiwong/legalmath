"""Optional assisted geometry transfer preserving original OCR segmentation."""
import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import re

from .successor.contracts import digest

VERSION = 'assisted-exact-word-geometry-transfer.v1'
POLICY = 'preserve-original-segmentation.v1'
IDENTITY = ('source_sha256','page_count','selected_pages')
RUNTIME = ('dpi','language','language_models','pymupdf','mupdf')
PAGE = ('page','image_sha256','image_width','image_height','width_points','height_points')


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def valid_hash(value):
    return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None


def worker(value):
    require(isinstance(value,dict) and value.get('version')=='hybrid-ocr.v1', 'Supported hybrid worker required')
    require(valid_hash(value.get('source_sha256')), 'Pinned original source identity required')
    count=value.get('page_count'); selected=value.get('selected_pages'); pages=value.get('pages')
    require(type(count) is int and count>0 and isinstance(selected,list) and selected
            and all(type(p) is int and 1<=p<=count for p in selected)
            and selected==sorted(set(selected)), 'Unique ordered selected pages required')
    require(isinstance(pages,list) and len(pages)==len(selected)
            and all(isinstance(p,dict) for p in pages) and [p.get('page') for p in pages]==selected,
            'Complete original page denominator required')
    runtime=value.get('runtime')
    require(isinstance(runtime,dict) and all(k in runtime for k in RUNTIME)
            and 'geometry_transfer' not in runtime, 'Original untransferred runtime identity required')
    require(type(runtime['dpi']) is int and runtime['dpi']>0
            and all(isinstance(runtime[k],str) and runtime[k] for k in ('language','pymupdf','mupdf'))
            and isinstance(runtime['language_models'],dict)
            and set(runtime['language_models'])==set(runtime['language'].split('+'))
            and all(valid_hash(v) for v in runtime['language_models'].values()), 'Complete model/runtime identity required')
    for page in pages:
        require(valid_hash(page.get('image_sha256'))
                and all(type(page.get(k)) is int and page[k]>0 for k in ('image_width','image_height'))
                and all(type(page.get(k)) in (int,float) and math.isfinite(page[k]) and 0<page[k]<=10000
                        for k in ('width_points','height_points')),
                'Original page image/dimension identity required')
        require(isinstance(page.get('text'),str) and isinstance(page.get('words'),list), 'Page text/words required')
        for word in page['words']:
            require(isinstance(word,list) and len(word)==8
                    and all(type(v) in (int,float) and math.isfinite(v) for v in word[:4])
                    and word[0]<word[2] and word[1]<word[3]
                    and isinstance(word[4],str)
                    and all(type(v) is int and v>=0 for v in word[5:]), 'Malformed ordinal word')


def transfer(original, candidate, *, original_sha256, candidate_sha256, policy):
    """Copy only validated positions. Pins are canonical JSON object digests."""
    require(policy==POLICY, 'Explicit original-segmentation policy required')
    worker(original); worker(candidate)
    require(valid_hash(original_sha256) and digest(original)==original_sha256
            and valid_hash(candidate_sha256) and digest(candidate)==candidate_sha256,
            'Pinned worker identity differs')
    require(all(original[k]==candidate[k] for k in IDENTITY), 'Original source/page identity differs')
    require(all(original['runtime'][k]==candidate['runtime'][k] for k in RUNTIME), 'Model/runtime identity differs')
    result=deepcopy(original); changed=0; words=0
    for base,new,target in zip(original['pages'],candidate['pages'],result['pages']):
        require(all(base[k]==new[k] for k in PAGE), 'Original raster/page geometry differs')
        require(len(base['words'])==len(new['words']), 'Missing/extra ordinal word')
        for bw,nw,rw in zip(base['words'],new['words'],target['words']):
            require(bw[4]==nw[4], 'Ordinal word text/order differs')
            x0,y0,x1,y1=nw[:4]
            require(0<=x0<x1<=base['width_points'] and 0<=y0<y1<=base['height_points'],
                    'Candidate position is outside original page')
            changed+=bw[:4]!=nw[:4]; words+=1
            rw[:4]=nw[:4]
    result['runtime']['geometry_transfer']={
        'profile':VERSION,'policy':POLICY,'method_sha256':sha256(Path(__file__)),
        'original_worker_sha256':original_sha256,'candidate_worker_sha256':candidate_sha256,
        'words':words,'changed_rectangles':changed,
        'segmentation':'Original text, ordinal word, block and line fields retained exactly',
        'coordinate_system':'Candidate positions already expressed in original page coordinates',
        'assisted':True,'automatic_segmentation':False,'independent_legal_acceptance':False}
    return result


def transfer_files(original, candidate, output, *, original_sha256, candidate_sha256, policy):
    """File pins cover actual bytes; the output also retains object digest pins."""
    source=Path(original); alternate=Path(candidate); target=Path(output)
    require(source.is_file() and alternate.is_file(), 'Both retained worker files required')
    require(not target.exists(), 'Geometry output already exists; no automatic retry')
    a=source.read_bytes(); b=alternate.read_bytes()
    require(hashlib.sha256(a).hexdigest()==original_sha256
            and hashlib.sha256(b).hexdigest()==candidate_sha256, 'Pinned worker file identity differs')
    base=json.loads(a); new=json.loads(b)
    result=transfer(base,new,original_sha256=digest(base),candidate_sha256=digest(new),policy=policy)
    result['runtime']['geometry_transfer']['input_files']={
        'original_sha256':original_sha256,'candidate_sha256':candidate_sha256}
    with target.open('x') as stream:
        json.dump(result,stream,ensure_ascii=False,allow_nan=False,indent=2); stream.write('\n')
    return {'output_sha256':sha256(target),'words':result['runtime']['geometry_transfer']['words'],
            'changed_rectangles':result['runtime']['geometry_transfer']['changed_rectangles']}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('original','candidate','original-sha256','candidate-sha256','policy','output'):
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args(argv)
    print(json.dumps(transfer_files(args.original,args.candidate,args.output,
        original_sha256=args.original_sha256,candidate_sha256=args.candidate_sha256,policy=args.policy)))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
