"""Public modular workflow: interpret once, then choose deterministic targets."""
from pathlib import Path
from ..canonical import loads,canonical,digest
from ..interpretation.search.providers import Allowance,CodexProvider,verify_allowance_checkpoint
from .frontend import interpret
from .pipeline import translate,build,execute,execute_all
from .model import from_bundle,fail


def configure(parser):
    commands=parser.add_subparsers(dest='rule_command',required=True)
    from ..qualification.__main__ import add_execution_arguments
    add_execution_arguments(commands.add_parser('assure',help='Machine-checked proof or explicit qualification; no human quality labels'))
    add_execution_arguments(commands.add_parser('verify-assurance',help='Recheck proof and runtime evidence against current source and method'),verify=True)
    front=commands.add_parser('interpret',help='Shared source interpretation and criticism; no target selection')
    for name in ('task','out','allowance'):front.add_argument('--'+name,required=True)
    front.add_argument('--max-calls',type=int,choices=range(1,5),default=4)
    front.add_argument('--resume',action='store_true');front.add_argument('--no-revision',action='store_true')
    front.add_argument('--routing-file')
    inspect=commands.add_parser('resources',help='Inspect Catala resource expansion without compiling')
    inspect.add_argument('--model',required=True);inspect.add_argument('--out',required=True)
    for name in ('translate','build'):
        command=commands.add_parser(name)
        command.add_argument('--model',required=True);command.add_argument('--target',choices=('ruleir','catala'),required=True)
        command.add_argument('--out',required=True)
        if name=='build':
            command.add_argument('--jdk',required=True)
            for option in ('compiler','upstream','lock'):command.add_argument('--'+option)
    run=commands.add_parser('execute',help='Draft execution under the model policy; no release authorization')
    for name in ('build','snapshot','valid-at','known-at','jdk'):run.add_argument('--'+name,required=True)
    selection=run.add_mutually_exclusive_group(required=True)
    selection.add_argument('--rule');selection.add_argument('--all',action='store_true')
    imp=commands.add_parser('import-ruleir',help='Wrap an existing RuleIR bundle without changing its semantics')
    for name in ('bundle','out'):imp.add_argument('--'+name,required=True)


def provider(args):
    ledger=Path(args.allowance).resolve()
    if not ledger.is_file():fail('E_AUTHORITY','An existing authorized allowance is required')
    value=loads(ledger.read_bytes());receipt=Path(args.out)/'allowance-commitment.json'
    if receipt.exists():
        if not args.resume:fail('E_JOB_STATE')
        commitment=loads(receipt.read_bytes());verify_allowance_checkpoint(ledger,commitment['checkpoint_hash'])
        if commitment['path']!=str(ledger) or commitment['max_calls']!=args.max_calls:fail('E_INTEGRITY')
    else:
        commitment={'path':str(ledger),'checkpoint_hash':digest(value),'max_calls':args.max_calls,
                    'ceiling':min(value['maximum'],len(value['calls'])+args.max_calls)}
        receipt.parent.mkdir(parents=True,exist_ok=True);receipt.write_bytes(canonical(commitment))
    return CodexProvider(allowance=Allowance(ledger,value['maximum'],reservation_ceiling=commitment['ceiling']),routing_file=args.routing_file)


def dispatch(args):
    read=lambda name:loads(Path(name).read_bytes())
    if args.rule_command in ('assure','verify-assurance'):
        from ..qualification.__main__ import execute as qualify
        return qualify(args,verify=args.rule_command=='verify-assurance')
    if args.rule_command=='interpret':
        return interpret(read(args.task),args.out,provider(args),resume=args.resume,max_revisions=0 if args.no_revision else 1)
    if args.rule_command=='resources':
        from .resources import preflight
        value=preflight(read(args.model));Path(args.out).write_bytes(canonical(value));return value
    if args.rule_command=='translate':
        value=translate(read(args.model),args.target);Path(args.out).write_bytes(canonical(value));return value
    if args.rule_command=='build':
        toolchain=None
        if args.target=='catala':
            if not all((args.compiler,args.upstream,args.lock)):fail('E_NOT_FOUND','Catala target requires --compiler, --upstream and --lock')
            toolchain={k:getattr(args,k) for k in ('compiler','upstream','lock')}
        return build(read(args.model),args.target,args.out,args.jdk,catala_toolchain=toolchain)
    if args.rule_command=='import-ruleir':
        value=from_bundle(read(args.bundle));Path(args.out).write_bytes(canonical(value));return value
    if args.all:
        return execute_all(args.build,read(args.snapshot),args.valid_at,args.known_at,args.jdk)
    return execute(args.build,read(args.snapshot),args.rule,args.valid_at,args.known_at,args.jdk)
