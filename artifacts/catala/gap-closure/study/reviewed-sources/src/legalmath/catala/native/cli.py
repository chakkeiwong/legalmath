"""The direct converter is a separate API/profile from RuleIR build-java."""
from pathlib import Path
from ...canonical import canonical, loads
from ...errors import LegalMathError
from ...interpretation.search.providers import Allowance, CodexProvider
from .converter import convert
from .runtime import build, evaluate, verify_cases


def configure(parser):
    commands = parser.add_subparsers(dest='native_command', required=True)
    generate = commands.add_parser('generate', help='Fresh native generation and source criticism')
    for name in ('task','out','allowance'):
        generate.add_argument('--'+name,required=True)
    generate.add_argument('--max-calls', type=int, choices=range(1,5), default=4)
    generate.add_argument('--resume',action='store_true')
    generate.add_argument('--routing-file')
    generate.add_argument('--no-revision',action='store_true')
    compile_cmd = commands.add_parser('build', help='Build a retained native candidate')
    for name in ('task','candidate','out'):
        compile_cmd.add_argument('--'+name,required=True)
    check = commands.add_parser('verify', help='Exact reference and interpreter/Java checks')
    for name in ('build','cases','out'):
        check.add_argument('--'+name,required=True)
    execute = commands.add_parser('execute', help='Draft execution with complete-input semantics')
    for name in ('build','snapshot'):
        execute.add_argument('--'+name,required=True)
    for command in (generate,compile_cmd,check,execute):
        command.add_argument('--jdk',required=True)
    for command in (generate,compile_cmd):
        for name in ('compiler','upstream','lock'):
            command.add_argument('--'+name,required=True)
    check.add_argument('--compiler',required=True)


def dispatch(args):
    read = lambda name: loads(Path(name).read_bytes())
    if args.native_command == 'generate':
        ledger = Path(args.allowance).resolve()
        if not ledger.exists():
            raise LegalMathError('E_AUTHORITY',details='Supply an existing authorized allowance')
        data = read(ledger)
        receipt = Path(args.out) / 'allowance-commitment.json'
        if receipt.exists():
            if not args.resume:
                raise LegalMathError('E_JOB_STATE')
            commitment = read(receipt)
            from ...interpretation.search.providers import verify_allowance_checkpoint
            verify_allowance_checkpoint(ledger, commitment['checkpoint_hash'])
            if commitment['path'] != str(ledger) or commitment['max_calls'] != args.max_calls:
                raise LegalMathError('E_INTEGRITY')
        else:
            from ...canonical import digest
            commitment = {'path':str(ledger),'checkpoint_hash':digest(data),'max_calls':args.max_calls,
                          'ceiling':min(data['maximum'],len(data['calls'])+args.max_calls)}
            receipt.parent.mkdir(parents=True,exist_ok=True)
            receipt.write_bytes(canonical(commitment))
        provider = CodexProvider(allowance=Allowance(ledger,data['maximum'],reservation_ceiling=commitment['ceiling']),routing_file=args.routing_file)
        return convert(read(args.task),args.out,provider,args.jdk,compiler=args.compiler,upstream=args.upstream,lock=args.lock,
                       resume=args.resume,max_revisions=0 if args.no_revision else 1)
    if args.native_command == 'build':
        return build(read(args.task),read(args.candidate),args.out,args.jdk,compiler=args.compiler,upstream=args.upstream,lock=args.lock)
    if args.native_command == 'verify':
        report = verify_cases(args.build,read(args.cases),args.jdk,compiler=args.compiler)
        Path(args.out).write_bytes(canonical(report))
        return report
    return evaluate(args.build,read(args.snapshot),args.jdk)
