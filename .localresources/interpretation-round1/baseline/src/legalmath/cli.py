"""Command line entry point; commands are added with their implementation."""
import argparse
import json
from pathlib import Path
from . import __version__


def main():
    parser = argparse.ArgumentParser(prog="legalmath")
    parser.add_argument("--version", action="version", version=__version__)
    subs = parser.add_subparsers(dest="command")
    evaluate = subs.add_parser("evaluate", help="Evaluate an explicit bundle/snapshot request")
    evaluate.add_argument("request")
    demo = subs.add_parser("demo", help="Run the full offline synthetic SPI walkthrough")
    demo.add_argument("--repository", default=".")
    demo.add_argument("--workdir", required=True)
    demo.add_argument("--jdk", required=True)
    serve = subs.add_parser("serve", help="Serve the public/synthetic workbench on localhost")
    serve.add_argument("--data-dir", required=True)
    serve.add_argument("--identities", required=True)
    serve.add_argument("--jdk")
    serve.add_argument("--comparison-jar")
    serve.add_argument("--port", type=int, default=8765)
    discovery = subs.add_parser("refresh", help="Read-only SFC discovery with persisted page/cursor evidence")
    discovery.add_argument("--data-dir", required=True)
    discovery.add_argument("--category", choices=["products", "intermediaries"], default="products")
    export = subs.add_parser("export-java", help="Export exact reviewed Java release bytes")
    export.add_argument("--data-dir", required=True)
    export.add_argument("--release-hash", required=True)
    export.add_argument("--output", required=True)
    build = subs.add_parser("build-java", help="Compile and verify a stored draft candidate")
    for name in ("data-dir", "bundle-hash", "cases", "jdk", "output", "identities", "caller"):
        build.add_argument("--" + name, required=True)
    build.add_argument("--event-cases")
    sources = subs.add_parser("sources", help="Import a hash-bound retained source manifest")
    source_commands = sources.add_subparsers(dest="source_command", required=True)
    source_import = source_commands.add_parser("import")
    source_import.add_argument("--manifest", required=True)
    source_import.add_argument("--data-dir", default="artifacts/workbench")
    acceptance = subs.add_parser("acceptance", help="Run the named offline end-to-end engineering scenario")
    acceptance.add_argument("--scenario", choices=["spi-23ec35"], required=True)
    acceptance.add_argument("--offline", action="store_true", required=True)
    acceptance.add_argument("--out", required=True)
    acceptance.add_argument("--jdk", default=".localresources/java-toolchain/jdk-17.0.20.1+1")
    acceptance.add_argument("--repository", default=".")
    args = parser.parse_args()
    from .canonical import loads
    try:
        if args.command == "evaluate":
            from .conformance import evaluate_case
            result = evaluate_case(loads(Path(args.request).read_bytes()))
        elif args.command == "demo":
            from .demo import walkthrough
            result = walkthrough(args.repository, args.workdir, str(Path(args.jdk).resolve()))
        elif args.command == "acceptance":
            from .demo import walkthrough
            result = walkthrough(args.repository, args.out, str(Path(args.jdk).resolve()))
        elif args.command == "sources":
            from .sources.manifest import import_manifest
            from .storage import Database
            result = import_manifest(Database(args.data_dir), args.manifest)
        elif args.command == "serve":
            import uvicorn
            from .api.app import create_app
            app = create_app(args.data_dir, loads(Path(args.identities).read_bytes()), jdk=args.jdk, comparison_jar=args.comparison_jar)
            uvicorn.run(app, host="127.0.0.1", port=args.port)
            return
        elif args.command == "refresh":
            from .sources.discovery import refresh_official
            from .storage import Database
            result = refresh_official(Database(args.data_dir), args.category)
        elif args.command == "export-java":
            from .review.releases import Releases
            from .storage import Database
            result = Releases(Database(args.data_dir)).export_java(args.release_hash, args.output)
        elif args.command == "build-java":
            from .review.releases import Releases
            from .storage import Database
            from .review.lifecycle import Lifecycle
            from .canonical import digest
            db = Database(args.data_dir)
            Lifecycle(db).register(loads(Path(args.identities).read_bytes()))
            cases = loads(Path(args.cases).read_bytes())
            if isinstance(cases, dict): cases = cases["cases"]
            events = loads(Path(args.event_cases).read_bytes()) if args.event_cases else None
            result = Releases(db).build(args.caller, "cli.build." + digest({"cases": cases, "events": events}), args.bundle_hash, args.output, args.jdk, cases, events)
        else:
            parser.print_help()
            return
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        from .errors import LegalMathError
        if not isinstance(exc, LegalMathError): raise
        print(json.dumps(exc.envelope()))
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
