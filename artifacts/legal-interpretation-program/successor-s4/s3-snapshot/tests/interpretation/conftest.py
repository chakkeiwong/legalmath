import pytest
from legalmath.interpretation import Interpretations
from legalmath.review.lifecycle import Lifecycle

@pytest.fixture
def svc(db):
    Lifecycle(db).register({'author':{'token':'author','roles':['author']},'meaning':{'token':'meaning','roles':['meaning']},'engineer':{'token':'engineer','roles':['engineering']}})
    return Interpretations(db)

@pytest.fixture
def packet():
    return {'source_key':'synthetic.promotional','authority':'SYNTHETIC_FIXTURE','selected_slice':'Promotional route',
        'units':[{'unit_id':'p10','locator':'paragraph 10','text':'A prior investment or product-type route is sufficient.','normative':True,'span':None},
                 {'unit_id':'fn1','locator':'footnote 1','text':'Product type is an alternative route.','normative':True,'span':None}],
        'dependencies':[],'family_ids':['literal','alternative']}

@pytest.fixture
def run(svc,packet):
    return svc.create('author','create',packet)

@pytest.fixture
def proposal(run):
    return dict(source_packet_hash=run['source_packet_hash'],source_unit_ids=['p10'],family_ids=['literal'],subject_unit='Customer',
        controlled_language='Prior investment route',bundle_hash=None,assumptions=[],arguments=[],parent_id=None,revision_reason='First reading')
