"""Retain two explicitly proposed branches of actual SFC FAQ Question 1."""
from pathlib import Path
from legalmath.canonical import canonical,raw_digest
from legalmath.interpretation.assurance.authorities import AuthorityCatalog
from legalmath.interpretation.assurance.examples import ExampleRegistry
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'.localresources/sfc-examples/b3'


def build_value(catalog):
    text=catalog.documents['faq.2010']['text']
    def anchor(quote):
        start=text.index(quote)
        return {'edition_id':'faq.2010','start':start,'end':start+len(quote),'quote':quote}
    outcome='then such gifts will be bound by this requirement'
    offered='if gifts are offered in such a way that they are linked to a particular type of investment product'
    records=[]
    for branch,quote in [('fund.type','certain types of funds'),('fund.house','funds offered by certain fund houses')]:
        records.append({'example_id':'sfc.faq.q1.'+branch,'kind':'OFFICIAL_EXAMPLE','provision_id':'faq.2010.q1',
            'issue_id':'paragraph.3.11.applicability','issue_description':'Whether paragraph 3.11 applies to a product-linked gift promotion',
            'factors':[{'factor_id':'gift.linked','description':'Gifts are offered linked to a particular type of investment product',
                        'evidence':[anchor(offered)]},
                       {'factor_id':branch+'.link','description':quote,'evidence':[anchor(quote)]}],
            'outcome':{'atom':'paragraph.3.11.applies','negative':False},
            'outcome_description':'The gift offer is bound by the paragraph 3.11 requirement; this alone does not decide every exception or prohibition.',
            'outcome_evidence':[anchor(outcome)],
            'derivation':'Developer factorization of one disjunctive official FAQ answer. The two records share one source family and are not independent cases. Historical applicability and factor materiality remain unresolved.'})
    return {'version':'example-registry.v1','authority_catalog_hash':catalog.hash,'examples':records}


if __name__=='__main__':
    if OUT.exists():raise ValueError('Preserve existing example snapshot')
    c=AuthorityCatalog.load(ROOT/'.localresources/sfc-authorities/b1/catalog.json')
    value=build_value(c);ExampleRegistry(value,c)
    OUT.mkdir(parents=True)
    (OUT/'registry.json').write_bytes(canonical(value))
    (OUT/'provenance.json').write_bytes(canonical({'source_catalog':'.localresources/sfc-authorities/b1/catalog.json',
        'source_family':'SFC Code FAQ 30 September 2010 Question 1; currently retained page',
        'source_sha256':c.editions['faq.2010']['raw_sha256'],'records':2,'independent_source_families':1,
        'extraction_authority':'DEVELOPER_PROPOSED_FACTORIZATION','legal_accuracy_evaluated':False}))
    (OUT/'manifest.json').write_bytes(canonical({'files':{p.name:raw_digest(p.read_bytes()) for p in OUT.iterdir()}}))
    print('Retained two proposed example branches from one real official FAQ answer.')
