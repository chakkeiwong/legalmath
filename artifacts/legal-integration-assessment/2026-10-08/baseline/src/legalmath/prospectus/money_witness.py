"""Independent validation of the finite monetary-field witness contract.

No extractor or regex capture objects are trusted. Labels and grammar remain
explicit bounded English assumptions; arithmetic/source checks are independent.
"""
import re
from fractions import Fraction

LABELS={'calculation_amount':'Calculation Amount',
        'final_redemption_amount':'Final Redemption Amount',
        'calculation_amount_alias':'Calculation Amount'}
PAREN={'applicable to notes in definitive form.','applicable to notes in definitive form',
       'applicable to the notes in definitive form.','applicable to the notes in definitive form',
       'see conditions','in definitive form','in relation to calculation of interest in global form see conditions',
       'in relation to calculation of interest on notes in global form or registered definitive form see conditions'}


def number(token):
    whole,dot,part=token.partition('.')
    if dot and (not part or not part.isascii() or not part.isdecimal()):raise ValueError('Bad decimal digits')
    groups=whole.split(',')
    if any(not s or not s.isascii() or not s.isdecimal() for s in groups):raise ValueError('Bad integer digits')
    if len(groups)>1 and (not 1<=len(groups[0])<=3 or any(len(s)!=3 for s in groups[1:])):
        raise ValueError('Bad thousands grouping')
    return Fraction(int(''.join(groups))*(10**len(part))+(int(part) if part else 0),10**len(part))


def field_value(quote,kind):
    text=' '.join(quote.split());label=LABELS[kind]
    if kind=='calculation_amount' and text.casefold().startswith('specified denominations'):
        label='Specified Denominations'
    if not text.casefold().startswith(label.casefold()):raise ValueError('Wrong money field label')
    rest=text[len(label):]
    if kind=='final_redemption_amount' and rest.casefold().startswith(' of each note'):rest=rest[len(' of each Note'):]
    if not rest or rest[0] not in ' :(\t\n':raise ValueError('Money heading has no boundary')
    rest=rest.lstrip()
    if rest.startswith('('):
        closing=rest.find(')')
        if closing<0 or rest[1:closing].casefold() not in PAREN:raise ValueError('Unsupported field qualification')
        rest=rest[closing+1:].lstrip()
    if rest.startswith(':'):rest=rest[1:].lstrip()
    if kind=='calculation_amount_alias':
        if rest.casefold()!='specified denominations':raise ValueError('Unsupported unit alias')
        return None
    currency=None
    for symbol,code in [('US$','USD'),('GBP','GBP'),('EUR','EUR'),('USD','USD'),('£','GBP'),('€','EUR')]:
        if rest.upper().startswith(symbol):currency=code;rest=rest[len(symbol):].lstrip();break
    if currency is None:raise ValueError('Missing currency')
    stop=0
    while stop<len(rest) and rest[stop] in '0123456789,.':stop+=1
    token=rest[:stop];tail=rest[stop:].strip()
    # A field witness ends at its value, not the following sentence punctuation.
    value=number(token)
    if kind=='final_redemption_amount':
        if tail.casefold()!='per calculation amount':raise ValueError('Final value has no explicit unit')
    elif tail:raise ValueError('Unexpected unit field suffix')
    if value<=0:raise ValueError('Nonpositive calculation/redemption amount')
    return currency,value


def verify(text,record):
    if record.get('status')!='equal':raise ValueError('Equality witness required')
    fields=record.get('fields',[])
    kinds=[f.get('field') for f in fields]
    if record.get('format')=='per_note':
        if kinds!=['final_redemption_per_note']:raise ValueError('Wrong per-note field roles')
        field=fields[0];a,b=field.get('start'),field.get('end')
        if type(a) is not int or type(b) is not int or not 0<=a<b<=len(text) or text[a:b]!=field['quote']:
            raise ValueError('Per-note source span changed')
        quote=' '.join(field['quote'].split())
        label='Final Redemption Amount of each Note'
        if not quote.lower().startswith(label.lower()):raise ValueError('Wrong per-note label')
        rest=quote[len(label):].lstrip();rest=rest[1:].lstrip() if rest.startswith(':') else rest
        parts=re.split(r'\s+per Note of\s+',rest,flags=re.I)
        if len(parts)!=2 or not parts[1].lower().endswith(' specified denomination'):
            raise ValueError('Explicit per-note unit required')
        left=field_value('Calculation Amount: '+parts[0],'calculation_amount')
        right=field_value('Calculation Amount: '+parts[1][:-len(' Specified Denomination')],'calculation_amount')
        if left!=right or left[0]!=record.get('currency') or left[1]!=Fraction(record.get('amount','0')):
            raise ValueError('Per-note values differ')
        return {'status':'CHECKED','currency':left[0],'amount':str(left[1]),'scope':'Explicit per-note denomination and exact rational equality'}
    if kinds not in (['calculation_amount','final_redemption_amount'],
                     ['calculation_amount_alias','calculation_amount','final_redemption_amount']):
        raise ValueError('Wrong or duplicate field roles')
    values={}
    for field in fields:
        a,b=field.get('start'),field.get('end')
        if type(a) is not int or type(b) is not int or not 0<=a<b<=len(text):raise ValueError('Invalid field offsets')
        if text[a:b]!=field['quote']:raise ValueError('Money quotation changed')
        if re.search(r'\bper\s*$',text[max(0,a-30):a],re.I):raise ValueError('A unit reference is not a field heading')
        values[field['field']]=field_value(field['quote'],field['field'])
    if values['calculation_amount']!=values['final_redemption_amount']:raise ValueError('Money fields differ')
    currency,value=values['calculation_amount']
    if record.get('currency')!=currency or Fraction(record.get('amount','0'))!=value:raise ValueError('Forged monetary equality')
    is_denom=next(f for f in fields if f['field']=='calculation_amount')['quote'].lower().startswith('specified denominations')
    if is_denom!=('calculation_amount_alias' in values):raise ValueError('Denomination lacks an explicit calculation-unit alias')
    return {'status':'CHECKED','currency':currency,'amount':str(value),'scope':'Bounded field labels, exact source spans and rational equality; not unrestricted English meaning'}
