"""Public command for investigation, verification, feed inspection and replay."""
import argparse
from pathlib import Path

from ..canonical import canonical, loads
from .engine import investigate, revalidate
from .evidence import Store
from .intake import bootstrap
from .lifecycle import replay
from .sanctions import parse, candidates


def main():
    parser = argparse.ArgumentParser(description="Qualified bank-compliance investigations; no execution authority")
    commands = parser.add_subparsers(dest="command", required=True)
    p = commands.add_parser("example", help="Import retained public sources; leave account and bank policy unknown")
    p.add_argument("--root", type=Path, default=Path.cwd())
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--at", required=True)
    p = commands.add_parser("freeze", help="Record the current method and sources before new observations")
    p.add_argument("--request", type=Path, required=True)
    p.add_argument("--store", type=Path, required=True)
    p.add_argument("--at", required=True)
    p.add_argument("--out", type=Path, required=True)
    p = commands.add_parser("observe", help="Investigate unseen source content under the frozen method")
    p.add_argument("--request", type=Path, required=True)
    p.add_argument("--store", type=Path, required=True)
    p.add_argument("--freeze", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p = commands.add_parser("refresh-feeds", help="Download, validate and retain new official list snapshots")
    p.add_argument("--root", type=Path, default=Path.cwd())
    for name in ("evaluate", "verify"):
        p = commands.add_parser(name)
        p.add_argument("--request", type=Path, required=True)
        p.add_argument("--store", type=Path, required=True)
        p.add_argument("--receipt", type=Path, required=name == "verify")
        p.add_argument("--out", type=Path, required=True)
    p = commands.add_parser("screen", help="Exact name candidates; no clearance from absence")
    p.add_argument("--xml", type=Path, required=True)
    p.add_argument("--list", choices=("SDN", "CONSOLIDATED"), required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--out", type=Path, required=True)
    p = commands.add_parser("execute-native", help="Evaluate retrieved transaction facts using retained compiled builds")
    p.add_argument("--request", type=Path, required=True)
    p.add_argument("--receipt", type=Path, required=True)
    p.add_argument("--store", type=Path, required=True)
    p.add_argument("--builds", type=Path, required=True)
    p.add_argument("--target", choices=("ruleir", "catala"), required=True)
    p.add_argument("--jdk", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p = commands.add_parser("replay")
    p.add_argument("--events", type=Path, required=True)
    p.add_argument("--store", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "refresh-feeds":
        from .feeds import retain
        result = retain(args.root, download=True)
        print(canonical(result).decode())
        return
    if args.command == "execute-native":
        from .native import execute
        result = execute(loads(args.receipt.read_bytes()), loads(args.request.read_bytes()), Store(args.store),
                         args.builds, args.target, args.jdk)
        output = args.out
    elif args.command == "freeze":
        from .prospective import freeze
        store = Store(args.store)
        registry = store.json(loads(args.request.read_bytes())["registry_sha256"])
        result = freeze(at=args.at, known_source_hashes=[r["blob"] for r in registry.values()])
        output = args.out
    elif args.command == "observe":
        from .prospective import observe
        result = observe(loads(args.freeze.read_bytes()), loads(args.request.read_bytes()), Store(args.store))
        output = args.out
    elif args.command == "example":
        request, store = bootstrap(args.root, args.out, at=args.at)
        result = investigate(request, store)
        output = args.out / "receipt.json"
    elif args.command in {"evaluate", "verify"}:
        request, store = loads(args.request.read_bytes()), Store(args.store)
        result = (investigate(request, store) if args.command == "evaluate" else
                  revalidate(loads(args.receipt.read_bytes()), request, store))
        output = args.out
    elif args.command == "screen":
        result = candidates(parse(args.xml.read_bytes(), list_kind=args.list), args.name)
        output = args.out
    else:
        result = replay(loads(args.events.read_bytes()), store=Store(args.store))
        output = args.out
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical(result))
    print(str(output))


if __name__ == "__main__":
    main()
