"""Declared comparisons read individually from the 35 retained statements.

These are inspection hypotheses, not a text classifier or equivalence oracle.
"""
from pathlib import Path
import json
from legalmath.canonical import digest
from legalmath.interpretation.semantics.clauses import propose
from legalmath.interpretation.semantics.records import Settings
from legalmath.interpretation.semantics.reconciliation import reconcile

# Each identity stays separate even where the comparison category agrees.
COMPARISONS = {
"deferred.744c4b5d99bc07afffce029b":"allocation-and-adequacy",
"deferred.2bc034bb48ed295565d54a40":"allocation",
"node.210068a368d2d851d97f6b2c":"allocation",
"node.a1aecd5b3f8f0268b771668f":"allocation",
"node.9d886e28a3d2ef8fd0f649e1":"allocation",
"node.77939279648de731412dc142":"allocation",
"alternative.006.85e21a337aa3f33d":"allocation",
"deferred.8e90af0c22246aec5c2d05d0":"allocation-and-adequacy",
"deferred.98a3f091e486e45ea459be6e":"unresolved-discharge",
"deferred.81d2c93ff70be47b96c5b4ae":"allocation",
"deferred.77b9a606d5eb7f3fbf1a2ba0":"unresolved-discharge",
"alternative.008.63eaa9a71420c12e":"allocation",
"node.b518939bd3cd4db81b61c26f":"unresolved-discharge",
"deferred.4722ac6513229bdbbbef2cfe":"unresolved-discharge",
"node.b2d71f930cf2e84f5205ceba":"unresolved-discharge",
"deferred.9cdc27606dfa89254fb0cf2c":"allocation",
"alternative.017.22bacfbbe572a908":"unresolved-discharge",
"alternative.018.c126f3978e443a4b":"allocation-and-conduct",
"alternative.011.3d746657604226ce":"allocation-and-conduct",
"alternative.005.5958f22bba2ea672":"allocation-and-conduct",
"alternative.019.8355d4775045e5e7":"allocation-and-adequacy",
"alternative.020.25356e7c001b28fe":"unresolved-discharge",
"alternative.015.63a62f7addb26e35":"unresolved-discharge",
"alternative.003.990af6ab5c7aa287":"allocation",
"alternative.014.f17e746329048376":"unresolved-discharge",
"alternative.001.fccab3d6d9633fa2":"unresolved-discharge",
"alternative.016.3c59f3e8bfcda88b":"unresolved-discharge",
"alternative.007.36f8d4feca397446":"allocation-and-conduct",
"alternative.010.036b7b89f3747a27":"allocation-and-conduct",
"alternative.013.002495f101679a7c":"allocation-and-conduct",
"alternative.004.3104c53459d53628":"allocation",
"alternative.000.f39a1382fac93154":"allocation",
"alternative.002.0120e4397a22bd9a":"allocation-and-conduct",
"alternative.012.3bfec12264c99831":"allocation",
"alternative.009.16b14207c64cad72":"allocation-and-conduct",
}
def policy(semantics="grounded",maximum=500):
    return Settings(semantics=semantics,ordering="none",priorities=(),max_arguments=maximum,
                    max_extensions=256,timeout_seconds=5)

def retained_inputs(root):
    folder=Path(root)/"artifacts/legal-interpretation-program/2026-10-06-offline-v1/P0/attempt-2"
    packet=json.loads((folder/"packet.json").read_text())
    overlay=json.loads((folder/"overlay.json").read_text())
    candidates={}
    for row in overlay["records"]:
        cid=row["reading_id"];rd=row["operative"]["original_reading"]
        if cid in candidates and candidates[cid]!=rd: raise ValueError("Conflicting original reading")
        candidates[cid]=rd
    if set(candidates)!=set(COMPARISONS): raise ValueError("Comparison inventory changed")
    questions={cid:{"control_id":cid,"question":"What follows conditionally from this retained proposal: "+rd["subject"],
        "unit_of_assessment":"declared provider/product/arrangement/period; factual applicability unresolved",
        "actor":"Product Provider","temporal_basis":"assessment period unresolved",
        "result_kind":"SATISFIED","true_means":"declared proposal conditionally true",
        "false_means":"declared proposal conditionally false; no legal noncompliance established",
        "source_evidence":rd["citations"]} for cid,rd in candidates.items()}
    table={}
    for cid,reading in candidates.items():
        kind=COMPARISONS[cid]
        dimensions={"allocation":("allocation",),"allocation-and-adequacy":("allocation","adequacy"),
                    "allocation-and-conduct":("allocation","conduct"),
                    "unresolved-discharge":("allocation","conduct","adequacy")}[kind]
        pilots=propose(packet,questions[cid],[reading],policy())["branches"]
        selected=[b for b in pilots if b["proposal_id"] in {"responsibility."+x for x in dimensions}]
        table[cid]={"reading_hash":digest(reading),"category":kind,
            "rationale":reading["distinction"],"pilot_clauses":[{"proposal_id":b["proposal_id"],"clauses":b["clauses"]} for b in selected],
            "relation":"partial comparison; discharge alternatives unresolved" if kind=="unresolved-discharge" else "partial comparison",
            "equivalence_not_established_with":["responsibility.combined","demonstration.A","demonstration.B","demonstration.C"],
            "qualifier":"Shared words or source spans do not establish equivalence of trigger, objects, standards, scope or formal consequence."}
    return packet,overlay,candidates,questions,table

def make_reconciliation(root):
    packet,overlay,candidates,questions,table=retained_inputs(root)
    return packet,candidates,questions,reconcile(packet,overlay,table,questions)

def execute_product(directory):
    from tests.search.support import FunctionProvider
    from tests.assurance.test_successor_workflow import complete_responder
    from tests.assurance.test_integration import source,settings
    from tests.search.test_formal import AT
    from tests.catala.backend_support import TOOLCHAIN
    from scripts.legal_interpretation_demo import options
    from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation
    root=Path(__file__).resolve().parents[1]
    def responder(request):
        result=complete_responder(request)
        if request["task"]=="STRUCTURED_CRITICISM":
            # Declared test objection: no claim that the gift source proves a contrary.
            a=result["arguments"][0]
            b={**a,"argument_id":"objection.fixture","inference_id":"objection.rule",
               "inference":"Synthetic contrary used only to test actual stage transport and attack handling",
               "conclusion":{**a["conclusion"],"negative":not a["conclusion"]["negative"]}}
            result["arguments"].append(b)
            result["attacks"]=[
                {"attacker":a["argument_id"],"target":b["argument_id"],"kind":"REBUT","target_component":b["argument_id"],"rationale":"Declared opposite test propositions"},
                {"attacker":b["argument_id"],"target":a["argument_id"],"kind":"REBUT","target_component":a["argument_id"],"rationale":"Declared opposite test propositions"}]
        return result
    runner=CompleteInvestigation(root,directory,FunctionProvider(responder),
        root/".localresources/java-toolchain/jdk-17.0.20.1+1",AT,settings=settings(),maximum_scoped_actions=12,
        scoped_rounds=1,machine_qualification=True,catala=TOOLCHAIN,semantic_options=options(2))
    return root,runner,runner.run([source()],"Selected gift control")
