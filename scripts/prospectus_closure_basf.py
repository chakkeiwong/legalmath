"""Bounded real BASF scalar/reference consumer; preserves previous attempts."""
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
REL = 'docs/implementation/prospectus-integration-closure/basf-consumer'
REFERENCE_PLAN = 'docs/plans/prospectus-basf-consumer-2026-10-09.md'
PLAN = 'docs/plans/prospectus-basf-scalars-2026-10-09.md'
SCALARS = 'docs/implementation/prospectus-integration-closure/basf-scalars'


def prepared_request(root, graph=None):
    from legalmath.prospectus.successor import basf, jobs, source_graph
    from legalmath.prospectus.successor.admissions import dispositions
    from legalmath.prospectus.successor.contracts import digest, read
    root = Path(root)
    review = read(root/REL/'review.json')
    scalar_review = read(root/SCALARS/'review.json')
    if scalar_review['version'] != 'basf-scalar-source-review.v1':
        raise ValueError('Unsupported BASF scalar source review')
    request = jobs.basf_request(root)
    graph = source_graph.build(request['bundle'],root) if graph is None else graph
    construction = basf.construct(graph,read(root/jobs.BASF))
    if digest(graph)!=review['graph_sha256'] or digest(construction)!=review['construction_sha256']:
        raise ValueError('BASF source review differs from current construction')
    for path,sha in [*review['images'].items(), *scalar_review['images'].items()]:
        if digest((root/path).read_bytes())!=sha:
            raise ValueError('BASF reviewed source image changed')
    baseline = scalar_review['baseline']
    legacy = basf.as_assembly(graph,construction)
    unmapped = [p for u in legacy['units'] for p in u.get('character_map', [])
                if p['operation'] == 'UnmappedSubstitution']
    if (construction != read(root/baseline['construction_path']) or
            digest(legacy) != baseline['legacy_assembly_sha256'] or
            len(unmapped) != baseline['unmapped_substitutions'] or
            len(construction['remaining_brackets']) != baseline['retained_markers'] or
            len(construction['interval_accounting']['unresolved']) != baseline['unresolved_intervals']):
        raise ValueError('BASF scalar baseline or retained obligations changed')
    request['construction']['scalar_admission'] = scalar_review['admission']
    assembly=basf.as_assembly(graph,construction,scalar_review['admission'])
    request['reviewed_dispositions']={'version':'reviewed-dispositions.v1',
        'assembly_sha256':digest(assembly),'review':review['review'],'units':review['units']}
    assembly=dispositions(graph,assembly,request['reviewed_dispositions'])
    request['reference_admission']={'version':'reviewed-references.v2',
        'assembly_sha256':digest(assembly),'review':review['review'],'references':review['references']}
    return request


def check_report(report,request):
    from legalmath.prospectus.successor.contracts import digest
    from legalmath.prospectus.successor.occurrences import uses
    graph, construction, assembly = report['source_map'], report['selected_contract'], report['assembly']
    admission = request['construction']['scalar_admission']
    if (digest(graph) != admission['graph_sha256'] or digest(construction) != admission['construction_sha256'] or
            assembly.get('scalar_admission') != admission or assembly['continuous_text'] != construction['candidate_text']):
        raise ValueError('BASF scalar consumer changed its reviewed construction')
    scalar_pieces = [(u,p) for u in assembly['units'] for p in u.get('character_map', [])
                     if 'scalar_operation_sha256' in p]
    if (len(admission['bindings']) != 6 or len(scalar_pieces) != 6 or
            any(p['operation'] == 'UnmappedSubstitution' for u in assembly['units'] for p in u.get('character_map', []))):
        raise ValueError('BASF scalar consumer lacks complete mapped substitutions')
    operations = {digest(o):o for o in construction['operations']}
    scalar_uses = []
    for row in admission['bindings']:
        pieces = [(u,p) for u,p in scalar_pieces if p['scalar_operation_sha256'] == row['operation_sha256']]
        operation = operations[row['operation_sha256']]
        if len(pieces) != 1:
            raise ValueError('BASF scalar output operation is missing or repeated')
        unit,piece = pieces[0]
        authority = row.get('selection_authority')
        if (unit['unit'] != operation['source_units'][0] or piece['source'] != row['source'] or
                piece['operation'] != ('Text' if row['kind'] == 'LITERAL_SELECTION' else 'Field') or
                piece.get('selection_authority') != authority or
                unit['text'][piece['start']:piece['end']] != operation['new']):
            raise ValueError('BASF scalar output or provenance changed')
        selected = {'units':[unit]}
        mapped = uses(graph, selected, row['source'], roles=(unit['role'],))
        if len(mapped) != 1 or (mapped[0]['start'],mapped[0]['end']) != (piece['start'],piece['end']):
            raise ValueError('BASF scalar did not reach its exact output use')
        if authority is not None and uses(graph, selected, authority, roles=(unit['role'],)):
            raise ValueError('BASF selection authority masquerades as copied literal')
        scalar_uses.append({'kind':row['kind'], 'operation_sha256':row['operation_sha256'],
                            'output_use':mapped[0], 'selection_authority':authority})
    markers = len(construction['remaining_brackets'])
    intervals = len(construction['interval_accounting']['unresolved'])
    if markers != 15 or intervals != 537:
        raise ValueError('BASF scalar repair changed the retained obligation inventory')
    rows={d['id']:d for d in report['dependencies']}
    for reference in request['reference_admission']['references']:
        dependency=rows['reviewed-reference:'+reference['id']]
        if dependency['status']!='RESOLVED' or len(dependency['targets'])!=len(reference['targets']):
            raise ValueError('Real BASF target occurrences did not resolve')
        for proposal in reference['discovery_ids']:
            if proposal+'@'+reference['from_use'] in rows:
                raise ValueError('Reviewed BASF reference left its original proposal unresolved')
    if ([report['questions'][q]['status'] for q in ('Q1','Q2','Q3')] != ['UNKNOWN','UNKNOWN','PARTIAL']
            or report['mode']!='ASSISTED'):
        raise ValueError('Reference repair promoted incomplete BASF meaning')
    return {'reviewed_references':3,'target_occurrences':[len(r['targets']) for r in request['reference_admission']['references']],
            'mapped_scalar_operations':len(scalar_uses), 'scalar_uses':scalar_uses,
            'construction_sha256':digest(construction), 'retained_markers':markers, 'unresolved_intervals':intervals,
            'remaining_brackets_sha256':digest(construction['remaining_brackets']),
            'interval_accounting_sha256':digest(construction['interval_accounting']),
            'questions':{q:report['questions'][q]['status'] for q in ('Q1','Q2','Q3')},
            'mode':report['mode'],'independent_legal_review':False,
            'remaining_reference_dependencies':sum(d['status']=='UNRESOLVED' for d in report['dependencies'])}


def main():
    os.environ['CUDA_VISIBLE_DEVICES']='-1'
    python=ROOT/'.venv/bin/python'
    if Path(sys.executable).absolute()!=python.absolute():
        os.execv(str(python),[str(python),'-m','scripts.prospectus_closure_basf',*sys.argv[1:]])
    sys.path.insert(0,str(ROOT/'src'))
    from legalmath.prospectus.successor import service
    from legalmath.prospectus.successor.contracts import digest,read,write
    folder=ROOT/REL/f'attempt-{len(list((ROOT/REL).glob("attempt-*")))+1:03d}'
    folder.mkdir()
    scalar_review=read(ROOT/SCALARS/'review.json')
    paths=[ROOT/PLAN,ROOT/REFERENCE_PLAN,ROOT/REL/'review.json',ROOT/SCALARS/'review.json',
           ROOT/scalar_review['baseline']['construction_path'],ROOT/REL/'fifteen-fields.json',ROOT/REL/'source-obligations.json',
           Path(__file__),*sorted((ROOT/'src/legalmath/prospectus/successor').glob('*.py'))]
    methods={str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in paths}
    tick=time.monotonic()
    write(folder/'started.json',{'command':['python3','-m','scripts.prospectus_closure_basf'],
        'plan':PLAN,'method':methods,'cpu_gpu':'CPU; CUDA_VISIBLE_DEVICES=-1','timeout_seconds':600,
        'evidence_limit_bytes':20_000_000,'metadata_reserve_bytes':1_048_576})
    try:
        request=prepared_request(ROOT)
        write(folder/'request.json',request)
        report=service.assess(request,ROOT)
        outcome=check_report(report,request)
        write(folder/'scalar-evidence.json',{'review_sha256':digest((ROOT/SCALARS/'review.json').read_bytes()),
            'baseline':scalar_review['baseline'], 'outcome':outcome,
            'scope':'Exact development-reviewed provenance; legal meaning remains partial'})
        write(folder/'consumer.json',{'outcome':outcome,'dependencies':report['dependencies'],
            'report_sha256':digest(report),'assembly_sha256':digest(report['assembly'])})
        if methods!={str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in paths}:
            raise ValueError('BASF consumer method changed during execution')
        if time.monotonic()-tick>600:
            raise TimeoutError('BASF consumer exceeded its bound')
        size=sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())
        if size+1_048_576>20_000_000:
            raise ValueError('BASF consumer exceeded its evidence budget')
        result={'status':'PASS','outcome':outcome,'evidence_payload_bytes':size,
                'evidence_limit_bytes':20_000_000,'metadata_reserve_bytes':1_048_576}
    except Exception as exc:
        result={'status':'FAIL','error':type(exc).__name__+': '+str(exc)}
    result.update(plan=PLAN,command=['python3','-m','scripts.prospectus_closure_basf'],
        method=methods,git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        environment={'python':sys.executable,'version':sys.version,'source':str(ROOT/'src')},
        cpu_gpu='CPU; CUDA_VISIBLE_DEVICES=-1',seeds='N/A; deterministic source/reference controls',
        wall_seconds=time.monotonic()-tick)
    write(folder/'result.json',result)
    write(folder/'manifest.json',{'files':{str(p.relative_to(folder)):digest(p.read_bytes()) for p in folder.rglob('*') if p.is_file()}})
    print({'directory':str(folder.relative_to(ROOT)), 'status':result['status'],'error':result.get('error')})
    if result['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':
    main()
