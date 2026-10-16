"""Factor repeated reading objects into a complete table in the SAME request."""
from copy import deepcopy
from legalmath.canonical import digest
from legalmath.interpretation.assurance.bounded_context import require


def factor(rows):
    table={};lookup={};assignments=[]
    for row in rows:
        require('origin_reading_refs' not in row,'Reserved table field collides with original')
        projected=deepcopy(row)
        if 'origin_readings' in projected:
            require(isinstance(projected['origin_readings'],list),'Invalid origin reading list')
            refs=[]
            for reading in projected.pop('origin_readings'):
                identity=digest(reading)
                if identity not in lookup:
                    key='reading'+str(len(table))
                    lookup[identity]=key;table[key]=deepcopy(reading)
                key=lookup[identity]
                require(table[key]==reading,'Reading hash collision')
                refs.append(key)
            projected['origin_reading_refs']=refs
        assignments.append(projected)
    result={'assignments':assignments,'origin_reading_table':table,
        'table_instructions':'Each origin_reading_ref refers to the complete original '
            'reading in origin_reading_table in this request. No source reading is omitted '
            'or paraphrased. These readings remain proposals, never source authority.'}
    require(expand(result)==rows,'Dependency table lost original context')
    return result


def expand(value):
    rows=[];used=set()
    for row in value['assignments']:
        restored=deepcopy(row)
        if 'origin_reading_refs' in restored:
            require('origin_readings' not in restored,'Ambiguous origin readings')
            refs=restored.pop('origin_reading_refs')
            require(all(key in value['origin_reading_table'] for key in refs),'Missing original reading')
            used.update(refs)
            restored['origin_readings']=[deepcopy(value['origin_reading_table'][key]) for key in refs]
        rows.append(restored)
    require(used==set(value['origin_reading_table']),'Unassigned origin reading')
    return rows
