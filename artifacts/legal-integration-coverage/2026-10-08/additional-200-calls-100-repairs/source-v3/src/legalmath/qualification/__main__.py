"""Run machine qualification and manage frozen prospective windows."""
import argparse
from pathlib import Path
from ..canonical import canonical, loads, digest
from . import assurance, prospective


def add_execution_arguments(parser, *, verify=False):
    parser.add_argument('--model', required=True)
    parser.add_argument('--jdk', required=True)
    parser.add_argument('--compiler')
    if verify:
        parser.add_argument('--directory', required=True)
    else:
        parser.add_argument('--cases', required=True)
        parser.add_argument('--out', required=True)
        parser.add_argument('--upstream'); parser.add_argument('--lock')


def execute(args, *, verify=False):
    model = loads(Path(args.model).read_bytes())
    if verify:
        return assurance.verify(args.directory, model, args.jdk, compiler=args.compiler)
    toolchain = None
    if any((args.compiler, args.upstream, args.lock)):
        if not all((args.compiler, args.upstream, args.lock)):
            from ..errors import LegalMathError
            raise LegalMathError('E_SCHEMA', details='Supply compiler, upstream and lock together')
        toolchain = {k: getattr(args, k) for k in ('compiler', 'upstream', 'lock')}
    return assurance.run(model, loads(Path(args.cases).read_bytes()), args.out, args.jdk, toolchain=toolchain)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    add_execution_arguments(commands.add_parser('assure'))
    add_execution_arguments(commands.add_parser('verify'), verify=True)
    freeze = commands.add_parser('freeze')
    freeze.add_argument('--out', required=True); freeze.add_argument('--ends-at', required=True)
    freeze.add_argument('--family', action='append', required=True)
    freeze.add_argument('--development-source', action='append', default=[])
    for name in ('admit', 'repair', 'report'):
        sub = commands.add_parser(name); sub.add_argument('--directory', required=True); sub.add_argument('--window-hash', required=True)
        if name == 'admit': sub.add_argument('--item', required=True)
        if name == 'repair': sub.add_argument('--reason', required=True)
        if name == 'report': sub.add_argument('--head-hash')
    args = parser.parse_args(argv)
    if args.command in ('assure', 'verify'):
        result = execute(args, verify=args.command == 'verify')
    elif args.command == 'freeze':
        result = prospective.freeze(args.out, digest(assurance.method_manifest()), args.family,
                                    ends_at=args.ends_at, development_sources=args.development_source)
    elif args.command == 'admit':
        result = prospective.admit(args.directory, args.window_hash, loads(Path(args.item).read_bytes()),
                                   method_hash=digest(assurance.method_manifest()))
    elif args.command == 'repair':
        result = prospective.repair(args.directory, args.window_hash, new_method_hash=digest(assurance.method_manifest()), reason=args.reason)
    else:
        result = prospective.report(args.directory, args.window_hash,expected_head=args.head_hash)
    print(canonical(result).decode())


if __name__ == '__main__':
    main()
