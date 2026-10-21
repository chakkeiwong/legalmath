"""A finite catalog of unchanged synthesis levels and reviewed missing work."""
from ..bounded_context import require
from ..integration_contract import read_evidence

PROFILE = 'exact-synthesis-catalog.v1'


def metadata(root, reference, input_hash):
    value=read_evidence(reference,root)
    require(value.get('profile')==PROFILE and value.get('input_hash')==input_hash
        and type(value.get('first_level_instructions')) is bool
        and value.get('phases') and value.get('rows'), 'Invalid synthesis catalog','E_INTEGRITY')
    return value


def selected(root, reference, key, input_hash):
    value=metadata(root,reference,input_hash)
    pointer=value['rows'].get(key)
    if pointer is None:
        require(not any(key.rsplit('-',1)[0] == k.rsplit('-',1)[0] for k in value['rows']),
            'New key in a retained synthesis level','E_INTEGRITY')
    return pointer


def load(root, reference, input_hash, *, provider_binding=None, limits=None):
    from . import synthesis_recovery
    value=metadata(root,reference,input_hash); rows={}
    require(len({p['sha256'] for p in value['phases']})==len(value['phases']), 'Duplicate catalog phase')
    for pointer in value['phases']:
        phase=synthesis_recovery.load(root,pointer,input_hash,provider_binding=provider_binding,limits=limits)
        require(phase.get('instruction_profile')==value['instruction_profile'], 'Changed catalog instructions')
        require(not set(rows)&set(phase['rows']), 'Overlapping synthesis levels')
        rows.update({key:pointer for key in phase['rows']})
    require(rows==value['rows'],'Incomplete synthesis catalog census','E_INTEGRITY')
    return value
