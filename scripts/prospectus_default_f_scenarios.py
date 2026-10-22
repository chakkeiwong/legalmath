"""Declared hypothetical controls; no measured or client facts."""
from copy import deepcopy

FACT_NAMES=['cessation','disposal','value_cessation','risk_cessation',
            'value_disposal','risk_disposal','value_joint','risk_joint']


def cases():
    empty={k:False for k in FACT_NAMES};full={k:True for k in FACT_NAMES}
    def make(name,x,r=None,**extra):
        facts={**{'exercise.'+k:v for k,v in x.items()},**{'receipt.'+k:v for k,v in (x if r is None else r).items()},
               'notice':True,'cured_before_exercise':False,'quorum_at_receipt':False,
               'other_eligible_at_receipt':False,'f_other_eligibility_at_receipt':True,**extra}
        return {'id':name,'kind':'HYPOTHETICAL_DEVELOPMENT','facts':facts}
    cessation={**empty,'cessation':True}
    disposal={**empty,'disposal':True,'value_disposal':True,'risk_disposal':True}
    out=[{'id':'all-open','kind':'HYPOTHETICAL_DEVELOPMENT','facts':{}},
         make('no-conduct',empty),make('all-causal-conditions',full),
         make('cessation-without-consequences',cessation),make('qualified-disposal-only',disposal),
         make('cured-before-exercise',full,cured_before_exercise=True),
         make('invalid-notice',full,notice=False),
         make('event-only-at-receipt',empty,full),make('event-only-at-exercise',full,empty),
         make('quorum-without-f',empty,quorum_at_receipt=True),
         make('other-eligible-event-without-f',empty,other_eligible_at_receipt=True),
         make('missing-receipt-eligibility',full,f_other_eligibility_at_receipt=None),
         make('conflicting-receipt-eligibility',full,f_other_eligibility_at_receipt='conflict'),
         make('missing-notice',full,notice=None),
         make('missing-causal-value',{**disposal,'value_disposal':None}),
         make('conflicting-causal-value',{**disposal,'value_disposal':'conflict'})]
    return out


EXPECTED={
    'all-open':(['UNKNOWN']*3,['UNKNOWN']*3),
    'no-conduct':(['NO']*3,['NO']*3),
    'all-causal-conditions':(['YES']*3,['YES']*3),
    'cessation-without-consequences':(['NO','NO','YES'],['NO','NO','YES']),
    'qualified-disposal-only':(['NO','YES','YES'],['NO','YES','YES']),
    'cured-before-exercise':(['NO']*3,['YES']*3),
    'invalid-notice':(['NO']*3,['YES']*3),
    'event-only-at-receipt':(['NO']*3,['YES']*3),
    'event-only-at-exercise':(['YES']*3,['NO']*3),
    'quorum-without-f':(['NO']*3,['YES']*3),
    'other-eligible-event-without-f':(['NO']*3,['YES']*3),
    'missing-receipt-eligibility':(['YES']*3,['UNKNOWN']*3),
    'conflicting-receipt-eligibility':(['YES']*3,['CONFLICT']*3),
    'missing-notice':(['UNKNOWN']*3,['YES']*3),
    'missing-causal-value':(['NO','UNKNOWN','UNKNOWN'],['NO','UNKNOWN','UNKNOWN']),
    'conflicting-causal-value':(['NO','CONFLICT','CONFLICT'],['NO','CONFLICT','CONFLICT']),
}


def manual_event(reading,f):
    # Independently transcribed source hypotheses, not the expression evaluator.
    c,d=f['cessation'],f['disposal']
    if reading=='both_conducts':return c and d and f['value_joint'] and f['risk_joint']
    if reading=='either_qualified_conduct':
        return (c and f['value_cessation'] and f['risk_cessation']) or (d and f['value_disposal'] and f['risk_disposal'])
    if reading=='cessation_or_qualified_disposal':return c or (d and f['value_disposal'] and f['risk_disposal'])
    raise ValueError('Unknown reviewed hypothesis')
