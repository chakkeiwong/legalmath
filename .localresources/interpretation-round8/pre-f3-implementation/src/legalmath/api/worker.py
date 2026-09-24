"""Bounded subprocess entry; requests are data and never executed as code."""
from pathlib import Path
import resource
import sys

from ..canonical import canonical, loads


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (55, 60))
    resource.setrlimit(resource.RLIMIT_FSIZE, (20 * 1024 * 1024, 20 * 1024 * 1024))
    payload = loads(Path(sys.argv[1]).read_bytes())
    r = payload["request"]
    if payload["kind"] == "draft":
        from ..drafting.provider import StubProvider
        from ..drafting.validate import propose
        result = propose(r["source_inventory"], StubProvider(r["responses"]), max_attempts=r.get("max_attempts", 3))
    elif payload["kind"] == "compare":
        from ..analysis.compare import compare
        result = compare(**r)
    else:
        raise ValueError("Unsupported job")
    Path(sys.argv[2]).write_bytes(canonical(result))


if __name__ == "__main__":
    main()
