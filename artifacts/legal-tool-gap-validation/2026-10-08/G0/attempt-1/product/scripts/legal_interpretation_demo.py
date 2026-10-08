"""Offline declared fixture exercising the actual CompleteInvestigation route."""
import os
os.environ["CUDA_VISIBLE_DEVICES"]="-1"
from pathlib import Path
from legalmath.interpretation.semantics.records import Settings
from legalmath.interpretation.semantics.integration import PROFILE

def options(variants=2):
    return {"profile":PROFILE,"settings":[Settings(semantics="grounded" if i%2==0 else "preferred",
        ordering="none",priorities=(),max_arguments=8,max_extensions=256+i,timeout_seconds=5).model_dump(mode="json")
        for i in range(variants)],"case_limit":2}

def execute(directory,variants=2):
    from tests.search.support import FunctionProvider
    from tests.assurance.test_successor_workflow import complete_responder
    from tests.assurance.test_integration import source,settings
    from tests.search.test_formal import AT
    from tests.catala.backend_support import TOOLCHAIN
    from legalmath.interpretation.assurance.complete_investigation import CompleteInvestigation
    root=Path(__file__).resolve().parents[1]
    provider=FunctionProvider(complete_responder)
    runner=CompleteInvestigation(root,directory,provider,root/".localresources/java-toolchain/jdk-17.0.20.1+1",AT,
        settings=settings(),maximum_scoped_actions=12,scoped_rounds=1,machine_qualification=True,catala=TOOLCHAIN,
        semantic_options=options(variants))
    result=runner.run([source()],"Selected gift control")
    return root,runner,result
