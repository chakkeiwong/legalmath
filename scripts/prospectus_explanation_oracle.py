"""Independent bitset checks; no production predicate/explanation evaluator."""
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import json

from legalmath.prospectus.reasoning_certificates import expectation, _truth_table


def require(value, message):
    if not value:
        raise ValueError(message)


def identity(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def check(expression, observations, result, *, engine='finite', active=True):
    expected = expectation(expression, observations)
    common = {'version':'subset-minimal.v1','scope':'ONE_BASIS_SUPPLIED_BOOLEAN_CONSEQUENCE',
        'claim':'SUBSET_MINIMAL_NOT_MINIMUM_CARDINALITY','order':'SORTED_FACT_NAME_DELETION',
        'limits':{'max_facts':12,'max_nodes':4096,'max_depth':24},
        'expression_sha256':identity(expression),'observations_sha256':identity(observations),
        'counterexample_scope':'BOOLEAN_ASSIGNMENTS_NOT_VERIFIED_EVENTS'}
    reason = ('INACTIVE_AUTHORITY' if not active else 'UNSUPPORTED_ENGINE' if engine != 'finite' else
              'DOMAIN_LIMIT' if expected.get('reason') == 'DOMAIN_LIMIT' else
              expected['status'] if expected['status'] in {'UNKNOWN','CONFLICT'} else None)
    if reason:
        require(result == {**common,'status':'NOT_AVAILABLE','reason':reason},'Incorrect unavailable explanation')
        return {'status':'NOT_AVAILABLE','reason':reason}
    require(set(result) == set(common)|{'status','conclusion','literals','deletion_counterexamples'},
            'Unexpected explanation fields')
    require(all(result[k] == v for k,v in common.items()),'Wrong explanation identity or scope')
    require(result['status']=='EXPLAINED' and result['conclusion']==expected['status'],'Wrong explanation conclusion')
    literals = result['literals']
    require(isinstance(literals,dict) and all(n in expected['support'] and type(v) is bool
        and type(observations.get(n)) is bool and observations[n] == v for n,v in literals.items()),
        'Invented explanation literal')
    require(expectation(expression,literals)['status'] == expected['status'],'Insufficient explanation')
    witnesses = result['deletion_counterexamples']
    require(isinstance(witnesses,dict) and set(witnesses)==set(literals),'Missing necessity witnesses')
    support, table, _ = _truth_table(json.dumps(expression,sort_keys=True,separators=(',',':'),allow_nan=False))
    for name, world in witnesses.items():
        reduced = {n:v for n,v in literals.items() if n != name}
        require(expectation(expression,reduced)['status'] != expected['status'],'Nonminimal explanation')
        require(isinstance(world,dict) and set(world)==set(support) and all(type(v) is bool for v in world.values()),
                'Malformed necessity witness')
        require(all(world[n] == v for n,v in reduced.items()),'Witness contradicts retained literal')
        index = sum(1 << i for i,n in enumerate(support) if world[n])
        require(bool(table & (1 << index)) != (expected['status']=='YES'),'Witness does not reverse conclusion')
    return {'status':'VERIFIED','conclusion':expected['status'],'retained':len(literals),'necessary':len(witnesses)}


def at(value):
    return datetime.fromisoformat(value.replace('Z','+00:00'))


def active(row,bundle,observation=False):
    effective, known = at(bundle['effective_at']), at(bundle['known_at'])
    return (at(row['valid_from']) <= effective and (row.get('valid_until') is None or effective < at(row['valid_until']))
        and at(row['known_from']) <= known and (row.get('known_until') is None or known < at(row['known_until']))
        and (not observation or at(row['observed_at']) <= known))


def anchor(graph, source):
    units = [u for u in graph['units'] if u['id']==source['unit']]
    require(len(units)==1,'Ambiguous source')
    u=units[0]
    require(u['visible'] and u['document']==source['document'] and u['source_sha256']==source['source_sha256']
        and u['raw'][source['start']:source['end']] == source['quote'],'Source mismatch')
    bound={**deepcopy(source),'page':u['page'],'bbox':u.get('bbox')}
    if u.get('geometry_issues'):
        bound.update(geometry_issues=u['geometry_issues'],image_sha256=u.get('image_sha256'))
    return bound


def check_row(row, data, bundle, graph, *, engine='finite'):
    basis=next(b for b in data['law_bases'] if b['id']==row['basis'])
    explanation=row['explanation']
    core={k:v for k,v in explanation.items() if k not in {'basis','authority_source','premise_support'}}
    result=check(row['expression'],row['premises'],core,engine=engine,active=active(basis,bundle))
    require(explanation['basis']==basis['id'] and explanation['authority_source']==anchor(graph,basis['source']),
            'Wrong explanation authority')
    expected={}
    for name,value in core.get('literals',{}).items():
        supports=[]
        for f in data['facts']:
            if f['basis_id']==basis['id'] and f['name']==name and active(f,bundle,True):
                require(f['value'] is value,'Contradictory fact became an explanation')
                supports.append({'kind':'OBSERVATION','observation':deepcopy(f),'source':anchor(graph,f['source'])})
        for key,kind in [('calculations','RATIO'),('calendar_calculations','CALENDAR')]:
            for c in row.get(key,[]):
                if c['name']==name and c['status'] in {'YES','NO'}:
                    require((c['status']=='YES') is value,'Wrong calculated literal')
                    supports.append({'kind':kind,'calculation':deepcopy(c)})
        require(supports,'Unsupported retained literal')
        expected[name]=supports
    require(explanation['premise_support']==expected,'Wrong explanation premise sources')
    return {**result,'source_support_checked':True,'basis':row['basis']}
