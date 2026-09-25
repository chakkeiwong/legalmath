"""Run source-driven search over an existing immutable source packet."""
from pathlib import Path
from ...canonical import loads,canonical
from ...storage import Database
from ..service import Interpretations
from .models import Settings
from .engine import create_search,Search
from .formal import Comparisons
from .providers import CodexProvider,Allowance


def execute(args):
    db=Database(args.data_dir);service=Interpretations(db)
    service.lc.register(loads(Path(args.identities).read_bytes()))
    settings=Settings.model_validate(loads(Path(args.settings).read_bytes()))
    packet=loads(Path(args.packet).read_bytes())
    domain=loads(Path(args.domain).read_bytes()) if args.domain else None
    run=create_search(service,args.caller,args.key,packet,settings)
    checker=Comparisons(Path(args.data_dir)/'search-java'/run['run_id'],args.jdk,args.at,domain)
    provider=CodexProvider(allowance=Allowance(args.allowance,args.total_calls))
    result=Search(service,args.caller,run['run_id'],provider,checker).drive()
    if args.output:Path(args.output).write_bytes(canonical(service.read(args.caller,run['run_id'])))
    return result
