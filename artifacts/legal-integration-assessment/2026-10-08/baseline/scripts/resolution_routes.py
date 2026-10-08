"""Fixed phase dispatcher; arguments cannot select a shell command or URL."""
from pathlib import Path
import argparse
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['R0','R1','R3','R4','R5','R6','R7'])
    parser.add_argument('--out',required=True);args=parser.parse_args();out=Path(args.out).resolve()
    if not out.is_relative_to(ROOT/'artifacts/interpretation/round14'):raise ValueError('Fixed artifact root required')
    out.mkdir(parents=True,exist_ok=True)
    if args.phase=='R0':from resolution_support import inventory as run
    elif args.phase=='R1':from resolution_sources import run
    elif args.phase=='R3':from resolution_live import run
    elif args.phase=='R4':from resolution_pdf import run
    elif args.phase=='R5':from resolution_new import run
    elif args.phase=='R6':from resolution_verify import run
    else:from resolution_documents import run
    value=run(out);print(value['status'],flush=True)

if __name__=='__main__':main()
