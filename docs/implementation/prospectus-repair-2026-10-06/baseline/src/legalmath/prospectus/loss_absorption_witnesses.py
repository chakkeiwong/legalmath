"""Bounded semantic constructions with replayable source witnesses.

These patterns support qualified English readings. A checked pattern is not
a theorem about unrestricted English, authority or document completeness.
"""
import re
from fractions import Fraction


DEBT=r'(?:(?:the|these|each|our|such)\s+)?(?:Notes?|(?:Preferred\s+)?(?:Securities|Security)|Bonds?|Debentures?)'
COMMON_CLASS=r'(?:(?:ordinary|common)(?:\s+registered)?\s+shares|common\s+(?:capital\s+)?stock)'
COMMON=rf'(?:(?:newly\s+issued|new|fully\s+paid(?:\s+up)?)\s+)*(?:{COMMON_CLASS}|Conversion\s+Shares)'
MOD=r'(?:will|shall|must|may)'
ADV=r'(?:(?:automatically|irrevocably|mandatorily|compulsorily|permanently|temporarily|promptly|be|and)\s+)*'
WRITE=r'(?:writ(?:e|ten)[ -]?(?:down|off)|reduc(?:e|ed)|cancel(?:led|ed)?)'
PASSIVE_WRITE=r'(?:written[ -]?(?:down|off)|reduced|cancelled|canceled)'
AMOUNT=r'(?:(?:prevailing|full|entire|aggregate|outstanding|then|current)\s+)*(?:principal|nominal|face)\s+(?:amount|value)'
NO_CONSENT=r'(?:\((?:and\s+)?without\s+(?:any\s+requirement\s+for\s+)?(?:the\s+)?consent(?:\s+or\s+approval)?\s+of\s+(?:the\s+)?Holders\)\s+)?'
# A numbered action inherits its modal only from this same list head. Other
# subjects, reporting verbs and action negation do not fit the action slot.
LIST_HEAD=r'(?P<trigger>If\s+the\s+(?:Trigger|Conversion|Capital)\s+Event\s+occurs\b[^;:]{0,160}?,\s*(?:then\s+)?)(?P<subject>the\s+(?:Bank|Issuer|Company))\s+(?P<modal>will|shall|must)\s*:\s*'
LIST_PREFIX=r'(?:\([a-z]\)\s+[^;]{1,2400};\s*(?:and\s+)?){0,8}\([a-z]\)\s+'

# Each rule binds obligation/power to the relevant action in one matched
# relation; an unrelated shall/notify/confirm is not a mandatory mechanism.
RULES={
 'copular_mandatory_conversion':('mandatory_common_conversion',rf'(?P<subject>{DEBT})\s+(?P<modal>are|is)\s+(?P<force>(?:(?:irrevocably|automatically)\s+and\s+)?(?:mandatorily|compulsorily))\s+(?P<action>(?:(?:and|irrevocably|automatically)\s+)*convertible\s+(?:into|to))\s+(?P<target>{COMMON})'),
 'numbered_mandatory_conversion':('mandatory_common_conversion',rf'{LIST_HEAD}{LIST_PREFIX}(?P<action>{ADV}{NO_CONSENT}convert)\s+(?:all\s+)?(?P<security>{DEBT})\s+(?:into|to)\s+(?P<target>{COMMON})'),
 'debt_conversion':('mandatory_common_conversion',rf'(?P<subject>{DEBT})\s+(?P<modal>will|shall|must)\s+(?P<action>{ADV}convert(?:ed)?\s+(?:into|to))\s+(?P<target>{COMMON})'),
 'issuer_conversion_power':('mandatory_common_conversion',rf'(?P<subject>(?:the\s+)?(?:issuer|resolution authority|regulator))\s+(?P<modal>{MOD})\s+(?P<action>{ADV}convert)\s+{DEBT}\s+(?:into|to)\s+(?P<target>{COMMON})'),
 'debt_write_down':('principal_write_down',rf'(?P<subject>{DEBT})\s+(?P<modal>{MOD})\s+(?P<action>{ADV}written[ -]?(?:down|off))\b'),
 'amount_write_down':('principal_write_down',rf'(?P<subject>{AMOUNT}\s+of\s+{DEBT})\s+(?P<modal>{MOD})\s+(?P<action>{ADV}{PASSIVE_WRITE})\b'),
 'issuer_write_down':('principal_write_down',rf'(?P<subject>(?:the\s+)?(?:issuer|resolution authority|regulator))\s+(?P<modal>{MOD})\s+(?:promptly\s+)?(?:\(without[^)]{{0,100}}\)\s*)?(?P<action>{ADV}{WRITE})\s+(?:(?:or\s+cancel|all|a portion|of|the)\s+)*{AMOUNT}\s+of\s+{DEBT}\b'),
 'issuer_notes_write_down':('principal_write_down',rf'(?P<subject>(?:the\s+)?(?:issuer|resolution authority|regulator))\s+(?P<modal>{MOD})\s+(?:promptly\s+)?(?:\([^)]{{0,150}}\)\s*)?(?P<action>{ADV}writ(?:e|ten)[ -]?(?:down|off))\s+{DEBT}\b'),
 'settlement_conversion':('mandatory_common_conversion',rf'(?P<subject>{DEBT})\s+(?P<modal>shall|will|must),?\s+(?:subject to[^;.]{{0,100}},\s*)?(?P<action>be redeemed and settled\s+\(the\s+["“]Conversion["”]\))\s+on[^;.]{{0,100}}?\bby\s+\(x\)\s+the delivery of\s+(?:new\s+)?(?:fully paid\s+)?(?P<target>{COMMON})'),
 'resolution_principal_power':('principal_write_down',rf'(?P<subject>(?:UK\s+)?bail-in power\s+by\s+the\s+(?:relevant\s+)?(?:UK\s+)?authority)\s+which\s+(?P<modal>may|shall|will)\s+(?P<action>result in\s+(?:\(i\)\s+)?the\s+reduction(?:\s+\d+)?\s+or\s+cancellation)\s+of\s+(?:all,?\s+or\s+a\s+portion,?\s+of\s+)?the\s+principal amount of,?\s+(?:or interest on,?\s+)?(?P<target>{DEBT})'),
 'resolution_defined_amounts':('principal_write_down',r'(?P<subject>Bail-In Power\s+(?:\(as defined below\)\s+)?by the Relevant Resolution Authority),?\s+which\s+(?P<modal>may)\s+include and result in[^;.]{0,140}?(?P<action>the reduction)\s+of\s+(?:all,?\s+or\s+a\s+portion,?\s+of\s+)?the\s+(?P<target>Amounts Due)'),
 'release_for_shares':('mandatory_common_conversion',rf'(?P<subject>obligations under\s+(?:the\s+)?(?:Additional Tier 1\s+)?{DEBT})\s+(?P<modal>shall|will)\s+(?P<action>be\s+{ADV}released)\s+(?:[^;.]*?\s+)?in consideration of\s+(?:(?:our|the)\s+)?issuance\s+(?:by\s+[\w’\x27]+\s+)?of\s+(?:the\s+)?(?P<target>{COMMON})'),
 'principal_forfeiture':('principal_write_down',rf'(?P<subject>(?:the\s+)?holders)\s+(?P<modal>permanently)\s+(?P<action>forfeit)\s+their\s+(?:entire\s+)?claim\s+to\s+repayment\s+of\s+(?:the\s+)?{AMOUNT}\s+of\s+{DEBT}\b'),
 'negative_write_down':('no_write_down',rf'(?P<subject>{DEBT})\s+(?P<modal>cannot|can\s+not|will\s+not|shall\s+not|must\s+not)\s+(?P<action>be\s+{ADV}writ(?:e|ten)[ -]?(?:down|off))\b'),
 'negative_conversion':('no_conversion',rf'(?P<subject>{DEBT})\s+(?P<modal>cannot|can\s+not|will\s+not|shall\s+not|are\s+not|is\s+not)\s+(?P<action>(?:be\s+)?convert(?:ed|ible))\b'),
}
COMPILED={key:re.compile(pattern,re.I|re.S) for key,(_,pattern) in RULES.items()}
RISK=re.compile(r'write[ -]?(?:down|off)|written[ -]?(?:down|off)|bail[ -]?in|convert\w*|conversion|forfeit\w*|extinguish\w*|haircut|waiv\w*|loss[ -]absorp|principal|nominal amount|face value|repayment claim',re.I)


def clean(text):
    return re.sub(r'(?<=\w)\s*-\s*(?=\w)','-',text)


def definitions_for(term,definitions):
    """Only explicit definition relations; nearby common-share words do not suffice."""
    target=COMMON_CLASS if term in ('Conversion Shares','Common Shares') else r'(?:outstanding\s+)?principal\s+amount'
    head=re.compile(re.escape(term)+r'["”]?\s+(?:means|shall mean|are(?=\s+(?:(?:the|our)\s+)?(?:ordinary|common|preferred|preference)\s+shares))\s+(?:(?:the|our)\s+)?',re.I)
    result=[]
    for m in head.finditer(definitions):
        meaning=re.match(target,definitions[m.end():],re.I)
        # An unsupported competing definition defeats the binding. Looking
        # only for the desired share class would silently discard a conflict.
        if meaning is None:return []
        end=m.end()+meaning.end()
        result.append({'term':term,'start':m.start(),'end':end,'quote':definitions[m.start():end]})
    return result


def semantic_features(text,definitions=''):
    text=clean(text);result=[]
    for name,pattern in COMPILED.items():
        kind,_=RULES[name]
        for m in pattern.finditer(text):
            before=text[max(0,m.start()-110):m.start()]
            # A quoted heading names another passage; its words do not themselves
            # assert a power here. Only exclude the quoted relation, preserving
            # a separate operative action after the closing quotation.
            in_heading=False
            for heading in re.finditer(r'\b(?:headed|entitled|titled)\s*["“]',text,re.I):
                closing='”' if text[heading.end()-1]=='“' else '"'
                end=text.find(closing,heading.end())
                if heading.end()<=m.start() and (end<0 or m.end()<=end):
                    in_heading=True;break
            if in_heading:continue
            if re.search(r'\bwhen,?\s+if at all\b',before,re.I):continue
            if re.search(r'\b(?:other|another)\s*$',before,re.I):continue
            if re.search(r'\b(?:interest|coupon|dividend)\s+(?:on|of|in respect of)\s*$',before,re.I):continue
            if re.search(r'\b(?:whether|would|could|if the terms were|hypothetically)\b',before,re.I):continue
            if re.search(r'(?:notify|confirm|report|state|disclose|determine)\b.{0,60}$',before,re.I) and kind.startswith('no_') is False:
                continue
            if kind.startswith('no_') and re.search(r'\b(?:unless|except|until|at the start|at the option|save where|provided that|subject to)\b',text,re.I):continue
            option_scope=text[m.start('action'):] if name=='numbered_mandatory_conversion' else text
            if kind=='mandatory_common_conversion' and re.search(
                    r'\b(?:holder|investor)\w*.{0,30}\b(?:option|request|elect\w*)\b|'
                    r'at the option of (?:the )?holders|'
                    r'\b(?:subject to|only with|with)\s+(?:the\s+)?(?:consent|approval)\s+of\s+(?:the\s+)?(?:holders|investors)',
                    option_scope,re.I):continue
            bindings=[]
            target=m.groupdict().get('target','')
            term=('Conversion Shares' if 'conversion shares' in target.lower() else
                  'Common Shares' if 'Common Shares' in target else None)
            if kind=='mandatory_common_conversion' and term:
                bindings=definitions_for(term,definitions)
                if not bindings:
                    result.append({'kind':'candidate','disposition':'unresolved_share_definition','origin':None});continue
            if name=='resolution_defined_amounts':
                bindings=definitions_for('Amounts Due',definitions)
                if not bindings:
                    result.append({'kind':'candidate','disposition':'unresolved_principal_definition','origin':None});continue
            # Conditional source wording is retained in full, never erased.
            witness={'rule':name,'relation':{'start':m.start(),'end':m.end(),'quote':m.group()},
                     'slots':{key:{'start':m.start(key),'end':m.end(key),'text':m.group(key)} for key in m.groupdict()},
                     'definitions':bindings,'mapping_status':'BOUNDED_ENGLISH_CONSTRUCTION_NOT_LEGAL_PROOF'}
            result.append({'kind':kind,'disposition':'applicable','origin':'statutory-disclosed' if re.search(r'bail.in|resolution authority',text,re.I) else 'contractual',
                           'semantic_witness':witness})
    return result


def validate_semantic_witness(item,definitions=''):
    """Replay the construction and every source slot; distrust supplied fact kinds."""
    record=item.get('semantic_witness')
    if not record:return False
    text=clean(item['quote']);rule=record.get('rule')
    if rule not in RULES or item['kind']!=RULES[rule][0]:return False
    relation=record.get('relation',{})
    a,b=relation.get('start'),relation.get('end')
    if type(a) is not int or type(b) is not int or not 0<=a<b<=len(text):return False
    m=COMPILED[rule].fullmatch(text,a,b)
    if not m or relation.get('quote')!=text[a:b]:return False
    expected={key:{'start':m.start(key),'end':m.end(key),'text':m.group(key)} for key in m.groupdict()}
    if record.get('slots')!=expected:return False
    for binding in record.get('definitions',[]):
        if definitions[binding['start']:binding['end']]!=binding['quote']:return False
        if binding not in definitions_for(binding['term'],definitions):return False
    return any(f.get('semantic_witness')==record and f['kind']==item['kind']
               for f in semantic_features(item['quote'],definitions))


def series_binding(text,issue):
    """Bind explicit series/ISIN/maturity references; shared language stays qualified."""
    ids=set(re.findall(r'\b[A-Z]{2}[A-Z0-9]{9}\d\b',text))
    selected=set(issue.get('identifiers',[]))
    if ids and selected and not ids&selected:return 'other_issue'
    year=re.search(r'\bdue\s+(?:\d{1,2}\s+\w+\s+)?((?:19|20)\d{2})\b',issue.get('title',''),re.I)
    years=set(re.findall(r'\b((?:19|20)\d{2})\s+(?:Notes|Debentures|Bonds)\b',text,re.I))
    if year and years and year.group(1) not in years:return 'other_issue'
    series=re.search(r'\bSeries\s+([\w-]+)',issue.get('title',''),re.I)
    references=set(re.findall(r'\bSeries\s+([A-Z0-9]+)(?=\s+(?:Notes|Securities|Bonds))',text,re.I))
    if series and references and series.group(1).casefold() not in {s.casefold() for s in references}:return 'other_issue'
    return 'selected_issue_reference' if ids&selected or (year and year.group(1) in years) or (series and references) else 'shared_terms_scope_premise'


def exact_repayment(text):
    """A final-redemption field must equal its explicitly named calculation unit."""
    money=r'(?P<currency>£|€|GBP|EUR|USD|US\$)\s*(?P<amount>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?)(?![\d,]|\.\d)'
    label=r'(?:\s*\((?:Applicable to (?:the )?Notes in definitive Form\.?|see Conditions|in definitive form|in relation to calculation of interest in global form see Conditions|in relation to calculation of interest on Notes in global form or registered definitive form see Conditions)\))?'
    separator=r'(?:\s*:\s*|\s+)'
    heading=r'(?<!per )\bCalculation Amount'+label+separator
    unit=list(re.finditer(heading+money,text,re.I))
    aliases=list(re.finditer(heading+r'Specified Denominations\b',text,re.I))
    final=list(re.finditer(r'\bFinal Redemption Amount(?: of each Note)?'+label+separator+money+r'\s+per\s+Calculation Amount',text,re.I))
    if aliases and unit:
        return {'status':'unresolved','reason':'Duplicate numeric and aliased calculation fields'}
    if len(list(re.finditer(r'\bFinal Redemption Amount(?: of each Note)?'+label+separator+r'(?:£|€|GBP|EUR|USD|US\$)\s*\d',text,re.I)))>1:
        return {'status':'unresolved','reason':'Duplicate final redemption fields across layouts'}
    if not final:
        inline = list(re.finditer(r'\bFinal Redemption Amount of each Note'+separator+money+
            r'\s+per Note of\s+'+money.replace('currency','unit_currency').replace('amount','unit_amount')+
            r'\s+Specified Denomination\b', text, re.I))
        if inline:
            if len(inline)!=1: return {'status':'unresolved','reason':'Ambiguous per-note redemption fields'}
            m=inline[0]
            currency=lambda v:{'£':'GBP','€':'EUR','US$':'USD'}.get(v.upper(),v.upper())
            value=Fraction(m['amount'].replace(',',''))
            if currency(m['currency'])!=currency(m['unit_currency']) or value!=Fraction(m['unit_amount'].replace(',','')) or value<=0:
                return {'status':'unresolved','reason':'Per-note redemption differs from explicit denomination'}
            return {'status':'equal','format':'per_note','currency':currency(m['currency']),'amount':str(value),
                'fields':[{'field':'final_redemption_per_note','start':m.start(),'end':m.end(),'quote':m.group()}]}
    if not final:
        return ({'status':'unresolved','reason':'Unsupported final redemption money field'}
                if re.search(r'Final Redemption Amount(?: of each Note)?'+label+separator+r'(?:£|€|GBP|EUR|USD|US\$)\s*\d',text,re.I) else None)
    alias_fields=[]
    if aliases and not unit:
        if len(aliases)!=1:return {'status':'unresolved','reason':'Ambiguous calculation-unit alias'}
        # Denomination becomes the calculation unit only through this explicit
        # equality, never by assuming that a minimum denomination is principal.
        unit=list(re.finditer(r'\bSpecified Denominations'+separator+money,text,re.I))
        alias_fields=[{'field':'calculation_amount_alias','start':aliases[0].start(),'end':aliases[0].end(),'quote':aliases[0].group()}]
    if len(unit)!=1 or len(final)!=1:return {'status':'unresolved','reason':'Ambiguous repayment/calculation fields'}
    currency=lambda m:{'£':'GBP','€':'EUR','US$':'USD'}.get(m['currency'].upper(),m['currency'].upper())
    value=lambda m:Fraction(m['amount'].replace(',',''))
    a,b=unit[0],final[0]
    if currency(a)!=currency(b) or value(a)!=value(b) or value(a)<=0:
        return {'status':'unresolved','reason':'Redemption and principal calculation unit differ'}
    return {'status':'equal','currency':currency(a),'amount':str(value(a)),
            'fields':alias_fields+[{'field':name,'start':m.start(),'end':m.end(),'quote':m.group()} for name,m in [('calculation_amount',a),('final_redemption_amount',b)]]}
