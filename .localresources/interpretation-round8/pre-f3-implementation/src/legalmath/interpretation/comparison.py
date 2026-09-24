"""Retain solver evidence without upgrading bounded equivalence to legal equivalence."""
from ..analysis.compare import compare
from ..canonical import digest
from ..errors import LegalMathError
from .contracts import V
from .service import ident

def compare_candidates(service, caller, run_id, left, right, rule_id, domain, valid_at, known_at, *, java_jar=None, jdk=None, budget_ms=10000):
    with service.db.connect() as con:
        service._owner(con,caller,run_id);run=service._run(con,run_id,True)
        cs=[service._get(con,run_id,'candidate',c) for c in (left,right)]
        if any(c['bundle_hash'] is None for c in cs): raise LegalMathError('E_REFERENCE')
        bundles=[service.db.get(con,c['bundle_hash']) for c in cs]
    result=compare(*bundles,rule_id,domain,valid_at,known_at,java_jar=java_jar,jdk=jdk,budget_ms=budget_ms)
    status={'COUNTEREXAMPLE':'DIFFERENT','NO_COUNTEREXAMPLE_IN_DECLARED_DOMAIN':'EQUIVALENT_WITHIN_DOMAIN','INCONSISTENT_DOMAIN':'INCONSISTENT_DOMAIN'}.get(result['status'],'UNKNOWN')
    with service.db.transaction() as con:
        service._run(con,run_id,True)
        e=dict(schema_version=V,evidence_id=ident('evidence'),run_id=run_id,source_packet_hash=run['source_packet_hash'],kind='FORMAL_COMPARISON',
            content_hash=service.db.put(con,'comparison',result),statement='Encoded status/type/value comparison in the declared domain',source_unit_ids=sorted(set(cs[0]['source_unit_ids']+cs[1]['source_unit_ids'])),
            validation_status='VALIDATED' if status in ('DIFFERENT','EQUIVALENT_WITHIN_DOMAIN') else 'UNVERIFIED',authority='SYNTHETIC_FIXTURE',validator_id='ruleir-comparison',action_id=None,review_decision_id=None,
            domain_hash=digest(domain),comparison_result=status,legal_source_commitment_resolved=False)
        service._save(con,'evidence',e)
        return dict(evidence=e,result=result)
