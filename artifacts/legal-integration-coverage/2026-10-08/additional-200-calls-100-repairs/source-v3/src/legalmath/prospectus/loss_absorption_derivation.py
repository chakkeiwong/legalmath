"""Check source/fact/decision/explanation joins separately from the extractor.

The source-construction recogniser is a shared, explicitly qualified premise.
This checker independently evaluates the four-state decision and validates
binding/derivation integrity; it is not an independent oracle for English.
"""
from itertools import product
from fractions import Fraction

from .common import digest
from .loss_absorption_witnesses import series_binding, validate_semantic_witness, exact_repayment


def evaluate(facts):
    names=('debt','principal_write_down','mandatory_common_conversion','coverage_complete')
    if set(facts)!=set(names):raise ValueError('Unexpected formal premises')
    if any(v=='conflict' for v in facts.values()):return None
    if any(v is not None and type(v) is not bool for v in facts.values()):raise ValueError('Invalid premise')
    choices=[(False,True) if facts[n] is None else (facts[n],) for n in names]
    possible=set()
    for debt,write_down,convert,covered in product(*choices):
        possible.add('yes' if debt and (write_down or convert) else 'no' if debt and covered else 'unknown')
    return True if possible=={'yes'} else False if possible=={'no'} else None


def render(row):
    """The presentation consumes only the checked decision's evidence links."""
    if row['answer'] is None:
        return 'No supported yes/no answer: '+('; '.join(row['open_issues']) or 'the required premises are unresolved.')
    evidence={e['id']:e for e in row['evidence']}
    identity=row['derivation']['evidence_ids'][0]
    e=evidence[identity]
    location=('PDF p.'+str(e['page']) if e['page']==e['end_page'] else
              'PDF pp.'+str(e['page'])+'–'+str(e['end_page']))
    citation=' ('+e['document']+', '+location+')'
    if row['answer']:
        mechanism=('the bond can be compulsorily converted into common/ordinary shares' if e['kind']=='mandatory_common_conversion'
                   else 'the principal can be reduced or cancelled')
        origin=' under a disclosed statutory resolution power' if e['origin']=='statutory-disclosed' else ' under the contractual terms'
        return 'Yes: '+mechanism+origin+citation+'. The conditions are retained in the cited evidence; the power need not have been exercised.'
    return ('No feature identified within the examined offering terms: cash principal repayment is provided'+citation+
            '; no applicable principal write-down or compulsory common-share conversion was identified. '
            'This is a qualified source reading, not a proof of absence in all operative language or documents.')


def check(row,documents):
    # documents map IDs to the verified, normalized text and original hash.
    d=row['derivation'];payload={k:v for k,v in d.items() if k!='sha256'}
    if digest(payload)!=d['sha256']:raise ValueError('Derivation digest changed')
    if d['issue_id']!=row['id'] or d['facts']!=row['facts'] or d['answer'] is not row['answer']:
        raise ValueError('Decision/derivation mismatch')
    if evaluate(row['facts']) is not row['answer']:raise ValueError('Independent decision mismatch')
    if row.get('certified_legal_answer') is not None or d.get('english_entailment')!='NOT_PROVED' or d.get('absence_proof')!='NOT_PROVED':
        raise ValueError('Unsupported legal certification')
    seen={}
    for e in row['evidence']:
        if e['id'] in seen:raise ValueError('Duplicate evidence identity')
        seen[e['id']]=e
        if digest({k:v for k,v in e.items() if k!='id'})[:24]!=e['id']:raise ValueError('Evidence digest changed')
        source=documents[e['document']]
        if e['source_sha256']!=source['sha256'] or source['text'][e['start']:e['end']]!=e['quote']:
            raise ValueError('Source witness changed')
        if e.get('issue_id')!=row['id']:raise ValueError('Evidence belongs to another issue')
        if e['disposition']!='applicable':continue
        bound_text=(' '.join(f['quote'] for f in e['repayment_derivation']['fields'])
                    if 'repayment_derivation' in e else e['quote'])
        if series_binding(bound_text,row)=='other_issue':raise ValueError('Evidence names another series')
        if e['kind'] in ('principal_write_down','mandatory_common_conversion','no_write_down','no_conversion'):
            if not validate_semantic_witness(e,source.get('definition_text',source['text'])):
                raise ValueError('Unsupported mechanism construction')
        if 'repayment_derivation' in e:
            r=e['repayment_derivation']
            if r['status']!='equal' or Fraction(r['amount'])<=0:raise ValueError('Invalid monetary derivation')
            if exact_repayment(source['text'])!=r:raise ValueError('Monetary relation does not replay')
            from .money_witness import verify as verify_money
            verify_money(source['text'],r)
            for f in r['fields']:
                if source['text'][f['start']:f['end']]!=f['quote']:raise ValueError('Monetary source field changed')
    for name,opposite in [('principal_write_down','no_write_down'),('mandatory_common_conversion','no_conversion')]:
        positive=any(e['kind']==name and e['disposition']=='applicable' for e in seen.values())
        negative=any(e['kind']==opposite and e['disposition']=='applicable' for e in seen.values())
        if row['facts'][name] is True and not positive:raise ValueError('Positive fact without its witness')
        if row['facts'][name] is False and positive:raise ValueError('Positive witness discarded')
        if row['facts'][name]=='conflict' and not (positive and negative):raise ValueError('Invented conflict')
    refs=d['evidence_ids']
    if len(refs)!=len(set(refs)) or any(i not in seen for i in refs):raise ValueError('Missing derivation evidence')
    if row['answer'] is not None and not refs:raise ValueError('Binary answer without derivation evidence')
    for identity in refs:
        e=seen[identity]
        required={'principal_write_down','mandatory_common_conversion'} if row['answer'] else {'cash_repayment'}
        if e['disposition']!='applicable' or e['kind'] not in required:raise ValueError('Wrong explanation witness')
    if row['answer'] is False and (row['open_issues'] or not row['facts']['coverage_complete']):
        raise ValueError('Negative with unresolved premises')
    if row.get('summary_reason')!=render(row):raise ValueError('Explanation is detached from its derivation')
    return {'status':'CHECKED','issue_id':row['id'],'derivation_sha256':d['sha256'],
            'formal_answer':row['answer'],'source_meaning':'QUALIFIED_NOT_PROVED'}
