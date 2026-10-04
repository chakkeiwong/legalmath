from legalmath.interpretation.search.models import DIMENSIONS


def packet():
    return {'source_key':'synthetic.threshold','authority':'SYNTHETIC_FIXTURE',
        'selected_slice':'Six-month control','units':[{'unit_id':'p1','locator':'paragraph 1',
        'text':'A fund may publish returns only if its history is at least six months.',
        'normative':True,'span':None}], 'dependencies':[],'family_ids':list(DIMENSIONS)}


def generation(comparator='>=', *, months='6'):
    return {'readings':[{'local_id':'threshold','family':'time','subject':'Fund',
        'statement':'At least six completed calendar months are required.',
        'distinction':'Inclusive lower boundary','citations':[{'unit_id':'p1','quote':'at least six months'}],
        'assumptions':[],'questions':[],
        'formalization':{'facts':[{'name':'months','type':'integer','meaning':'Completed calendar months of fund history',
            'unit':'calendar months','source_unit_ids':['p1'],'requires_judgment':False}],
            'scope':'true','result':f'({comparator} months (integer {months}))','result_type':'bool'}}],
        'dimensions':[{'dimension':d,'status':'PROPOSED','source_unit_ids':['p1'],'explanation':'Engineering fixture'} for d in DIMENSIONS],
        'coverage':[{'unit_id':'p1','status':'INTERPRETED','reason':'Threshold selected'}],'questions':[]}


class FunctionProvider:
    provider_id='test.function';live=False
    def __init__(self, function): self.function=function;self.requests=[]
    def complete(self, request, schema, settings):
        from legalmath.interpretation.search.providers import Completion
        self.requests.append(request)
        return Completion(self.function(request),{'provider':self.provider_id,'fresh_context':True,'usage':[]})
