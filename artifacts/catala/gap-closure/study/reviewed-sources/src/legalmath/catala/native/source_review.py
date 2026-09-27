"""Exact retained sources, provisional references and heldout admission checks."""
from ...canonical import digest, raw_digest
from .contracts import fail, validate_task
from .package import source_check


def validate_packet(packet, source_bytes):
    if packet.get('record_type')!='CatalaSourceReviewPacket' or not packet.get('corpus'):fail('E_SCHEMA')
    blobs={raw_digest(v):v for v in source_bytes}
    if sorted(blobs)!=packet['source_hashes']:fail('E_HASH_MISMATCH')
    ids=set()
    for row in packet['corpus']:
        task=validate_task(row['task']);key=task['task_id']
        if key in ids:fail('E_DUPLICATE_ID')
        ids.add(key);source_check(task,blobs)
        if not row['cases'] or row['source_family'] not in blobs:fail('E_REFERENCE')
        w=row['witness']
        if w['selected']==w['rival'] or set(w['inputs'])!={f['name'] for f in task['inputs']}:fail('E_REFERENCE','Rival needs a distinguishing input')
        if row['adjudication']['status'] not in ('PENDING_HUMAN','ADJUDICATED'):fail('E_SCHEMA')
    return {'packet_hash':digest(packet),'tasks':len(ids),'source_families':len({r['lineage_family'] for r in packet['corpus']}),
            'adjudication':'PENDING' if any(r['adjudication']['status']!='ADJUDICATED' for r in packet['corpus']) else 'REQUIRES_EXTERNAL_ATTESTATION'}


def admit_heldout(packet, training_families, attestations):
    """Attestations must come from the trusted study owner, outside generation."""
    reasons=[]
    for row in packet['corpus']:
        key=row['task']['task_id'];a=attestations.get(key)
        if row['lineage_family'] in training_families or row['source_family'] in training_families:reasons.append(key+':SOURCE_FAMILY_EXPOSED')
        if (not a or not a.get('independent_human') or not a.get('reviewer') or a['reviewer']==row['reference_author']
                or a.get('reference_hash')!=digest({'task':row['task'],'cases':row['cases'],'witness':row['witness']})
                or a.get('verdict')!='ACCEPT'):reasons.append(key+':UNADJUDICATED_REFERENCE')
    return {'admitted':not reasons,'reasons':reasons,'packet_hash':digest(packet)}
