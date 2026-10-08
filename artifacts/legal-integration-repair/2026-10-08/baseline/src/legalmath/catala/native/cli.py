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
    generate.add_argument('--reading',help='Select an existing shared interpretation when several readings remain')
    generate.add_argument('--shared-version',choices=('1','2'),help='Shared model version (default: 2 for multiple outputs, otherwise 1)')
    generate.add_argument('--legacy-code-generation',action='store_true',help='Explicit compatibility mode for the historical target-specific generator')
    compile_cmd = commands.add_parser('build', help='Build a retained native candidate')
    for name in ('task','candidate','out'):
        compile_cmd.add_argument('--'+name,required=True)
    check = commands.add_parser('verify', help='Exact reference and interpreter/Java checks')
    for name in ('build','cases','out'):
        check.add_argument('--'+name,required=True)
    execute = commands.add_parser('execute', help='Draft execution with complete-input semantics')
    for name in ('build','snapshot'):
        execute.add_argument('--'+name,required=True)
    execute.add_argument('--rule',help='Select a shared output; omit to return all outputs')
    for command in (generate,compile_cmd,check,execute):
        command.add_argument('--jdk',required=True)
    for command in (generate,compile_cmd):
        for name in ('compiler','upstream','lock'):
            command.add_argument('--'+name,required=True)
    check.add_argument('--compiler',required=True)


def dispatch(args):
    read = lambda name: loads(Path(name).read_bytes())
    if args.native_command == 'generate':
        if not args.legacy_code_generation:
            from ...translation.cli import provider
            from ...translation.native_compat import convert as shared_convert
            return shared_convert(read(args.task),args.out,provider(args),args.jdk,
                compiler=args.compiler,upstream=args.upstream,lock=args.lock,resume=args.resume,
                max_revisions=0 if args.no_revision else 1,reading_id=args.reading,shared_version=args.shared_version)
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
    if args.native_command in ('verify','execute') and (Path(args.build)/'model.json').exists():
        from ...translation.native_compat import execute_native,snapshot
        from ...translation.verification import verify_execution,verify_executions
        from ...translation.pipeline import verify_build
        if args.native_command=='execute':return execute_native(args.build,read(args.snapshot),args.jdk,rule_id=args.rule)
        cases=read(args.cases);records=[]
        for c in cases:
            result=execute_native(args.build,c['snapshot'],args.jdk)
            expected=c['expected'];value=expected.get('value')
            if result['record_type']=='TranslatedRuleResults':
                if result['status']!=expected['status'] or result['value']!=value:raise LegalMathError('E_INTEGRITY',details=c['id'])
                if 'reason' in expected and result['reason']!=expected['reason']:raise LegalMathError('E_INTEGRITY',details=c['id'])
                m,_,_=verify_build(args.build);checks={}
                references=expected.get('results')
                if references is None:
                    if not isinstance(value,dict) or set(value)!=set(result['results']):raise LegalMathError('E_SCHEMA')
                    references={k:{'status':('TRUE' if v else 'FALSE') if type(v)is bool else 'VALUE','value':v} for k,v in value.items()}
                if set(references)!=set(result['results']):raise LegalMathError('E_SCHEMA')
                checks=verify_executions(args.build,snapshot(c['snapshot'],m),result,references,args.jdk,compiler=args.compiler)
                records.append({'case_id':c['id'],'result':result,'checks':checks});continue
            if value is not None:
                if len(value)!=1:raise LegalMathError('E_SCHEMA')
                value=next(iter(value.values()))
            status=expected['status']
            if status=='VALUE' and type(value)is bool:status='TRUE' if value else 'FALSE'
            if (result['status']!=status or result['value']!=value
                    or ('reason' in expected and result['reason']!=expected['reason'])):raise LegalMathError('E_INTEGRITY',details=c['id'])
            m,_,_=verify_build(args.build)
            reference={'status':status,'value':value,**({'reason':expected['reason']} if 'reason' in expected else {})}
            checks=verify_execution(args.build,snapshot(c['snapshot'],m),result,reference,args.jdk,compiler=args.compiler)
            records.append({'case_id':c['id'],'result':result,'checks':checks})
        if not records:raise LegalMathError('E_SCHEMA')
        report={'record_type':'TranslatedRuleVerification','passed':len(records),'records':records}
        Path(args.out).write_bytes(canonical(report));return report
    if args.native_command == 'verify':
        report = verify_cases(args.build,read(args.cases),args.jdk,compiler=args.compiler)
        Path(args.out).write_bytes(canonical(report))
        return report
    return evaluate(args.build,read(args.snapshot),args.jdk)
