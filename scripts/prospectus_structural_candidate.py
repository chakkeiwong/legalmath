"""Prepare structural-context candidates; no candidate execution here."""
from copy import deepcopy
import ast
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts import prospectus_selected_role_review as prior
from legalmath.prospectus.successor.contracts import digest
AUTH=prior.AUTH;BASE=prior.BASE
PREP=AUTH/'reviews/structural-context-295'
HERE=AUTH/'attempts/basf-references/attempt-036'
PLAN='docs/plans/prospectus-structural-integration-2026-10-19.md'
read,save,sha,rel=prior.read,prior.save,prior.sha,prior.rel
PREFIX='src/legalmath/prospectus/successor/'


def replace(text,old,new):
    assert text.count(old)==1,(old,text.count(old))
    return text.replace(old,new)


def candidates():
    base=read(BASE/'complete-products.json.gz');g=base['P1']['payload']['graph'];a=base['P2']['payload']['assembly']
    review=read(prior.HERE/'source-review.json');packet=read(prior.HERE/'source-packet.json.gz')
    selected={u['unit']:u for u in a['units']};decisions=[]
    for row in review['decisions']:
        assert selected[row['unit']]['role']=='UNKNOWN'
        decisions.append({'unit':row['unit'],'before':deepcopy(selected[row['unit']]),'reason':row['basis'],
            'source_segments':row['source_segments'],'image':{'path':row['image']['path'],'sha256':row['image']['sha256']}})
    ids={r['unit'] for r in decisions};assert len(ids)==44
    migrated=deepcopy(a);by_id={u['unit']:u for u in migrated['units']}
    for row in decisions:by_id[row['unit']].update(role='HEADER',reason=row['reason'])
    migrated['unresolved']=[u['unit'] for u in migrated['units'] if u['role']=='UNKNOWN']
    refs=base['P3']['payload']['interpretation_input']['reference_admission']['references']
    affected=[r for r in refs if ids.intersection(t['use'] for t in r['targets'])]
    assert len(affected)==4
    spec={'profile':'basf-selected-structural-roles.v1','graph_sha256':digest(g),
        'baseline_assembly_sha256':digest(a),'migrated_body_sha256':digest(migrated),
        'decisions':decisions,'affected_references':affected,
        'source_review_sha256':sha(prior.HERE/'source-review.json'),
        'protected_unknown_ids':packet['protected_unknown_ids'],
        'definition_profiles':{kind:digest(read(ROOT/PREFIX/('definition_'+kind+'_spec.json.gz'))) for kind in ('scopes','applications')}}
    profile=digest(spec);migrated['structural_role_review']={'profile':spec['profile'],'profile_sha256':profile}
    assembly_hash=digest(migrated)
    result={'structural_roles_spec.json':json.dumps(spec,ensure_ascii=False,indent=2)+'\n'}
    structural=(ROOT/PREFIX/'structural_roles.py').read_text()
    structural=replace(structural,'PROFILE_SHA256 = None','PROFILE_SHA256 = '+repr(profile))
    structural=replace(structural,'ASSEMBLY_SHA256 = None','ASSEMBLY_SHA256 = '+repr(assembly_hash))
    result['structural_roles.py']=structural
    text=(ROOT/PREFIX/'reviewed_references.py').read_text()
    text=replace(text,"    fields(packet, {'version','assembly_sha256','review','references'},\n           {'version','assembly_sha256','review','references'})",
        "    required={'version','assembly_sha256','review','references'}\n    structural=set()\n    if packet['version']=='reviewed-references.v4':\n        required.add('structural_role_review')\n        from .structural_roles import reference_context\n        structural=reference_context(graph,assembly,packet)\n    fields(packet,required,required)")
    text=text.replace("'reviewed-references.v3'}","'reviewed-references.v3', 'reviewed-references.v4'}")
    text=replace(text,'        destinations = []\n        unknown_targets = []','        destinations = []\n        contexts = []\n        seen_targets = set()\n        unknown_targets = []')
    text=replace(text,"            found = target(graph, assembly, {k:value[k] for k in ('source','use')}, _lookup=_lookup)",
        "            key=digest(value)\n            if packet['version']=='reviewed-references.v4' and key in seen_targets:\n                raise ValueError('Duplicate reviewed target')\n            seen_targets.add(key)\n            context=value['use'] in structural\n            if context:\n                matches=locate(graph,assembly,value['source'],roles=('HEADER',))\n                matches=[m for m in matches if m['unit']==value['use']]\n                if len(matches)!=1:\n                    raise ValueError('Structural context is not an exact source occurrence')\n                found=matches[0]\n            else:\n                found = target(graph, assembly, {k:value[k] for k in ('source','use')}, _lookup=_lookup)")
    text=replace(text,"selected[found['unit']]['role'] not in (('OPERATIVE', 'UNKNOWN') if packet['version'] == 'reviewed-references.v3' else ('OPERATIVE',))",
        "selected[found['unit']]['role'] not in (('HEADER',) if context else (('OPERATIVE', 'UNKNOWN') if packet['version'] in {'reviewed-references.v3','reviewed-references.v4'} else ('OPERATIVE',)))")
    text=replace(text,'            destinations.append(found)','            (contexts if context else destinations).append(found)')
    text=replace(text,"        for question in row['questions']:\n            referring",
        "        if not destinations:\n            raise ValueError('Reviewed reference requires a substantive target')\n        for question in row['questions']:\n            referring")
    text=replace(text,"            'discovery_ids':discovery_ids,",
        "            'discovery_ids':discovery_ids,\n            **({'structural_targets':contexts,'structural_role_review':packet['structural_role_review']} if contexts else {}),")
    text=replace(text,"packet['version'] == 'reviewed-references.v3':","packet['version'] in {'reviewed-references.v3','reviewed-references.v4'}:")
    result['reviewed_references.py']=text
    for name in ('basf_substitution_references.py','basf_financial_references.py','basf_internal_references.py'):
        text=(ROOT/PREFIX/name).read_text()
        text=replace(text,'def check(graph, assembly, packet):',
            'def check(graph, assembly, packet):\n    from .structural_roles import legacy_view, reference_report\n    original=legacy_view(graph,assembly)\n    return reference_report(_check(graph,original,packet),assembly)\n\n\ndef _check(graph, assembly, packet):')
        result[name]=text
    for kind in ('scopes','applications'):
        name='definition_'+kind+'.py';text=(ROOT/PREFIX/name).read_text()
        text=replace(text,'def specification():','def specification(structural=False):\n    if structural:\n        from .structural_roles import definition_specification\n        return definition_specification('+repr(kind)+')')
        if kind=='scopes':
            text=replace(text,"def packet():\n    return {'profile': specification()['profile'], 'profile_sha256': PROFILE_SHA256}",
                "def packet(structural=False):\n    spec=specification(structural)\n    return {'profile':spec['profile'],'profile_sha256':digest(spec)}")
            text=replace(text,"    spec = specification()\n    if {k:value[k]",
                "    structural=value['profile'].endswith('.structural-v1')\n    spec = specification(structural)\n    profile_hash=digest(spec)\n    if {k:value[k]")
            text=replace(text,"{'profile': spec['profile'], 'profile_sha256': PROFILE_SHA256}","{'profile': spec['profile'], 'profile_sha256': profile_hash}")
            text=replace(text,"    assembly = selected['assembly']",
                "    assembly = selected['assembly']\n    if structural:\n        from .structural_roles import verify\n        verify(graph,assembly,request.get('structural_roles'))")
            text=replace(text,"'profile_sha256':PROFILE_SHA256,","'profile_sha256':profile_hash,")
        else:
            text=replace(text,"def packet():\n    return {'profile':specification()['profile'],'profile_sha256':PROFILE_SHA256}",
                "def packet(structural=False):\n    spec=specification(structural)\n    return {'profile':spec['profile'],'profile_sha256':digest(spec)}")
            text=replace(text,"    spec=specification()\n    require(isinstance(request,dict) and request==packet(),",
                "    structural=isinstance(request,dict) and str(request.get('profile','')).endswith('.structural-v1')\n    spec=specification(structural)\n    require(isinstance(request,dict) and request==packet(structural),")
            text=replace(text,"'profile_sha256':PROFILE_SHA256,","'profile_sha256':digest(spec),")
        result[name]=text
    name='contracts.py';text=(ROOT/PREFIX/name).read_text();text=replace(text,'"statutory_references", "definition_sources"},','"statutory_references", "definition_sources", "structural_roles"},');result[name]=text
    name='service.py';text=(ROOT/PREFIX/name).read_text()
    text=replace(text,'    result = {"assembly": assembly, "selected_contract": construction}',
        "    if 'structural_roles' in request:\n        from .structural_roles import apply\n        assembly=apply(graph,assembly,request['structural_roles'])\n    result = {'assembly': assembly, 'selected_contract': construction}")
    text=replace(text,'    assembly = selected["assembly"]\n    from . import definition_scopes',
        "    assembly = selected['assembly']\n    from .structural_roles import verify as verify_roles\n    verify_roles(graph,assembly,request.get('structural_roles'))\n    from . import definition_scopes")
    text=replace(text,"    interpretation_input = {**request, **(semantic.get('interpretation_input') or {})}",
        "    from .structural_roles import verify as verify_roles\n    verify_roles(graph,selected['assembly'],request.get('structural_roles'))\n    interpretation_input = {**request, **(semantic.get('interpretation_input') or {})}")
    result[name]=text
    changes=[]
    for name,text in result.items():
        if name.endswith('.py'):ast.parse(text)
        destination=PREP/'candidate'/name;destination.parent.mkdir(parents=True,exist_ok=True)
        with destination.open('x') as f:f.write(text)
        target=ROOT/PREFIX/name
        if target.exists():
            backup=PREP/'baseline'/name;backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(target.read_bytes())
        changes.append({'target':PREFIX+name,'candidate':rel(destination),
            'before_sha256':sha(target) if target.exists() else None,'after_sha256':sha(destination)})
    save(PREP/'candidate-manifest.json',{'files':changes,'profile_sha256':profile,'assembly_sha256':assembly_hash})
    return {'status':'PASS','candidate_files':len(changes),'profile_sha256':profile,'assembly_sha256':assembly_hash,'candidate_evaluated':False}

if __name__=='__main__':print(json.dumps(candidates()))
