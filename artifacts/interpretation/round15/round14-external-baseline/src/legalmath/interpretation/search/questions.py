"""Rank replayable distinguishing questions without assigning legal probabilities."""
from math import log
from ...canonical import digest
from ...ir.evaluate import evaluate
from .formal import bundle,RULE,project
from .alignment import discover,translate_snapshot


def questions(nodes,comparisons,packet,at):
    by_id={n['node_id']:n for n in nodes};answers={}
    for comparison in comparisons:
        result=comparison['result']
        if result['status']!='DIFFERENT':continue
        snapshot=result['snapshot'];key=digest(snapshot)
        if key in answers:continue
        left=by_id[comparison.get('left_node_id',comparison['pair'][0])]
        facts=left['reading']['formalization']['facts'];predictions={};excluded=[]
        mappings={}
        for node in nodes:
            f=node['reading']['formalization']
            if node['encoding_error'] or not f:
                excluded.append(node['node_id']);continue
            candidate_snapshot=snapshot
            if f['facts']!=facts:
                # Historical comparisons remain interpreted with their original
                # exact-binding rule. Only a new explicit correspondence opts in.
                found=discover(left['reading'],node['reading']) if 'fact_correspondence' in result else None
                if not found or found['mapping'] is None:
                    excluded.append(node['node_id']);continue
                candidate_snapshot=translate_snapshot(snapshot,found['mapping'])
                mappings[node['node_id']]=found['mapping']
            compiled=bundle(node['reading'],packet,at)
            predictions[node['node_id']]=project(evaluate(compiled,candidate_snapshot,RULE,at,at))
        groups={}
        for node_id,value in predictions.items():groups.setdefault(digest(value),[]).append(node_id)
        pairs=sum(len(a)*len(b) for i,a in enumerate(groups.values()) for b in list(groups.values())[i+1:])
        answers[key]={'snapshot_hash':key,'snapshot':snapshot,'predictions':predictions,
            'excluded_incompatible_fact_bindings':excluded,'separated_candidate_pairs':pairs,
            'question':'Which source-supported outcome applies to these facts, and why?',
            'score_purpose':'REVIEW_INFORMATION_ONLY','legal_correctness_probability':None}
        if mappings:answers[key]['exact_fact_correspondences']=mappings
    return sorted(answers.values(),key=lambda q:(-q['separated_candidate_pairs'],q['snapshot_hash']))


def behavioral_groups(nodes,comparisons):
    """Complete-link grouping requires checked pairwise equivalence, never model similarity."""
    equivalent={tuple(sorted(c['pair'])) for c in comparisons if c['result']['status']=='EQUIVALENT_WITHIN_DOMAIN'}
    groups=[]
    for node in nodes:
        ident=node['node_id']
        group=next((g for g in groups if all(tuple(sorted((ident,x))) in equivalent for x in g)),None)
        if group is None:groups.append([ident])
        else:group.append(ident)
    count=len(nodes)
    entropy=-sum((len(g)/count)*log(len(g)/count) for g in groups) if count else None
    return {'groups':groups,'empirical_branch_entropy':str(entropy) if entropy is not None else None,
        'interpretation':'Descriptive distribution of retained branches; no random-sampling or legal-probability claim',
        'distinct_source_commitments_preserved':True}
