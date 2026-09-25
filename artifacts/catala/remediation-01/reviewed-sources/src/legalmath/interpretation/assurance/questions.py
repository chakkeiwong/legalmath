"""Executed question partitions with bounded work and explicit comparability."""
from copy import deepcopy
from itertools import combinations
from ...canonical import digest
from ...errors import LegalMathError
from ...ir.trace import verify_result
from ..search.alignment import discover, translate_snapshot
from ..search.formal import bundle, project
from .semantics import check_quotes
from ..outputs import convention


def proposals(comparisons, candidates, packet, at):
    result = {}; deferred = []
    for comparison in comparisons:
        value = comparison['result']
        if value['status'] != 'DIFFERENT': continue
        cid = comparison['pair'][0]
        if cid not in candidates or not value.get('snapshot'):
            deferred.append({'pair':comparison['pair'],'reason':'MISSING_BASE_OR_SNAPSHOT'}); continue
        reading = candidates[cid]
        record = {'source_packet_hash':digest(packet),'candidates_hash':digest(candidates), 'at':at,
            'base_candidate_id':cid,'snapshot':deepcopy(value['snapshot']),
            'question':'Which source-supported outcome applies to these facts, and why?',
            'evidence':deepcopy(reading['citations']),'assumptions':deepcopy(reading['assumptions']),
            'subject':reading['subject'],'output_meaning':convention(reading)}
        result[digest({'base':cid,'snapshot':record['snapshot']})] = record
    return list(result.values()), deferred


def partition(question, candidates, packet, checker, *, max_replays=32):
    if type(max_replays) is not int or not 0 <= max_replays <= 256: raise LegalMathError('E_RESOURCE_LIMIT')
    if (question['source_packet_hash'] != digest(packet) or question['candidates_hash'] != digest(candidates)
            or question['at'] != checker.at): raise LegalMathError('E_STALE_REVIEW')
    base = candidates.get(question['base_candidate_id'])
    if base is None or base['formalization'] is None: raise LegalMathError('E_REFERENCE')
    check_quotes(question['evidence'],packet)
    if (question['assumptions'] != base['assumptions'] or question['subject'] != base['subject']
            or question['output_meaning'] != convention(base)): raise LegalMathError('E_STALE_REVIEW')
    records = {}; excluded = []; replayed = 0
    for cid, reading in sorted(candidates.items()):
        reason = None
        if not reading['formalization']: reason = 'UNSUPPORTED_FORMALIZATION'
        elif convention(base) is None or convention(reading) != convention(base): reason = 'OUTPUT_MEANING_UNALIGNED'
        elif reading['subject'] != base['subject']: reason = 'SUBJECT_UNALIGNED'
        if reason:
            excluded.append({'candidate_id':cid,'reason':reason}); continue
        found = discover(base, reading)
        if found['mapping'] is None:
            excluded.append({'candidate_id':cid,'reason':'INCOMPATIBLE_FACT_BINDINGS','correspondence':found}); continue
        if replayed >= max_replays:
            excluded.append({'candidate_id':cid,'reason':'REPLAY_LIMIT'}); continue
        snapshot = translate_snapshot(question['snapshot'],found['mapping'])
        try:
            compiled = bundle(reading,packet,checker.at)
            replayed += 1
            replay = checker.replay([compiled],snapshot)[0]
            if replay['java']['status'] == 'ERROR':
                excluded.append({'candidate_id':cid,'reason':'ERROR_RESULT','replay':replay}); continue
            records[cid] = {'snapshot':snapshot,'bundle':compiled,'replay':replay,
                            'correspondence':found,'assumptions':reading['assumptions']}
        except LegalMathError as exc:
            excluded.append({'candidate_id':cid,'reason':'REPLAY_FAILED','error':exc.code})
    pairs = [list(pair) for pair in combinations(sorted(records),2)
             if project(records[pair[0]]['replay']['java']) != project(records[pair[1]]['replay']['java'])]
    result = {'question':deepcopy(question),'question_id':'question.'+digest(question)[:24],
        'status':'EXECUTED_PARTITION','records':records,'excluded':excluded,'replays_consumed':replayed,
        'separated_pairs':pairs,'separated_candidate_pairs':len(pairs),
        'coverage_complete':not excluded,'source_question_answered':False,
        'score_meaning':'Executed differing program outputs under declared facts; not legal probability',
        'release_eligible':False}
    return {**result,'partition_hash':digest(result)}


def verify_partition(record, candidates, packet, at):
    body = {k:v for k,v in record.items() if k != 'partition_hash'}
    q=record['question']
    if digest(body) != record['partition_hash']: raise LegalMathError('E_INTEGRITY')
    if q['source_packet_hash'] != digest(packet) or q['candidates_hash'] != digest(candidates) or q['at'] != at:
        raise LegalMathError('E_STALE_REVIEW')
    check_quotes(q['evidence'],packet)
    base=candidates.get(q['base_candidate_id'])
    if (not base or q['assumptions']!=base['assumptions'] or q['subject']!=base['subject']
            or q['output_meaning']!=convention(base)):
        raise LegalMathError('E_STALE_REVIEW')
    excluded=[e['candidate_id'] for e in record['excluded']]
    if (len(set(excluded))!=len(excluded) or set(excluded)&set(record['records'])
            or set(excluded)|set(record['records']) != set(candidates)):
        raise LegalMathError('E_REFERENCE')
    for cid, row in record['records'].items():
        compiled=bundle(candidates[cid],packet,at)
        if compiled != row['bundle']: raise LegalMathError('E_STALE_REVIEW')
        found=discover(base,candidates[cid])
        if (found['mapping'] is None or found!=row['correspondence']
                or translate_snapshot(q['snapshot'],found['mapping'])!=row['snapshot']
                or row['assumptions']!=candidates[cid]['assumptions']
                or convention(candidates[cid])!=q['output_meaning'] or candidates[cid]['subject']!=q['subject']):
            raise LegalMathError('E_STALE_REVIEW')
        for language in ('python','java'):
            verify_result(compiled,row['snapshot'],'selected.control',row['replay'][language])
        a,b=(row['replay'][lang] for lang in ('python','java'))
        exclude={'engine_version','result_hash'}
        if {k:v for k,v in a.items() if k not in exclude}!={k:v for k,v in b.items() if k not in exclude}:
            raise LegalMathError('E_INTEGRITY')
    pairs=[list(pair) for pair in combinations(sorted(record['records']),2) if
           project(record['records'][pair[0]]['replay']['java']) != project(record['records'][pair[1]]['replay']['java'])]
    if pairs!=record['separated_pairs'] or len(pairs)!=record['separated_candidate_pairs']:
        raise LegalMathError('E_INTEGRITY')
    return record


def execute_partitions(comparisons,candidates,packet,checker,*,max_questions=4,max_replays=32):
    if type(max_questions) is not int or not 0<=max_questions<=32 or type(max_replays) is not int or not 0<=max_replays<=256:
        raise LegalMathError('E_RESOURCE_LIMIT')
    questions,deferred=proposals(comparisons,candidates,packet,checker.at);records=[];remaining=max_replays
    for index, question in enumerate(questions):
        if index>=max_questions or remaining==0:
            deferred.append({'question_hash':digest(question),'reason':'QUESTION_OR_REPLAY_LIMIT'});continue
        result=partition(question,candidates,packet,checker,max_replays=remaining)
        verify_partition(result,candidates,packet,checker.at)
        records.append(result);remaining-=result['replays_consumed']
    return {'source_packet_hash':digest(packet),'candidates_hash':digest(candidates),'at':checker.at,
        'partitions':records,'deferred':deferred,'replays_consumed':max_replays-remaining,
        'status':('INCOMPLETE' if deferred or any(not r['coverage_complete'] for r in records)
                  else 'EXECUTED' if records else 'NO_CHECKED_DISTINCTIONS'),
        'legal_source_commitment_resolved':False}


def annotate_actions(actions, checked, candidates, packet, at):
    if (checked['source_packet_hash']!=digest(packet) or checked['candidates_hash']!=digest(candidates)
            or checked['at']!=at): raise LegalMathError('E_STALE_REVIEW')
    for record in checked['partitions']:verify_partition(record,candidates,packet,at)
    result=[]
    for action in actions:
        cid=action.get('candidate_id');pairs=set();hashes=[]
        for record in checked['partitions']:
            relevant=[p for p in record['separated_pairs'] if cid in p]
            if relevant:
                pairs.update(tuple(p) for p in relevant);hashes.append(record['partition_hash'])
        result.append({**action,'separated_pairs':len(pairs),'separation_basis':'EXECUTED_JAVA_PARTITIONS',
            'source_omission_check':action.get('stage')=='INTERPRETATION',
            'inputs':{**action.get('inputs',{}),'partition_hashes':hashes},
            'score_scope':{'source_packet_hash':digest(packet),'candidates_hash':digest(candidates),'at':at}})
    return result
