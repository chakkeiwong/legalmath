"""Conditional source probes frozen before unfamiliar-task generation."""
from run_assurance_successor import ROOT,OUT,read,save,sha,rel,now
from legalmath.canonical import digest
from legalmath.errors import LegalMathError

# These are deliberately questions about an express, bounded proposition, not
# invented independent judgments of complete legal compliance.
SPECS={
 '26ec55':[
  ('equal.threshold','An SFC-authorised fund, which is not a listed closed-ended alternative asset fund, has total direct and indirect private-market exposure of exactly 50% of NAV.',
   'Does the express 50% threshold classify this fund as complex?', 'TRUE','50% or more'),
  ('below.no.designation.evidence','The same type of in-scope fund has exposure of 49.9% NAV; no evidence establishes whether SFC made a case-by-case designation.',
   'Is the fund definitely non-complex under this circular?', 'NOT_ESTABLISHED','case-by-case basis'),
  ('excluded.laf','The investment vehicle is a listed closed-ended alternative asset fund with 60% exposure.',
   'Does this circular itself establish its complex-product classification?', 'NOT_ESTABLISHED','Except for listed closed-ended'),
  ('no.solicitation','An in-scope fund has already been classified complex. Its sale involves no solicitation or recommendation.',
   'Does the circular still state a suitability requirement for its investors?', 'TRUE','irrespective of whether solicitation')],
 '26ec51':[
  ('screenshot.only','A payer bank does not require owner confirmation. The only ownership evidence is a deposit screenshot supplied by the client; no independent bank record or alternative verification exists.',
   'Does this evidence satisfy the described small-transfer ownership verification route?', 'FALSE','obtained by the licensed firm from its bank'),
  ('missing.identity','A robust payer-bank owner-confirmation process is established. The required identification information has not been verified by any method.',
   'Does owner confirmation alone establish satisfaction of both paragraph 10(a) and 10(b)?', 'FALSE','identification information'),
  ('different.id','The client used a different identity document to open the bank account; the firm obtains that document and verifies it. The question concerns the described identification route only.',
   'Does the circular expressly describe this as an identification-verification route?', 'TRUE','obtaining the identification document'),
  ('automatic.decline','A red flag is observed, but the appropriateness of declining the request has not been assessed.',
   'Does the circular require automatic unconditional decline in every such case?', 'FALSE','where appropriate')],
 '25ec66':[
  ('ordinary.change','On 1 December 2025 an in-scope UCITS proposes a material investment-policy change compliant with home-jurisdiction requirements, without novel or complex features or local policy implications; there is no pre-effective pending application.',
   'Does the circular remove the prior-SFC-approval requirement for this change?', 'TRUE','Removing the SFC’s requirement on prior approval for material changes'),
  ('complex.change','The same change involves novel or complex product features.',
   'Does the stated removal unconditionally cover this change?', 'FALSE','except for changes'),
  ('pending.application','An application was received on 27 November 2025 and no approval or authorisation had been granted by the Effective Date.',
   'Does the circular state that the existing approval or authorisation process continues for this application?', 'TRUE','before the Effective Date'),
  ('uk.ucits','A scheme domiciled in the United Kingdom is authorised as UK UCITS.',
   'Is it included in this circular’s definition of UCITS funds?', 'TRUE','United Kingdom authorised as UK UCITS')],
 '26ec35':[
  ('already.bound','An existing client already has a bound device.',
   'Does this circular require that client to rebind that device merely because of the new authentication measures?', 'FALSE','not required to request existing clients to rebind'),
  ('otp.claim','An internet broker proposes to label SMS OTP as a phishing-resistant authentication solution.',
   'Does that classification agree with the circular’s stated view?', 'FALSE','does not consider OTP'),
  ('four.devices','A client requests four bound devices; the firm has not conducted an adequate assessment.',
   'Has the firm met the expressly stated assessment condition before approving more than three?', 'FALSE','conduct adequate assessment'),
  ('large.broker','A large internet broker plans to delay its robust authentication solution until July 2027 solely on the ground that all firms have twelve months.',
   'Does that justification preserve the circular’s express expectation for large internet brokers?', 'FALSE','large internet brokers are expected to implement these solutions immediately')]
}


def freeze():
    target=OUT/'conditional-case-reference.json'
    if target.exists():return read(target)
    if (OUT/'unfamiliar-study').exists():raise LegalMathError('E_STALE_REVIEW',details='Reference must precede unfamiliar answers')
    rows=[]
    for ref in read(OUT/'task-freeze.json')['tasks']:
        if sha(ROOT/ref['path'])!=ref['sha256']:raise LegalMathError('E_INTEGRITY')
        task=read(ROOT/ref['path']);p=task['packet']
        for ident,facts,question,expected,needle in SPECS[task['task_id']]:
            units=[u for u in p['units'] if needle in u['text']]
            if not units:raise LegalMathError('E_REFERENCE',details=needle)
            rows.append({'case_id':task['task_id']+'.'+ident,'task_id':task['task_id'],'facts':facts,'question':question,
                'expected':expected,'evidence':[{'unit_id':u['unit_id'],'quote':u['text']} for u in units],
                'basis':'Conditional implication of an express retained clause; same-executor source check, not independent legal adjudication',
                'assumptions':['The supplied classifications and factual stipulations are true.',
                  'No later amendment or other applicable authority displaces the selected clause.'],
                'source_packet_hash':digest(p)})
    value={'profile':'conditional-source-reference.v1','frozen_at':now(),'cases':rows,
           'model_calls_at_freeze':len(read(OUT/'live-allowance.json')['calls']),
           'unfamiliar_model_answers_at_freeze':0,'independent_legal_ground_truth':False,
           'performance_claim':'Source-condition challenge outcomes; no estimated deployment accuracy'}
    save(target,value);return value


if __name__=='__main__':print({'frozen_cases':len(freeze()['cases'])})
