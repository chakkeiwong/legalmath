"""Authorized live generation from two retained public circulars; no supplied readings."""
from argparse import ArgumentParser
from pathlib import Path
import re
from legalmath.canonical import canonical,digest,raw_digest,loads
from legalmath.storage import Database
from legalmath.storage.archive import export_history
from legalmath.sources.intake import import_source
from legalmath.sources.extract import extract
from legalmath.sources.anchors import make_span
from legalmath.interpretation import Interpretations
from legalmath.interpretation.search.models import Settings,DIMENSIONS
from legalmath.interpretation.search.engine import Search,create_search
from legalmath.interpretation.search.formal import Comparisons
from legalmath.interpretation.search.providers import CodexProvider,Allowance

ROOT=Path(__file__).resolve().parents[1]
AT='2026-09-23T00:00:00.000000Z'


def pilot_measurements(engine,report):
    counts={'initial_generated':sum(v is not None for v in engine.state['initial'].values()),
            'candidates':len(engine.state['nodes']),
            'children':sum(n['parent'] is not None for n in engine.state['nodes']),
            'roundtrips':len(engine.state['roundtrips']),
            'comparisons':len(engine.state['comparisons']),
            'search_rounds':engine.state['rounds'],
            'java_checks':len(engine.state['java_checks']),
            'encoding_errors':sum(n['encoding_error'] is not None for n in engine.state['nodes']),
            'failures':engine.state['failures']}
    counts['unrepaired_failures']=[f for f in counts['failures']
        if f.get('repair')!='VALIDATED_OUTPUT_ONLY_MEANING_UNRESOLVED']
    # Recovering malformed output is a tested behavior, not a reason to erase the
    # failure or reject the repair. Legal uncertainty still blocks every release.
    passed=(counts['initial_generated']==3 and counts['candidates']>=2 and counts['children']>=1
            and counts['roundtrips']>=1 and not counts['unrepaired_failures']
            and report['status']=='BLOCKED_UNRESOLVED' and not report['release_eligible'])
    return counts,passed


def source_packet(db,ref):
    raw=(ROOT/'.localresources/sfc'/f'{ref}.json').read_bytes()
    text,_=extract(raw,'application/json');units=[]
    for i,match in enumerate(re.finditer(r'[^\n]+',text)):
        if not match.group().strip():continue
        start=match.start()+len(match.group())-len(match.group().lstrip())
        end=match.end()-len(match.group())+len(match.group().rstrip())
        unit='u'+str(i+1)
        units.append({'unit_id':unit,'locator':'Retained text line '+str(i+1),'text':text[start:end],
            'normative':True,'span':make_span('s.'+unit,ref,raw,text,start,end)})
    with db.transaction() as con:
        import_source(db,con,ref,raw,'application/json',
            'https://apps.sfc.hk/edistributionWeb/gateway/EN/circular/doc?refNo='+ref,AT,authority='RETAINED_PUBLIC_SOURCE')
    slice_text={'24EC50':'Selected control: the compulsory electronic submission route and its transition date. Account for the whole source as context; do not invent duties for optional facilities.',
                '23EC46':'Selected paragraph-10 gift-promotion control, its fee-discount exception and product/product-type connection. Retain surrounding provisions and footnotes as context and unresolved dependencies.'}[ref]
    return {'source_key':'sfc.'+ref.lower()+'.search','authority':'RETAINED_SOURCE','selected_slice':slice_text,
        'units':units,'dependencies':[{'dependency_id':'external-authorities.'+ref.lower(),'source_hash':None}],
        'family_ids':list(DIMENSIONS)}


def main():
    parser=ArgumentParser(description=__doc__);parser.add_argument('--out',required=True)
    parser.add_argument('--allowance',required=True)
    parser.add_argument('--rounds',type=int,default=1)
    parser.add_argument('--max-calls',type=int,default=6)
    parser.add_argument('--min-rounds',type=int,default=1);args=parser.parse_args()
    if not 1<=args.min_rounds<=args.rounds:parser.error('Invalid minimum rounds')
    out=Path(args.out)
    if out.exists():raise ValueError('Use a fresh evidence directory')
    out.mkdir(parents=True)
    reports=[];overall=True
    authorized=loads((ROOT/'docs/implementation/interpretation-round2/master-plan.json').read_bytes())['live_call_allowance']
    for ref in ('24EC50','23EC46'):
        allowance=loads(Path(args.allowance).read_bytes()) if Path(args.allowance).exists() else {'maximum':authorized,'calls':[]}
        if allowance['maximum']!=authorized:raise ValueError('Live ledger ceiling differs from the reviewed plan')
        # Three initial roles, one investigation/refinement, one possible output
        # repair, and one isolated reconstruction require six counted calls.
        if allowance['maximum']-len(allowance['calls'])<args.max_calls:
            reports.append({'circular':ref,'engineering_pass':False,'status':'LIVE_ALLOWANCE_INSUFFICIENT',
                'calls_remaining':allowance['maximum']-len(allowance['calls'])})
            overall=False;break
        directory=out/ref;directory.mkdir()
        db=Database(directory/'work');service=Interpretations(db)
        service.lc.register({'pilot.author':{'token':'public-synthetic-author','roles':['author']}})
        packet=source_packet(db,ref)
        settings=Settings(scheduler='uct' if ref=='23EC46' else 'bfs',max_model_calls=args.max_calls,max_rounds=args.rounds,
                          timeout_seconds=180,deadline_seconds=1200,max_candidates=24)
        (directory/'packet.json').write_bytes(canonical(packet));(directory/'settings.json').write_bytes(canonical(settings.model_dump()))
        run=create_search(service,'pilot.author','pilot.'+ref,packet,settings)
        checker=Comparisons(directory/'java',ROOT/'.localresources/java-toolchain/jdk-17.0.20.1+1',AT)
        provider=CodexProvider(allowance=Allowance(args.allowance,allowance['maximum']))
        engine=Search(service,'pilot.author',run['run_id'],provider,checker)
        report=engine.drive();engine.verify_report();record=service.read('pilot.author',run['run_id'])
        (directory/'investigation.json').write_bytes(canonical(record));(directory/'report.json').write_bytes(canonical(report))
        export_history(db,directory/'history.zip')
        counts,passed=pilot_measurements(engine,report)
        passed=passed and counts['search_rounds']>=args.min_rounds
        reports.append({'circular':ref,'engineering_pass':passed,'counts':counts,'report_hash':digest(report)})
        overall &= passed
        print(ref+': '+str(counts),flush=True)
        if not passed:break
    result={'engineering_pass':overall,'sources':reports,'legal_accuracy_evaluated':False,
            'corpus_status':'DEVELOPMENT_MATERIAL','independent_human_annotations':False,
            'limits':['Same-model fresh contexts are correlated','Source review can overturn candidates',
                      'Finite comparisons do not prove completeness or English fidelity']}
    (out/'result.json').write_bytes(canonical(result))
    if not overall:raise SystemExit(1)


if __name__=='__main__':main()
