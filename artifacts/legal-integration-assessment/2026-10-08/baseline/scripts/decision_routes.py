"""Fixed substantive round-13 phase commands."""
from pathlib import Path
from argparse import ArgumentParser
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

def main():
    parser=ArgumentParser(__doc__)
    parser.add_argument('phase',choices=['sources','pdf','live','java','documents'])
    parser.add_argument('--out',required=True)
    args=parser.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    if args.phase=='live':
        from decision_live import run
    elif args.phase=='sources':
        from decision_sources import run
    elif args.phase=='pdf':
        from decision_pdf import run
    elif args.phase=='java':
        from decision_java import run
    else:
        from decision_documents import run
    result=run(out)
    print(result.get('status','EXECUTED'))
if __name__=='__main__':main()
