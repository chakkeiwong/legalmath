"""Explicit source-reviewed references beyond the bounded heading recognizer."""
from .admissions import review
from .anchors import fields, bind
from .contracts import digest
from .occurrences import uses, target


def admit(graph, assembly, packet):
    fields(packet, {'version','assembly_sha256','review','references'},
           {'version','assembly_sha256','review','references'})
    if packet['version'] not in {'reviewed-references.v1', 'reviewed-references.v2'} or packet['assembly_sha256'] != digest(assembly):
        raise ValueError('Reviewed reference assembly changed')
    review(packet['review'])
    selected = {u['unit']:u for u in assembly['units']}
    raw = {u['id']:u for u in graph['units']}
    discovered = {r['id']:r for r in graph.get('references', [])}
    claimed = set()
    ids, dependencies, edges = set(), [], []
    for row in packet['references']:
        required = {'id','form','source','from_use','language','targets','authority','questions','reason'}
        if packet['version'] == 'reviewed-references.v2':
            required.add('discovery_ids')
        fields(row, required, required)
        if (not row['id'] or row['id'] in ids or row['form'] not in {'named','relative','external','amendment'} or
                not row['reason'] or not row['questions'] or set(row['questions']) - {'Q1','Q2'}):
            raise ValueError('Invalid reviewed reference')
        ids.add(row['id'])
        bind(graph,row['source'])
        if raw[row['source']['unit']]['language'] != row['language']:
            raise ValueError('Reference language differs from source')
        discovery_ids = row.get('discovery_ids', [])
        if (not isinstance(discovery_ids, list) or any(not isinstance(key,str) for key in discovery_ids)
                or len(set(discovery_ids)) != len(discovery_ids)):
            raise ValueError('Distinct discovery identities required')
        for key in discovery_ids:
            proposal = discovered.get(key)
            source = row['source']
            if (proposal is None or proposal['unit'] != source['unit'] or
                    proposal['document'] != source['document'] or proposal['source_sha256'] != source['source_sha256'] or
                    not source['start'] <= proposal['start'] < proposal['end'] <= source['end'] or
                    raw[source['unit']]['raw'][proposal['start']:proposal['end']] != proposal['text']):
                raise ValueError('Reviewed reference does not cover its discovered source')
            for question in row['questions']:
                identity = (key, row['from_use'], question)
                if identity in claimed:
                    raise ValueError('Discovered reference has multiple reviewed replacements')
                claimed.add(identity)
        if not row['targets']:
            raise ValueError('Reviewed reference needs exact targets')
        destinations = []
        for value in row['targets']:
            fields(value, {'source','use','language'}, {'source','use','language'})
            found = target(graph, assembly, {k:value[k] for k in ('source','use')})
            if (raw[value['source']['unit']]['language'] != value['language'] or
                    selected[found['unit']]['role'] != 'OPERATIVE' or
                    not set(row['questions']) <= set(selected[found['unit']]['questions'])):
                raise ValueError('Reference target is not operative in the declared language/question')
            if row['form']=='external' and value['source']['document']==row['source']['document']:
                raise ValueError('External reference requires another document')
            destinations.append(found)
        for question in row['questions']:
            referring = [m for m in uses(graph,assembly,row['source'],question=question) if m['unit']==row['from_use']]
            if len(referring)!=1 or len(uses(graph,assembly,row['authority'],question=question))!=1:
                raise ValueError('Reference source/authority is not an unambiguous selected occurrence')
        identity = 'reviewed-reference:'+row['id']
        dependencies.append({'id':identity,'questions':row['questions'],'status':'RESOLVED',
            'source_use':referring[0],'targets':destinations,'form':row['form'],
            'discovery_ids':discovery_ids,
            'authority':row['authority'],'review':packet['review'],'automatic_discovery':False})
        for destination in destinations:
            edges.append({'id':identity,'from':row['from_use'],'to':destination['unit'],
                'kind':'reference','resolved':True,'authority':row['authority'], 'questions':row['questions']})
    return dependencies, edges
