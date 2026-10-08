"""Resource preflight, kept separate from committed translation records."""
from ..canonical import digest
from ..errors import LegalMathError
from .model import validate,inner


def preflight(model):
    """Inspect native expansion without launching a compiler or changing limits.

    A passing report describes the static envelope, not compilation success or
    runtime capacity. Existing translation payloads and hashes remain unchanged.
    """
    from . import catala,ruleir
    from .structured import Layout
    from .catala_structured import Compiler
    m,types=validate(model)
    result={'record_type':'CatalaResourceReport','version':'1','model_hash':digest(m),
            'dimensions':{},'issues':[]}

    def measure(name,value,limit,minimum=0):
        ok=minimum<=value<=limit
        result['dimensions'][name]={'actual':value,'minimum':minimum,'maximum':limit,'within_limit':ok}
        if not ok: result['issues'].append({'dimension':name,'reason':'E_RESOURCE_LIMIT','actual':value,'minimum':minimum,'maximum':limit})

    if m['version']=='1' and ruleir.capabilities(m)['supported']:
        result.update(route='scalar-compatibility',supported=True,
                      note='Native interface limits do not apply to this scalar compatibility route.')
        return result
    result['route']='native'
    measure('inputs',len(m['facts']),40,1);measure('outputs',len(m['rules']),40,1)
    packet=m['review']['packet']
    if packet is None: result['issues'].append({'dimension':'source_packet','reason':'E_REFERENCE'})
    else: measure('source_units',len(packet['units']),100,1)
    try:
        if m['version']=='2':
            layout=Layout(m,types,enforce_type_limit=False)
            definitions=layout.types
            roots=list(layout.boxes.values())
            measure('expanded_fields',max(layout.sizes.values(),default=0),10000)
        else:
            definitions=m['types']
            roots=[f['type'] for f in m['facts']]+[r['type'] for r in m['rules']]
        measure('generated_types',len(definitions),30)
        defs={d['name']:d for d in definitions};depths={}

        def depth(typ):
            if typ in depths: return depths[typ]
            child=inner(typ,'list') or inner(typ,'optional')
            if child is not None: value=1+depth(child)
            elif typ in defs:
                d=defs[typ];children=[f['type'] for f in d['fields']]+[c['type'] for c in d['cases'] if c['type']]
                value=1+max((depth(c) for c in children),default=-1)
            else: value=0
            depths[typ]=value
            return value

        measure('generated_type_depth',max((depth(t) for t in [*defs,*roots]),default=0),12)
        if not result['issues']:
            if m['version']=='2':
                source=Compiler(m,types).source()
                measure('candidate_source_bytes',len(source.encode()),64000)
            else:
                lowered=catala.lower(m)
                measure('candidate_source_bytes',len(lowered['candidate']['source'].encode()),64000)
    except LegalMathError as exc:
        result['issues'].append({'dimension':'generated_interface','reason':exc.code,'details':exc.details})
    result['supported']=not result['issues']
    result['note']='Static resource envelope only; compiler and runtime limits still apply.'
    return result
