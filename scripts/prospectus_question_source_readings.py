"""Retain source reading material for every unmatched audit identifier."""
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT)]
from scripts import prospectus_question_scope_repair as audit


def main():
    started=time.monotonic()
    audit.frozen()
    p=audit.read(audit.prior.HERE/'complete-products.json.gz')
    semantic=p['P3']['payload']
    nodes={r['id']:(i,r) for i,r in enumerate(semantic['clauses']['nodes'])}
    units={r['unit']:(i,r) for i,r in enumerate(p['P2']['payload']['assembly']['units'])}
    raw={r['id']:(i,r) for i,r in enumerate(p['P1']['payload']['graph']['units'])}
    from legalmath.prospectus.successor.occurrences import segments
    raw_lookup={k:v[1] for k,v in raw.items()}
    def source(node):
        result=[]
        for identity in node['units']:
            index,unit=units[identity]
            result.append({'assembly_index':index,'assembly':unit,
                           'exact_segments':segments(p['P1']['payload']['graph'],unit,_raw=raw_lookup)})
        return result
    rows=[]
    for item in audit.read(audit.HERE/'unmatched.json.gz'):
        identity=item['id']
        if identity.startswith('Missing reference target: '):
            target=identity.removeprefix('Missing reference target: ')
            edges=[{'index':i,'edge':edge} for i,edge in enumerate(semantic['clauses']['edges'])
                   if edge['to']==target]
            assert edges and target not in nodes
            node_ids=sorted({e['edge']['from'] for e in edges})
            kind='ABSENT_APPLICATION_TARGET'
        elif identity.startswith('Unresolved condition/exception: ') and identity.endswith(': OPEN_PREMISES'):
            node_ids=[identity.removeprefix('Unresolved condition/exception: ').removesuffix(': OPEN_PREMISES')]
            assert node_ids[0] in nodes
            edges=[]
            kind='CONDITIONAL_TRIGGER_OR_EXCEPTION'
        else:
            raise ValueError('Unreviewed identifier: '+identity)
        rows.append({'id':identity,'kind':kind,'edges':edges,
            'nodes':[{'index':nodes[key][0],'node':nodes[key][1],'sources':source(nodes[key][1])} for key in node_ids]})
    assert len(rows)==32
    selected_ids={u['unit'] for piece in semantic['definition_sources']['source_pieces'] for u in piece.get('assembly_uses',[])}
    selected_unknown=[{'index':i,'unit':u,'exact_segments':segments(p['P1']['payload']['graph'],u,_raw=raw_lookup)}
        for i,u in enumerate(p['P2']['payload']['assembly']['units'])
        if u['unit'] in selected_ids and u['role']=='UNKNOWN']
    missing=[{'index':i,'piece':piece} for i,piece in enumerate(semantic['definition_sources']['source_pieces'])
        if piece['kind']=='EXACT_SOURCE_COPY' and not piece['assembly_uses']]
    whitespace=[{'index':i,'unit':u} for i,u in enumerate(p['P2']['payload']['assembly']['units'])
                if u['unit'] in semantic['clauses']['uncovered_units'] and not u['text'].strip()]
    audit.save(audit.HERE/'exceptional-source-readings.json.gz',{'unmatched_resolved_to_sources':rows,
        'selected_unknown_units':selected_unknown,'missing_selected_occurrences':missing,
        'uncovered_whitespace':whitespace,'no_legal_relevance_decisions':True})
    audit.save(audit.HERE/'source-reading-manifest.json',{'status':'PASS','identifiers':len(rows),
        'selected_unknown_units':len(selected_unknown),'missing_selected_occurrences':len(missing),
        'uncovered_whitespace':len(whitespace),'wall_seconds':time.monotonic()-started,
        'command':['.venv/bin/python','-m','scripts.prospectus_question_source_readings'],
        'method_sha256':audit.sha(Path(__file__)),'production_changes':False})
    print({'status':'PASS','all_unmatched_identifiers_source_linked':len(rows),
           'selected_unknown_units':len(selected_unknown),'missing_selected_occurrences':len(missing),
           'uncovered_whitespace':len(whitespace)})


if __name__=='__main__':
    main()
