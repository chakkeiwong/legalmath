"""Exact finite structural roles; source context never becomes an obligation."""
from copy import deepcopy
import json
from pathlib import Path
from .contracts import digest

# Registered by the source-profile preparation before any trial. The body hash
# excludes the review marker, so the profile never hashes itself.
PROFILE_SHA256 = 'e116f4dcf6713c030ccbc0c186fd0bbe1e6b2b65fd0f9ebfa558147998a2f4e8'
ASSEMBLY_SHA256 = 'f67049e7bf8e36a181f2ea57558b6993dad57a65cc0ca885f963d89cd145cb3b'


def specification():
    folder=Path(__file__).parent
    spec=json.loads((folder/'structural_roles_spec.json').read_text())
    if PROFILE_SHA256 is None or digest(spec)!=PROFILE_SHA256:
        raise ValueError('Structural role registered profile changed')
    return spec


def packet():
    spec=specification()
    return {'profile':spec['profile'],'profile_sha256':digest(spec)}


def apply(graph,assembly,request):
    spec=specification()
    if request!=packet() or digest(graph)!=spec['graph_sha256'] or digest(assembly)!=spec['baseline_assembly_sha256']:
        raise ValueError('Structural role source or baseline differs from exact review')
    result=deepcopy(assembly)
    units={u['unit']:u for u in result['units']}
    for row in spec['decisions']:
        if units.get(row['unit'])!=row['before']:
            raise ValueError('Structural role original occurrence changed')
        units[row['unit']].update(role='HEADER',reason=row['reason'])
    result['unresolved']=[u['unit'] for u in result['units'] if u['role']=='UNKNOWN']
    if digest(result)!=spec['migrated_body_sha256']:
        raise ValueError('Structural role migration differs from exact reviewed delta')
    result['structural_role_review']=packet()
    if digest(result)!=ASSEMBLY_SHA256:
        raise ValueError('Structural role registered assembly changed')
    return result


def legacy_view(graph,assembly):
    """Restore only the registered roles for existing source-extent validators."""
    if 'structural_role_review' not in assembly:
        return assembly
    spec=specification()
    if assembly['structural_role_review']!=packet() or digest(graph)!=spec['graph_sha256'] or digest(assembly)!=ASSEMBLY_SHA256:
        raise ValueError('Structural role review or complete selected assembly changed')
    originals={r['unit']:r['before'] for r in spec['decisions']}
    result={k:v for k,v in assembly.items() if k!='structural_role_review'}
    result['units']=[deepcopy(originals[u['unit']]) if u['unit'] in originals else u for u in assembly['units']]
    result['unresolved']=[u['unit'] for u in result['units'] if u['role']=='UNKNOWN']
    if digest(result)!=spec['baseline_assembly_sha256']:
        raise ValueError('Structural role reconstruction changed nonrole source content')
    return result


def verify(graph,assembly,request):
    if request is None:
        if 'structural_role_review' in assembly:
            raise ValueError('Structural role review has no request')
        return None
    if request!=packet() or assembly.get('structural_role_review')!=request:
        raise ValueError('Structural role request differs from registered selection')
    legacy_view(graph,assembly)
    return specification()


def reference_report(report,assembly):
    if report is None or 'structural_role_review' not in assembly:
        return report
    ids={r['unit'] for r in specification()['decisions']}
    targets={t['use'] for r in report['references'] for t in r['targets']}
    result=deepcopy(report)
    result['unknown_target_uses']=[u for u in result.get('unknown_target_uses',[]) if u not in ids]
    result['structural_target_uses']=sorted(ids&targets)
    result['structural_role_review']=packet()
    return result


def reference_context(graph,assembly,reference_packet):
    """Validate an exact context profile; never admit arbitrary HEADER targets."""
    if reference_packet.get('structural_role_review')!=packet():
        raise ValueError('Structural reference requires the registered role review')
    legacy_view(graph,assembly)
    spec=specification()
    structural={r['unit'] for r in spec['decisions']}
    registered={r['id']:r for r in spec['affected_references']}
    for row in reference_packet['references']:
        if row['id'] not in registered and not structural.intersection(t['use'] for t in row['targets']):
            continue
        expected=registered.get(row['id'])
        if expected is None or {k:v for k,v in row.items() if k!='reason'}!={k:v for k,v in expected.items() if k!='reason'}:
            raise ValueError('Structural reference requires its complete registered target context')
    return structural


def definition_specification(kind):
    """An explicit alternate profile; all original source readings are retained."""
    import gzip
    if kind not in ('scopes','applications'):
        raise ValueError('Unknown structural definition profile')
    spec=specification()
    value=json.loads(gzip.decompress(Path(__file__).with_name('definition_'+kind+'_spec.json.gz').read_bytes()))
    if digest(value)!=spec['definition_profiles'][kind]:
        raise ValueError('Structural definition baseline profile changed')
    if value['bindings']['assembly_sha256']!=spec['baseline_assembly_sha256']:
        raise ValueError('Structural definition baseline selection differs')
    value['bindings']['assembly_sha256']=ASSEMBLY_SHA256
    value['profile']+='.structural-v1'
    return value
