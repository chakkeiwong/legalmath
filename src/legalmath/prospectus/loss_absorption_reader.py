"""Bounded, source-bound clause analysis; English conclusions stay qualified.

The inventory supplies document identity and section scope, never expected
answers. Unsupported mechanism language remains visible and blocks a negative.
"""
from bisect import bisect_right
from pathlib import Path
import re

from .common import digest, read, sha
from .loss_absorption import FACTS, decide, explain
from .loss_absorption_witnesses import (RISK, COMPILED, semantic_features, validate_semantic_witness,
                                       series_binding, exact_repayment)
from . import reader_scope


def norm(text):
    return re.sub(r'\s+', ' ', text).strip()


def joined(document):
    parts, starts, cursor = [], [], 0
    for page in document['pages']:
        text = norm(page['text'])
        starts.append(cursor); parts.append(text); cursor += len(text) + 1
    return ' '.join(parts), starts


def definition_scope(text,starts,selection):
    selected=selection.get('operative_pages',[[1,len(starts)]])
    return ''.join(text[a:b] if any(lo<=i+1<=hi for lo,hi in selected) else ' '*(b-a)
                   for i,(a,b) in enumerate(zip(starts,starts[1:]+[len(text)])))


def quote_valid(evidence, document):
    text, starts = joined(document)
    return (evidence['source_sha256'] == document['source_sha256'] and
            0 <= evidence['start'] < evidence['end'] <= len(text) and
            text[evidence['start']:evidence['end']] == evidence['quote'] and
            evidence['page'] == bisect_right(starts, evidence['start']))


WRITE_TERM = r'writ(?:e\s*-?\s*down|ten\s*-?\s*down|e\s*-?\s*off|ten\s*-?\s*off)'
WATCH = re.compile(r'\b(?:'+WRITE_TERM+r'|bail[ -]?in|resolution authority|conver(?:t\w*|sion)|cancel\w*|reduc\w*|loss[ -]absor\w*)\b', re.I)
DEBT = r'\b(?:notes?|securities|bonds?|debentures?)\b'
PRINCIPAL = r'\b(?:principal|nominal|face) (?:amount|value)|\bamounts due\b'
WRITE = r'\b(?:'+WRITE_TERM+r'|reduc\w*|cancel\w*)\b'
COMMON = r'\b(?:ordinary|common) (?:registered )?shares\b|\bcommon (?:capital )?stock\b'


def match(pattern, text):
    return re.search(pattern, text, re.I | re.S)


def _candidate_features(text, *, scope='operative', definitions='', context=''):
    """Recognized lexical/structural constructions, not an English theorem."""
    text = re.sub(r'(?<=\w)\s*-\s*(?=\w)', '-', text)
    result = []
    def add(kind, disposition='applicable', origin=None):
        result.append({'kind': kind, 'disposition': disposition, 'origin': origin})
    cash = (match(DEBT, text) and match(r'\b(?:redeem\w*|repay\w*|matur\w*|redemption)\b', text) and
            (match(r'100(?:\.0+)?\s*(?:%|per cent)|entire principal|redemption at par', text)
             or (match(DEBT+r'.{0,40}\b(?:shall|will) (?:be )?(?:finally )?redeemed\b', text)
                 and match(r'final redemption amount\s*\([^)]{0,150}\bis (?:its |the )?nominal amount\)'
                           r'|final redemption amount (?:is|equals) (?:its |the )?nominal amount', text)))
            and not match(r'no repayment|if the claim for|interest.{0,50}payable semi', text)
            and not match(r'\b(?:not|never|cannot)\b.{0,80}\b(?:redeemed|repaid|repay|redeem)\b'
                          r'|\bredemption\b.{0,60}\b(?:not|never)\b.{0,30}\b100'
                          r'|\b(?:redeemed|repaid)\b.{0,30}\b(?:not|never)\b.{0,30}\b100', text))
    if cash and scope != 'foreign':
        add('cash_repayment')
    if match(DEBT, text) and match(r'\b(?:unsecured|unsubordinated|subordinated)\b.{0,100}\b(?:obligations?|indebtedness)\b|\bdebt (?:securities|instruments)\b', text) and scope != 'foreign':
        add('debt')
    if reader_scope.deferred_interest_forfeiture(text):
        add('candidate', 'distribution_only'); return result
    if scope != 'foreign' and reader_scope.partial_redemption(text):
        add('candidate', 'principal_repaid_in_partial_redemption'); return result
    if scope != 'foreign' and reader_scope.redemption_floor(text, context):
        add('candidate', 'principal_repaid_in_partial_redemption'); return result
    if not WATCH.search(text):
        return result
    if scope == 'foreign':
        add('candidate', 'foreign_document_section'); return result
    # These subjects are distinct from the selected bond's principal.
    if match(r'(?:administrator|administration) (?:of|for) (?:the |an? )?(?:\w+ ){0,3}(?:benchmark|reference rate)|jurisdiction over the administrator', text):
        add('candidate', 'benchmark_administrator'); return result
    if match(r'\b(?:currency|currencies|exchange rate|renminbi|RMB|sterling|foreign exchange|U\.S\. dollars?)\b', text) and match(r'\bconvert|\bconversion', text) and not match(COMMON + '|' + WRITE + '.{0,50}principal', text):
        add('candidate', 'currency_conversion'); return result
    if match(r'convert\w*.{0,100}(?:interest (?:basis|rate)|fixed rate|floating rate)|(?:interest (?:basis|rate)|fixed rate|floating rate).{0,100}convert', text) and not match(COMMON, text):
        add('candidate', 'interest_rate_conversion'); return result
    capital_trigger = match(r'\b(?:bail.in|trigger event|resolution (?:authority|measure)|'+WRITE_TERM+r')\b', text)
    if (match(r'\b(?:purchased|repurchased|redeemed|surrendered|repayment)\b', text) and match(r'\bcancel\w*', text) and not capital_trigger):
        add('candidate', 'repurchase_or_redemption_cancellation'); return result
    if (match(r'pool factor', text) and match(r'\bredeem\w*|\bredemption\b',text) and not capital_trigger) or (match(r'\bso reduced\b',text) and match(r'pool factor',context) and not capital_trigger):
        add('candidate', 'principal_repaid_in_partial_redemption'); return result
    if match(r'(?:principal|nominal) amount.{0,100}reduced by the instalment amount|instalment amount.{0,100}(?:principal|nominal) amount',text) and not capital_trigger:
        add('candidate', 'principal_repaid_in_partial_redemption'); return result
    if match(r'taxable credit|tax purposes',text) and match(r'\bif\b|\bwere\b',text):
        add('candidate', 'tax_consequence_of_hypothetical_mechanism'); return result
    if match(r'(?:majorit|extraordinary resolution|consent of (?:each|all)|consent of the holder of each|(?:amend|modif)\w*.{0,100}consent of (?:the )?holders)', text) and not match(r'\b(?:trigger event|bail.in|resolution authority|automatic conversion)\b', text):
        add('candidate', 'creditor_amendment'); return result
    if match(r'(?:we|the issuer) may (?:issue|offer)|prospectus supplement.{0,90}(?:specify|describe|provide)|terms.{0,80}(?:will|would) be (?:specified|described)|date or dates, if any', text) and scope == 'shelf':
        add('candidate', 'unselected_shelf_option'); return result
    if match(r'shareholders.{0,100}resolution.{0,120}(?:share capital|new shares)|authori[sz]ation.{0,100}any issue of securities', text):
        add('candidate', 'corporate_issuance_authorisation'); return result
    if match(r'\b(?:other|another|any other) (?:\w+ ){0,3}(?:securities|instruments|notes|capital stock)\b|\b(?:exchange|convert) one class|security convertible into|conversion of one class|convertible notes that rank equally', text) and not match(r'\b(?:these|the|our) (?:notes|securities|debentures) (?:will|shall|may|can) (?:be )?(?:convert|writ)', text):
        add('candidate', 'other_security'); return result
    convert = bool(match(r'\b(?:convert\w*|conversion)\b', text))
    principal = bool(match(PRINCIPAL, text))
    debt = bool(match(DEBT, text))
    write_down = bool(match(WRITE, text))
    statutory = bool(match(r'\b(?:bail.in|resolution (?:authority|measure|powers?|regime|laws)|statutory write.down)\b', text))
    origin = 'statutory-disclosed' if statutory else 'contractual' if match(r'\b(?:trigger event|the issuer|shall|terms and conditions)\b',text) else 'unresolved'
    if statutory and match(r'applicable only if.{0,100}(?:scope|implemented)',text):
        add('candidate', 'unresolved_statutory_scope'); return result
    if convert and match(r'(?:at|on|by).{0,25}(?:option|request|election).{0,25}(?:holder|investor)|(?:holder|investor).{0,25}(?:option|elect|request)', text) and not match(r'\b(?:automatic|automatically|trigger event|bail.in)\b', text):
        add('candidate', 'holder_optional_conversion'); return result
    negative = match(DEBT + r' (?:are|is|will be|shall be) (?:not|never) (?:be )?(?:convertible|converted|'+WRITE_TERM+r')', text)
    if negative and match(r'\b(?:unless|except|until|at the start|on that date)\b', text):
        add('candidate', 'unresolved_conditional_negation'); return result
    if negative:
        add('no_conversion' if convert else 'no_write_down'); return result
    common = bool(match(COMMON, text))
    if not common and convert and match(r'\bConversion Shares\b', text) and match(r'conversion shares.{0,200}' + COMMON, definitions):
        common = True
    force = bool(match(r'\b(?:will|shall|automatic|automatically|compulsor\w*|mandatory|power|right to convert)\b', text) or match(r'without.{0,50}consent', text))
    # Require a conversion relation involving this debt, not coexistence of
    # conversion-price, ordinary-share and "shall" words in a definition.
    relation = match(r'\b(?:Notes|Securities|Debentures)\b.{0,100}\bconvert(?:ed)? (?:into|to)\b|\bconvert(?:ed)? (?:the |these |our )?(?:Notes|Securities|Debentures)\b|\bconversion of.{0,100}\b(?:Notes|Securities|Debentures)\b.{0,40}\binto\b|\bAutomatic Conversion\b.{0,120}release.{0,80}obligations.{0,30}(?:Notes|Securities)|\bAutomatic Conversion\b.{0,150}obligations.{0,40}(?:Notes|Securities).{0,80}released', text)
    if convert and common and debt and force and relation:
        add('mandatory_common_conversion', origin=origin)
    elif convert and debt and match(r'\b(?:preferred|preference) (?:shares|stock)\b', text) and not common:
        add('candidate', 'preferred_share_conversion')
    elif convert and debt and not common and force and relation and match(r'\bshares\b|\bequity\b', text):
        add('mandatory_common_conversion', 'unresolved_share_class', origin)
    # Nominal/principal reduction counts even when temporary or only partial.
    # The noun "write-down" alone does not establish whose claim is reduced.
    nominal_definition = match(r'prevailing (?:nominal|principal) amount.{0,350}(?:reduced|'+WRITE_TERM+r')', text)
    explicit_write = match(WRITE_TERM+r'.{0,100}(?:the |each )?(?:Notes|Securities)|(?:Notes|Securities).{0,180}'+WRITE_TERM, text)
    explicit_write = explicit_write and (force or statutory or bool(match(r'\bmay be\b.{0,60}'+WRITE_TERM+r'|\b(?:upon|after|following).{0,70}trigger event',text)))
    reductions = list(re.finditer(r'(?:reduc\w*|cancel\w*).{0,120}(?:principal amount|nominal amount|amounts due)|(?:principal amount|nominal amount|amounts due).{0,110}reduc\w*',text,re.I))
    operative_reduction = any(not match(r'\binterest\b|\bcoupon\b', m.group()) for m in reductions)
    if write_down and debt and (nominal_definition or explicit_write or (principal and operative_reduction and (force or statutory))):
        if not match(r'market (?:price|value)|tax (?:rate|liabilit)|withholding|taxation', text):
            add('principal_write_down', origin=origin)
    if result and any(r['kind'] in ('principal_write_down', 'mandatory_common_conversion') for r in result):
        return result
    if match(r'\b(?:interest|coupon|dividend)\w*\b', text) and not principal and not common:
        add('candidate', 'distribution_only'); return result
    if match(r'\b(?:capital requirement|capital ratio|risk.weighted assets|CET1)\b', text) and not (principal or (debt and match(r'write.down|written.down', text))):
        add('candidate', 'capital_requirement_only'); return result
    if match(r'\b(?:market value|market price|credit rating|tax|earnings|profit|cost|emission|revenue|dilution|redemption price|rate of interest)\b', text) and not (principal and match(r'write.down|written.down|bail.in', text)):
        add('candidate', 'market_tax_or_other_amount'); return result
    if scope == 'shelf' and convert:
        add('candidate', 'unselected_shelf_option'); return result
    if (principal and write_down) or (convert and debt and match(r'shares|equity', text)) or (statutory and debt):
        add('candidate', 'unresolved_mechanism')
    else:
        add('candidate', 'no_principal_or_common_share_mechanism')
    return result


def clause_features(text, *, scope='operative', definitions='', context=''):
    """Retrieve broadly, then require an action-bound witness for mechanism facts."""
    candidates=_candidate_features(text,scope=scope,definitions=definitions,context=context)
    if scope=='foreign':return candidates
    ordinary=[r for r in candidates if r['kind'] not in
              {'principal_write_down','mandatory_common_conversion','no_write_down','no_conversion'}]
    # Unselected form fields are not a repayment promise for a selected issue.
    if '[' in text and ']' in text:
        ordinary=[r for r in ordinary if r['kind']!='cash_repayment']
        if scope=='shelf':
            return ordinary+[{'kind':'candidate','disposition':'unselected_shelf_option','origin':None}]
    exempt={'creditor_amendment','unselected_shelf_option','holder_optional_conversion',
            'preferred_share_conversion','foreign_document_section','other_security',
            'corporate_issuance_authorisation','tax_consequence_of_hypothetical_mechanism',
            'principal_repaid_in_partial_redemption','repurchase_or_redemption_cancellation',
            'distribution_only','unresolved_statutory_scope'}
    if any(r['disposition'] in exempt for r in candidates):
        # An optional conversion does not exempt a distinct, action-bound
        # principal write-down in the same sentence. Other exempt contexts
        # remain subject to their existing scope checks.
        if all(r['disposition'] in {'holder_optional_conversion','preferred_share_conversion'}
               for r in candidates if r['disposition'] in exempt):
            separate=[r for r in semantic_features(text,definitions) if r['kind']=='principal_write_down']
            if separate:return ordinary+separate
        return ordinary
    semantic=semantic_features(text,definitions)
    if semantic:
        return [r for r in ordinary if r['kind']!='candidate']+semantic
    mechanism_candidates=[r for r in candidates if r['kind'] in
                          {'principal_write_down','mandatory_common_conversion','no_write_down','no_conversion'}]
    if mechanism_candidates:
        return ordinary+[{'kind':'candidate','disposition':'unresolved_action_or_polarity','origin':None}]
    alternative_loss=match(r'\b(?:forfeit\w*|extinguish\w*|haircut)\b',text)
    alternative_loss = alternative_loss or match(
        r'\bsurrender\w*\s+(?:(?:all|any|their|the|its)\s+)*(?:rights?|claims?)\b.{0,80}\b(?:principal|repayment)\b'
        r'|\b(?:principal|repayment|nominal|face value)\b.{0,60}\b(?:lapse|impairment|impaired|abandon)\w*\b'
        r'|\bimpairment\s+of\s+(?:the\s+)?principal\b'
        r'|\bdischarg\w*\b.{0,50}\bwithout\b.{0,30}\b(?:payment|repayment)\b', text)
    conditional_denial = match(
        r'\b(?:cannot\s+(?:be\s+)?(?:written|converted)|not convertible|not be written)\b',text) and match(
        r'\b(?:save where|provided that|subject to)\b',text)
    if conditional_denial:
        ordinary=[r for r in ordinary if r['kind'] not in {'no_conversion','no_write_down'}]
        ordinary.append({'kind':'candidate','disposition':'unresolved_conditional_negation','origin':None})
    alternative_loss=alternative_loss or match(r'waiv\w*\s+(?:(?:their|the|all|any|rights?|claims?|to|for|of)\s+)*(?:principal|repayment)',text)
    missing_dependency=match(r'\b(?:schedule|appendix|supplement|incorporated document|conditions)\b.{0,100}\b(?:unavailable|not (?:provided|included|supplied)|missing)\b',text)
    if RISK.search(text) and (alternative_loss or missing_dependency):
        ordinary.append({'kind':'candidate','disposition':'unresolved_operative_wording','origin':None})
    return ordinary


def segments(text):
    # Join page boundaries before segmenting so a page split cannot hide a clause.
    start = 0
    independent = (r',\s+(?:and|but|whereas)\s+(?=(?:the\s+)?'
                   r'(?:(?:principal|nominal)\s+amount\s+of\s+(?:the\s+)?Notes\s+(?:shall|will|may|must)'
                   r'|holders\s+shall\s+(?:surrender|forfeit)'
                   r'|Issuer\s+(?:shall|will|must)\s+(?:write|reduce|convert)))')
    for boundary in re.finditer(r'(?<=[.;])\s+(?=[A-Z“"(])|' + independent, text):
        if boundary.group().startswith(','):
            head = text[start:boundary.start()]
            tail = text[boundary.end():]
            stop = re.search(r'(?<=[.;])\s+(?=[A-Z“"(])', tail)
            tail = tail[:stop.start()] if stop else tail
            # A shared consent/conditional head still governs coordinated actions.
            # Split only an explicit independent loss condition; a reduction by
            # cash paid is still part of the redemption relation.
            if (match(r'\b(?:if|unless|provided that|subject to|with the consent)\b', head)
                    or not match(r'\b(?:Solvency Event|Trigger Event|Capital Event|bail.in|surrender|forfeit)\b', tail)):
                continue
        end = boundary.start()
        if end > start:
            yield start, end
        start = boundary.end()
    if start < len(text):
        yield start, len(text)


def analyze_document(row, document, selection, issue=None):
    text, starts = joined(document)
    evidence = []
    selected = selection.get('operative_pages', [[1, len(starts)]])
    shelf = selection.get('shelf_pages', [])
    priority = selection.get('evidence_priority_pages', [])
    reader_scope.validate(selection, len(starts))
    def page_scope(page):
        return 'operative' if any(a <= page <= b for a, b in selected) else 'shelf' if any(a <= page <= b for a, b in shelf) else 'foreign'
    # Preserve offsets but exclude definitions belonging to unselected pages.
    definition_text=definition_scope(text,starts,selection)
    # Never assign a sentence spanning two distinct document sections solely
    # by its first page. Preserve joins only within the same scope.
    cuts = [0] + [starts[i] for i in range(1, len(starts)) if page_scope(i) != page_scope(i+1)] + [len(text)]
    spans = [(left + a, left + b) for left, right in zip(cuts, cuts[1:])
             for a, b in segments(text[left:right])]
    predecessors = {}
    for (a, b), (start, end) in zip(spans, spans[1:]):
        if (text[b:start].strip() == '' and
                bisect_right(cuts, a) == bisect_right(cuts, start)):
            predecessors[start] = (a, b)
    # Keep a scoped numbered obligation together even when semicolons would
    # separate the action from its governing actor and modal. Never join across
    # a declared source-section boundary. Retain the remainder of the action's
    # sentence so an option/qualification after the share class is not erased.
    for left, right in zip(cuts, cuts[1:]):
        for relation in COMPILED['numbered_mandatory_conversion'].finditer(text,left,right):
            start=next((a for a,b in spans if a <= relation.start() < b),relation.start())
            end=next((b for a,b in spans if a <= relation.end()-1 < b),relation.end())
            span=(start,end)
            if span not in spans:spans.append(span)
    for start, end in spans:
        clause = text[start:end]
        page = bisect_right(starts, start)
        scope = page_scope(page)
        antecedent = predecessors.get(start)
        previous = text[antecedent[0]:antecedent[1]] if antecedent else ''
        for feature in clause_features(clause, scope=scope, definitions=definition_text, context=previous):
            binding=series_binding(clause,issue or {})
            if binding=='other_issue':
                feature={**feature,'disposition':'other_issue'}
            item = {'document': row['id'], 'source_sha256': document['source_sha256'],
                    'start': start, 'end': end, 'page': page, 'end_page': bisect_right(starts, end - 1),
                    'quote': clause, 'scope': scope,
                    'priority': 0 if any(a <= page <= b for a,b in priority) else 1 if scope == 'operative' else 2,
                    'issue_id':(issue or {}).get('id'),'issue_binding':binding,**feature}
            if text[start:end] != item['quote'] or not (0 <= start < end <= len(text)):
                raise ValueError('Invalid quotation location')
            if antecedent and reader_scope.redemption_floor(clause, previous):
                item['context_witness'] = {'start': antecedent[0], 'end': antecedent[1],
                    'quote': previous, 'page': bisect_right(starts, antecedent[0]),
                    'end_page': bisect_right(starts, antecedent[1]-1)}
            item['id'] = digest(item)[:24]
            evidence.append(item)
    repayment=exact_repayment(text)
    if repayment and repayment['status']=='equal':
        fields=repayment['fields'];start=min(f['start'] for f in fields);end=max(f['end'] for f in fields)
        # A benchmark bond in the intervening text does not bind these fields.
        # Include only the fields and explicit statements assigning them to an issue.
        assignments = re.findall(r'\b(?:these |the )?(?:fields|amounts)\s+(?:apply|relate)\s+to\s+[^.]{1,160}',
                                 text[start:end], re.I)
        bound_text = ' '.join([f['quote'] for f in fields] + assignments)
        if (all(page_scope(p)=='operative' for f in fields for p in range(
                bisect_right(starts,f['start']), bisect_right(starts,f['end']-1)+1))
                and series_binding(bound_text, issue or {}) != 'other_issue'):
            item={'document':row['id'],'source_sha256':document['source_sha256'],'start':start,'end':end,
                  'page':bisect_right(starts,start),'end_page':bisect_right(starts,end-1),'quote':text[start:end],
                  'scope':'operative','priority':0,'kind':'cash_repayment','disposition':'applicable','origin':None,
                  'issue_id':(issue or {}).get('id'),'issue_binding':'selected_document_fields',
                  'repayment_derivation':repayment}
            item['id']=digest(item)[:24];evidence.append(item)
    elif repayment:
        issues={'document':row['id'],'source_sha256':document['source_sha256'],'start':0,'end':len(text),
                'page':1,'end_page':len(starts),'quote':text,'scope':'operative','priority':0,
                'kind':'candidate','disposition':'unresolved_repayment_units','origin':None,
                'issue_id':(issue or {}).get('id'),'issue_binding':'selected_document_fields'}
        issues['id']=digest(issues)[:24];evidence.append(issues)
    return evidence


def evidence_order(item):
    """Prefer operative actions to definitions when rendering a short reason.

    This ordering affects presentation, not the classification predicate.
    """
    text = item['quote']
    kind = item['kind']
    direct = False
    if kind == 'cash_repayment':
        direct = bool(match(r'redemption basis|redemption/payment basis|final redemption:|entire principal amount', text))
    elif kind == 'principal_write_down':
        direct = bool(match(r'\bshall\b.{0,100}'+WRITE_TERM+r'|\bshall be\b.{0,100}reduced|(?:will|shall) automatically be written|exercise.{0,100}bail.in power|bound by.{0,200}bail.in power', text))
    elif kind == 'mandatory_common_conversion':
        direct = (item.get('semantic_witness',{}).get('rule')=='numbered_mandatory_conversion' or
                  bool(match(r'automatic conversion.{0,40}(?:is|shall|will)|upon (?:the )?occurrence.{0,60}trigger event|shall.{0,50}convert', text)))
    return (0 if item['scope']=='operative' and direct else 1, item['priority'],
            1 if match(r'"|“',text[:1]) else 0, item['page'], item['start'])


def load_document(row, root):
    original, path = Path(root) / row['original'], Path(root) / row['text']
    if not original.exists() or not path.exists():
        raise ValueError('Missing document: ' + row['id'])
    if sha(original.read_bytes()) != row['sha256'] or sha(path.read_bytes()) != row['text_sha256']:
        raise ValueError('Source or extraction hash mismatch: ' + row['id'])
    document = read(path)
    if document['source_sha256'] != row['sha256']:
        raise ValueError('Extraction belongs to another original: ' + row['id'])
    if len(document['pages']) != row['pages'] or [p['page'] for p in document['pages']] != list(range(1, row['pages'] + 1)):
        raise ValueError('Missing/reordered pages: ' + row['id'])
    if document.get('preliminary_indicator'):
        raise ValueError('Preliminary terms cannot replace final terms: ' + row['id'])
    text, _ = joined(document)
    if any(norm(marker).lower() not in text.lower() for marker in row.get('identity_markers', [])):
        raise ValueError('Document identity/edition mismatch: ' + row['id'])
    return document


def analyze_issue(issue, documents, root):
    evidence, issues, coverage, checked_documents = [], [], [], {}
    for selection in issue['documents']:
        key = selection['id']
        if key not in documents:
            issues.append('Missing required source ' + key); continue
        row = documents[key]
        try:
            document = load_document(row, root)
            text, starts = joined(document)
            reader_scope.validate(selection, len(starts))
            checked_documents[key]={'text':text,'sha256':row['sha256'],
                                    'definition_text':definition_scope(text,starts,selection)}
            if any(norm(marker).lower() not in text.lower() for marker in selection.get('required_markers', [])):
                raise ValueError('Issue/edition link is not present in ' + key)
            for locator in selection.get('required_page_markers', []):
                page = locator['page']
                if (type(page) is not int or not 1 <= page <= len(document['pages']) or
                        norm(locator['text']).lower() not in norm(document['pages'][page-1]['text']).lower()):
                    raise ValueError('Issue/edition marker missing from its required page in ' + key)
            evidence.extend(analyze_document(row, document, selection, issue))
            coverage.append({'document': key, 'pages_read': len(document['pages']), 'sha256': row['sha256'],
                             'operative_pages': selection.get('operative_pages', [[1, len(document['pages'])]]),
                             'required_page_markers': selection.get('required_page_markers', []),
                             'scope_basis': selection.get('scope_basis', 'Dated issue terms; English applicability is a qualified premise')})
        except (OSError, ValueError, KeyError) as exc:
            issues.append(str(exc))
    issues.extend(issue.get('unresolved_operative_dependencies', []))
    facts = dict.fromkeys(FACTS, None)
    if issue.get('security_type') == 'preferred_share':
        facts['debt'] = False
    else:
        facts['debt'] = True if any(e['kind'] == 'debt' and e['disposition'] == 'applicable' for e in evidence) else None
    ordinary = {'distribution_only': 'coupon/dividend provisions', 'repurchase_or_redemption_cancellation': 'cancellation after repayment or repurchase',
                'principal_repaid_in_partial_redemption': 'principal reduction through cash redemption',
                'creditor_amendment': 'creditor-approved amendments', 'holder_optional_conversion': 'holder-optional conversion',
                'interest_rate_conversion': 'interest-rate conversion', 'currency_conversion': 'currency conversion',
                'benchmark_administrator': 'benchmark-administrator resolution'}
    unresolved = [e for e in evidence if e['disposition'].startswith('unresolved')]
    cash = any(e['kind'] == 'cash_repayment' and e['disposition'] == 'applicable' for e in evidence)
    for name in ('principal_write_down', 'mandatory_common_conversion'):
        positive = any(e['kind'] == name and e['disposition'] == 'applicable' for e in evidence)
        negative_kind = 'no_write_down' if name == 'principal_write_down' else 'no_conversion'
        negative = any(e['kind'] == negative_kind and e['disposition'] == 'applicable' for e in evidence)
        facts[name] = 'conflict' if positive and negative else True if positive else None if unresolved else False
    facts['coverage_complete'] = bool(not issues and not unresolved and cash and coverage)
    if not cash and not any(facts[k] is True for k in ('principal_write_down', 'mandatory_common_conversion')):
        issues.append('Affirmative principal repayment terms have not been resolved')
    if unresolved:
        issues.append(str(len(unresolved)) + ' potentially relevant clauses require scope/meaning resolution')
    if facts['debt'] is None:
        issues.append('Debt status is not established from the selected terms')
    # Physical/identity/dependency failures defeat even a plausible positive.
    hard_failure = len(coverage) != len(issue['documents']) or bool(issue.get('unresolved_operative_dependencies'))
    if hard_failure:
        facts = dict.fromkeys(FACTS, None)
    decision = decide(facts)
    evidence.sort(key=evidence_order)
    for item in evidence:
        if item['disposition']=='applicable' and item['kind'] in ('principal_write_down','mandatory_common_conversion','no_write_down','no_conversion'):
            definition_text=checked_documents[item['document']]['definition_text']
            if not validate_semantic_witness(item,definition_text):
                raise ValueError('Invalid semantic witness: '+item['id'])
    used=[e['id'] for e in evidence if e['disposition']=='applicable' and
          ((decision['answer'] is True and e['kind'] in ('principal_write_down','mandatory_common_conversion')) or
           (decision['answer'] is False and e['kind']=='cash_repayment'))]
    derivation={'version':'bond-feature-derivation.v2','issue_id':issue['id'],'facts':dict(facts),
                'answer':decision['answer'],'evidence_ids':used,'coverage_basis':'DECLARED_SOURCES_AND_BOUNDED_CONSTRUCTIONS',
                'english_entailment':'NOT_PROVED','absence_proof':'NOT_PROVED',
                'source_dependencies':[{'document':c['document'],'sha256':c['sha256']} for c in coverage]}
    derivation['sha256']=digest(derivation)
    explanation = explain(decision, evidence, issues=issues,
                          ordinary_features=[ordinary[e['disposition']] for e in evidence if e['disposition'] in ordinary])
    result={**{k: v for k, v in issue.items() if k != 'documents'}, **decision, 'summary_reason': explanation,
            'facts': facts, 'evidence': evidence, 'coverage': coverage, 'open_issues': issues,'derivation':derivation,
            'certified_legal_answer':None,
            'qualification': 'Conditional on the declared issue/document scope and bounded English analysis. Source meaning, relevance of omitted material and later amendments are not independently proved.',
            'legal_entailment': 'NOT_PROVED', 'human_quality_evidence': False}
    from .loss_absorption_derivation import check, render
    result['summary_reason']=render(result)
    result['summary_evidence_ids']=derivation['evidence_ids'][:1]
    if not hard_failure:
        result['derivation_check']=check(result,checked_documents)
    else:
        result['derivation_check']={'status':'SOURCE_INCOMPLETE','source_meaning':'NOT_PROVED'}
    return result
