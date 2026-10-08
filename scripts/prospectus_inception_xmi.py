"""Run the optional Cassis codec in the retained annotation sidecar."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from legalmath.prospectus.successor.annotation_xmi import encode, decode, normalized


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["encode", "decode"])
    parser.add_argument("--packet", required=True)
    parser.add_argument("--xmi", required=True)
    parser.add_argument("--types")
    parser.add_argument("--output")
    parser.add_argument("--expect-equal", action="store_true", help="Trial assertion: require the predeclared edited packet")
    args = parser.parse_args()
    packet = json.loads(Path(args.packet).read_text())
    if args.command == "encode":
        xmi, types = encode(packet)
        Path(args.xmi).write_bytes(xmi)
        Path(args.types).write_bytes(types)
    else:
        result = decode(Path(args.xmi).read_bytes(), packet["source"], packet["text"],
                        types=Path(args.types).read_bytes() if args.types else None)
        Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        if args.expect_equal and normalized(result) != normalized(packet):
            raise ValueError("Actual exported packet differs from predeclared expected edit")
    print(json.dumps({"operation": args.command, "status": "PASS"}))


if __name__ == "__main__":
    main()
