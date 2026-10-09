"""Internal Cassis worker used by the fixed integration runner."""
import json
import sys
import argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from legalmath.prospectus.successor import annotation_authoring as draft,annotation_xmi as xmi


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('empty','decode','admit'))
    parser.add_argument('source_path');parser.add_argument('cas_path');parser.add_argument('output_path')
    parser.add_argument('--types',help='Explicit exported TypeSystem.xml for standalone XMI')
    args=parser.parse_args()
    operation,source_path,cas_path,output_path=args.operation,args.source_path,args.cas_path,args.output_path
    data=json.loads(Path(source_path).read_text())
    if operation=='empty':
        raw,types=draft.empty(data['text'],data['source'])
        Path(cas_path).write_bytes(raw);Path(output_path).write_bytes(types)
    elif operation in ('decode','admit'):
        out=draft.decode(Path(cas_path).read_bytes(),data['source'],data['text'],
                         types=Path(args.types).read_bytes() if args.types else None)
        Path(output_path).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
        if operation=='decode' and xmi.normalized(out['packet'])!=xmi.normalized(data):
            raise ValueError('Actual authored packet differs from independent expected operation')
    else:raise ValueError('Unknown fixed codec operation')


if __name__=='__main__':main()
