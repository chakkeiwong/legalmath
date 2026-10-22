"""Independently inspected remaining occurrence identities and interpretations."""
from copy import deepcopy
from legalmath.prospectus.successor.contracts import digest

KEY='definition_remainder_review'
VERSION='definition-remainder-review.v1'
# Exact pairs preserve nested matches with a common start.
PAIR_TEXT={
'D13':'5647:5676 6073:6100 28917:28944 29162:29189 29424:29451 29602:29629',
'D14':'6487:6503 6802:6817 12494:12509',
'D15':'7355:7373 7407:7423 7426:7442',
'D16':'7570:7593 7634:7657',
'D17':'8813:8817 8833:8837 8907:8911',
'D18':'9344:9351 9454:9461 9535:9542 9716:9723 22964:22971',
'D19':'9932:9938',
'D20':'6634:6648 6946:6956 7033:7043 9363:9377 10859:10873 11354:11368 27291:27301 28615:28629 29783:29793',
'D21':'10163:10181 10225:10243 10281:10299 11313:11331 11391:11409 11843:11861 17567:17585 17768:17786 18416:18434 19131:19149 21187:21205 21317:21335 21414:21432 21463:21481 21558:21576 21611:21629 28414:28432',
'D22':'13649:13669 15740:15760 15829:15849 15914:15937',
'D23':'14092:14105 14112:14125 14358:14371 14618:14631',
'D24':'14130:14133 14166:14169 14704:14707 14819:14822',
'D25':'14173:14180 14200:14207 14727:14734 14841:14848',
'D26':'14214:14219 14246:14251 14712:14717 14827:14832',
'D27':'13580:13601 14424:14445',
'D28':'13472:13487 13499:13514 13616:13632 14466:14481 14918:14933 15582:15598',
'D29':'15007:15030 15189:15210',
'D30':'13546:13570 14518:14542 15506:15529',
'D32':'13768:13790 15864:15886 16141:16163 16507:16529',
'D33':'15680:15698 16189:16206',
'D34':'16369:16387 16413:16431 16585:16603 16801:16819',
'D35':'19073:19112 19184:19224 19664:19703',
'D36':'22296:22328 22369:22400',
'D37':'22420:22447 22920:22947',
'D38':'2525:2544 24544:24562 24568:24587',
'D39':'10578:10598 12560:12581 12941:12961 13164:13185 25742:25762 25769:25789 26066:26086 28067:28086',
'D40':'32492:32512 32640:32660 32755:32775 33055:33075 33216:33236 33736:33756',
'D42':'34924:34929 35008:35013 35693:35698 35964:35969 36016:36021 37235:37240',
'D43':'37477:37488 37880:37891 37987:37998 38106:38117 38859:38870 38985:38996 39025:39036 39043:39054 39364:39375 39701:39712 40311:40322',
'D44':'44239:44259 44432:44444 44480:44492 46086:46099',
'U02':'5538:5545 7781:7788 7804:7811 10004:10011 10069:10076 10636:10643 26360:26367 27331:27338 28544:28551 32291:32298',
'U03':'5550:5556 6725:6731 6887:6893 7198:7204 7238:7244 8041:8047 8065:8071 8271:8277 9615:9621 10016:10022 10485:10491 10648:10654 11960:11966 13989:13995 17711:17717 19256:19262 21276:21282 26373:26379 27344:27350 28497:28503 28557:28563 32304:32310',
'U04':'17427:17459 17512:17532 17732:17752 17732:17762 19085:19105 19196:19224 19676:19696 22991:23019',
'U05':'10276:10306 17561:17601 17763:17801 18411:18441',
'U08':'1191:1203 5561:5573 11745:11757 16249:16261 16889:16901 23156:23168 23312:23324 23528:23540 23852:23865 23959:23971 24113:24125 24855:24867 28825:28837 31693:31705 32059:32071 32850:32862 33782:33794 42351:42363 43658:43670 43757:43769',
'U09':'23197:23207 23329:23339 23548:23558 23877:23887 24001:24012 24874:24884',
'U10':'21769:21786 21975:21992 23237:23254 23466:23483 23567:23584 23897:23914 24030:24047 24157:24174 24893:24910',
'U11':'27684:27708',
'U12':'15069:15109 15111:15115',
'U13':'36160:36180 36222:36243 36466:36487 36569:36590 36626:36646 37072:37092 37184:37206',
'M01':'7725:7736','M02':'1769:1783','M03':'38231:38242 38328:38339','M04':'41382:41399'}
PAIRS={k:[tuple(map(int,x.split(':'))) for x in v.split()] for k,v in PAIR_TEXT.items()}

# These are finite source readings. Full declarations/support remain alongside them.
READINGS={
'D13':('Capital-market debt retains borrowed-money, original-maturity greater than one year and actual or potential listing/trading requirements; section9(c) expressly reuses section2(2).',['ACTUAL_DEBT_CLASSIFICATION_OPEN']),
'D14':('Interest is payable annually in arrears on March8, separately from the initial payment and payment-day adjustment; the tax call expressly reuses section3(1).',['ACTUAL_PAYMENT_CALENDAR_OPEN']),
'D15':('The numerator is actual days in the calculation interval; the denominator is actual days in the relevant Zinsperiode, whose literal definition is missing.',['DENOMINATOR_INTEREST_PERIOD_UNDEFINED']),
'D16':('The calculation interval is the arbitrary period for which interest is calculated; it does not define the denominator interest period.',['DENOMINATOR_INTEREST_PERIOD_UNDEFINED']),
'D17':('Code denotes the printed U.S. Internal Revenue Code of1986 in the withholding reservation.',['HISTORICAL_LEGISLATION_AND_APPLICATION_OPEN']),
'D18':('The payment-adjustment definition excludes weekends and requires clearing-system and relevant TARGET2 opening. Its express purpose limit leaves calculation-day reuse requiring qualified interpretation.',['CALCULATION_DAY_SCOPE_IMPORT_OPEN','ACTUAL_CALENDAR_OPEN']),
'D19':('TARGET abbreviates the printed Trans-European Automated Real-time Gross Settlement Express Transfer System2.',['DATED_OPERATIONAL_CALENDAR_OPEN']),
'D20':('Section5(1) specifies8March2032 subject to prior redemption/purchase/cancellation. Ordinary due-date uses cannot all be replaced by that date.',['LATE_INTEREST_DUE_DATE_SCOPE_OPEN','ACTUAL_DUE_EVENTS_OPEN']),
'D21':('The nominal redemption amount is principal per note; a token within an early or call amount label is not independently this definition.',['ACTUAL_PRINCIPAL_OPEN']),
'D22':('The holder-option event combines control change with a causal qualifying rating event in the specified period; the earlier tax-notice exception and exercise requirements remain.',['ACTUAL_EVENT_AND_CAUSATION_OPEN']),
'D23':('Eligible agencies include the three named entities, their successors, or another agency selected by BASF of comparable international standing.',['ACTUAL_SUCCESSOR_OR_SELECTION_OPEN']),
'D24':('S&P denotes S&P Global Ratings Europe Limited in this holder option; its printed thresholds belong to the local rating condition.',['RAW_RATING_CLASSIFICATION_OPEN']),
'D25':('Moodys alias denotes Moodys Deutschland GmbH; retain the exact source spelling and Baa3/Ba1 threshold distinctions.',['RAW_RATING_CLASSIFICATION_OPEN']),
'D26':('Fitch denotes Fitch Ratings Ireland Limited, including the slash-adjacent threshold uses retained by the source dossier.',['RAW_RATING_CLASSIFICATION_OPEN','LEXICAL_RECALL_NOT_ESTABLISHED']),
'D27':('Withdrawal of a previously assigned eligible rating or the defined investment-to-noninvestment change in the period is required; the event clause separately requires causation.',['RAW_RATING_CLASSIFICATION_OPEN','ACTUAL_EVENT_AND_CAUSATION_OPEN']),
'D28':('The control condition retains concert-party or instructed-third-party attribution and strictly more than50percent of votes, independent of board consent.',['ACTUAL_VOTES_ATTRIBUTION_AND_HISTORICAL_LAW_OPEN']),
'D29':('Relevant persons are the person or persons in the source concert-party control test; persons acting on their instructions remain separate participants.',['ACTUAL_CONCERT_AND_ATTRIBUTION_OPEN']),
'D30':('The control period ends120days after the control event and is distinct from the45day exercise period.',['EVENT_DATE_AND_COUNTING_PREMISES_OPEN']),
'D32':('The issuer notice describes the defined event and holder-option procedure under section13; publication starts the exercise period.',['ACTUAL_NOTICE_PUBLICATION_OPEN']),
'D33':('The exercise period is45days after publication, with the separate17:00Frankfurt receipt cutoff retained; its end enters the holder redemption-day rule.',['ACTUAL_NOTICE_RECEIPT_AND_COUNTING_OPEN']),
'D34':('The holder exercise declaration is sent to the designated Fiscal Agent office in text or written form and retains deadline, content, irrevocability and delivery requirements.',['ACTUAL_EXERCISE_AND_DELIVERY_OPEN']),
'D35':('The early issuer call date is the section5(5) date, with notice30to60days before and accrued interest excluding that date; it is distinct from the table-call name.',['ACTUAL_CALL_OPEN','CALCULATION_DAY_NAME_AMBIGUITY']),
'D36':('Comparable benchmark yield selects a German euro reference bond of comparable remaining maturity to8March2032 using stated market practice at the calculation day; spread is a separate0.300percentage points.',['BENCHMARK_MARKET_INPUTS_OPEN','CALCULATION_DAY_NAME_AMBIGUITY']),
'D37':('The printed calculation day is the third payment day before Wahl-Ruckzahlungstag(Call); the make-whole context suggests the early call while the literal label matches the table call. Neither alternative is selected here.',['CALCULATION_DAY_NAME_AMBIGUITY','PAYMENT_DAY_SCOPE_IMPORT_OPEN']),
'D38':('United States is the expressly declared territory including states,DC and listed territories, reused in exchange delivery; it does not define person tax status.',['ACTUAL_DELIVERY_LOCATION_OPEN','US_PERSON_STATUS_NOT_DEFINED_BY_GEOGRAPHY']),
'D39':('Additional amounts restore net amounts only under the full gross-up condition, all(a)-(e)exceptions and the final German withholding-tax exclusion.',['HISTORICAL_TAX_LAW_AND_FACTS_OPEN']),
'D40':('A successor principal debtor is a qualifying affiliate only subject to all section10(a)-(e)conditions and associated notice/amendment provisions.',['ACTUAL_SUBSTITUTION_AND_LEGAL_PREDICATES_OPEN']),
'D42':('SchVG is the printed statute alias; sections5ff remain open references and a current edition cannot establish the2022 position.',['HISTORICAL_STATUTORY_VERSION_AND_APPLICATION_OPEN']),
'D43':('Einberufung denotes the meeting call, retaining its content, notice, registration,participation and permitted variations.',['ACTUAL_MEETING_NOTICE_OPEN']),
'D44':('The jurisdiction provision labels note-related proceedings and is nonexclusive; enforcement uses retain procedural qualifications and do not establish standing.',['ACTUAL_PROCEEDING_AND_PROCEDURAL_LAW_OPEN']),
'U02':('References to capital expressly include applicable nominal,early,call,premium and other payable amounts; scope remains conditional on applicability.',['APPLICABLE_PAYMENT_CATEGORY_AND_AMOUNT_OPEN']),
'U03':('References to interest include applicable section7additional amounts without erasing tax exceptions or the no-extra-delay-interest rule.',['APPLICABLE_INTEREST_AND_TAX_PREMISES_OPEN']),
'U04':('The table-call window is8December2031to7March2032; shorter components of the early-call name are different-purpose uses, and calculation-day wording remains ambiguous.',['ACTUAL_CALL_OPEN','CALCULATION_DAY_NAME_AMBIGUITY']),
'U05':('The table-call amount is aggregate nominal principal for that option; column labels and operative references keep their separate roles.',['ACTUAL_PRINCIPAL_AND_CALL_OPEN']),
'U08':('The initial Fiscal Agent is Deutsche Bank Aktiengesellschaft at the printed Frankfurt address; current role,office changes and replacement depend on separate source conditions.',['ACTUAL_CURRENT_APPOINTMENT_AND_OFFICE_OPEN']),
'U09':('The initial Paying Agent shares the Deutsche Bank appointment; plural or replacement roles do not establish every future agent identity.',['ACTUAL_CURRENT_APPOINTMENT_AND_OFFICE_OPEN']),
'U10':('The construction retains its name/office placeholder, while exact final-term authority separately names NatWest Markets N.V. as Calculation Agent. Its office and actual/current appointment remain open; Deutsche Banks office cannot be imported.',['CALCULATION_AGENT_OFFICE_UNRESOLVED','ACTUAL_CURRENT_APPOINTMENT_OPEN']),
'U11':('The parenthetical identifies the Tax Haven Defence Act dated25June2021 as amended, including regulations; it does not prove residence or an applicable noncooperative-jurisdiction list.',['HISTORICAL_LAW_RESIDENCE_AND_LIST_OPEN']),
'U12':('The full statutory name and WpUG acronym refer to section30(2)within the concert-party condition.',['HISTORICAL_STATUTORY_VERSION_AND_CONCERT_OPEN']),
'U13':('A common representative may be appointed by majority; powers,instructions,individual-exercise restrictions,reporting and statutory requirements remain conditional.',['ACTUAL_APPOINTMENT_POWERS_AND_HISTORICAL_LAW_OPEN']),
'M01':('Zinsperiode is used as the denominator period without a literal current declaration; do not substitute the numerator calculation period or absent historical Bezugsperiode.',['MISSING_INTEREST_PERIOD_DEFINITION']),
'M02':('US-person status and exceptions arise in the tax certification condition; the contractual territory definition does not supply that status rule.',['MISSING_PERSON_STATUS_RULE','HISTORICAL_US_TAX_LAW_AND_FACTS_OPEN']),
'M03':('Unless the call provides otherwise,a voting ticket issued by the appointed agent gives participation/voting access subject to the stated six-day deposit or blocking/proof alternatives.',['ACTUAL_TICKET_HOLDING_AND_NOTICE_OPEN']),
'M04':('The vote-recipient label is contextually related to section11(4):issuer-commissioned notary or the common representative if it called the vote. No actual person is identified.',['ACTUAL_CHAIR_APPOINTMENT_AND_CALL_OPEN'])}

SUPPORT={'D13':[(5381,6457),(28908,30278)],'D14':[(6470,6870)],
'D15':[(7179,7737)],'D16':[(7403,7737)],'D18':[(9338,9981),(22919,23020)],
'D20':[(6470,7179),(9338,9981),(10613,11128),(11144,11385)],
'D21':[(9982,10612),(11386,11499),(17242,17851),(21298,23020)],
'D35':[(18874,20224)],'D36':[(21483,23020)],'D37':[(17242,17851),(18874,19276),(21483,23020)],
'D40':[(32191,34657)],'D43':[(37242,40353)],'D44':[(44083,46125)],
'U02':[(9982,10612),(25146,28126)],'U03':[(9338,9981),(9982,10612),(25146,28126)],
'U04':[(17242,17851),(18874,19276),(22919,23020)],
'U08':[(23086,25134)],'U09':[(23086,25134)],'U10':[(21483,23020),(23086,25134)],
'U13':[(36031,36268),(36462,37241)],'M01':[(6459,7745)],
'M02':[(1322,2596),(24491,24809)],'M03':[(37977,38969)],'M04':[(36031,36268),(41117,41637)]}
for _key in ('D22','D23','D24','D25','D26','D27','D28','D29','D30','D32','D33','D34','U12'):
    SUPPORT[_key]=[(13468,17241)]

P3={
'D13':['basf-pledge:capital-market-debt'],
'D14':['basf-payment:coupon_dates','basf-payment:first_coupon'],
'D15':['basf-payment:day_count'],'D16':['basf-payment:day_count'],
'D17':['basf-payment:payment_currency'],'D18':['basf-payment:payment_day'],
'D19':['basf-payment:payment_day'],'D20':['basf-redemption:maturity','basf-payment:late_interest'],
'D21':['basf-redemption:nominal-amount-definition','basf-redemption:makewhole-definition'],
'D35':['basf-redemption:early_call'],'D36':['basf-redemption:makewhole-definition'],
'D37':['basf-redemption:makewhole-definition'],'D38':['basf-global:united-states-definition'],
'D39':['basf-payment:gross_up','basf-payment:german_flat_tax'],
'D40':['basf-governance:substitution'],'D42':['basf-governance:amendment_agreement'],
'D43':['basf-governance:notice_publication','basf-governance:participation_proof'],
'D44':['basf-governance:jurisdiction','basf-notices:holding-proof'],
'U02':['basf-payment:principal_definition'],'U03':['basf-payment:interest_definition'],
'U04':['basf-redemption:par_call','basf-redemption:early_call'],
'U05':['basf-redemption:par_call'],'U11':['basf-payment:gross_up'],
'U13':['basf-governance:representative_appointment','basf-representative:individual-exercise-restriction'],
'M01':['basf-payment:day_count'],'M02':['basf-global:exchange-certification'],
'M03':['basf-governance:participation_proof'],'M04':['basf-governance:voting_chair']}
for _key in ('D22','D23','D24','D25','D26','D27','D28','D29','D30','D32','D33','D34','U12'):
    P3[_key]=['basf-redemption:control_put']
for _key in ('U08','U09','U10'):
    P3[_key]=['basf-agents:initial-agent','basf-agents:office-replacement',
        'basf-agents:appointment-change','basf-agents:effectiveness-reference','basf-agents:contractual-capacity']

HEADINGS={'D14':{6487},'D15':{7407},'D18':{9344},'D28':{13472},'D43':{38985},
          'U02':{7781,10004,10636},'U03':{6887,7198,8041,10016,10648},'U13':{36466}}
NAMES={'D17':{8813},'D24':{14130},'D25':{14173},'D26':{14214},'D38':{24568},'U12':{15069}}
COMPONENTS={'D21':{10225,10281,11843,17567,17768,18416,19131,21317,21414,21558},
            'U04':{19085,19196,19676}}

def decision(key,start,end):
    kind='SCOPED_SOURCE_READING';reason='The inspected context invokes this source reading with all retained qualifications.'
    if start in HEADINGS.get(key,set()):
        kind,reason='HEADING_MENTION','This exact token is a heading fragment,distinct from following operative prose.'
    elif start in NAMES.get(key,set()):
        kind,reason='NAME_COMPONENT','This occurrence is within the full name before or alongside the shorthand declaration.'
    elif start in COMPONENTS.get(key,set()):
        kind,reason='OTHER_DEFINITION_COMPONENT','This token belongs to a longer early/call purpose label; it cannot independently select this shorter definition.'
    elif key=='D20' and start in {9363,10859,27291,28615,29783}:
        kind,reason='GENERIC_DUE_DATE','This refers to the due date of the relevant payment or other debt,not automatically the defined final maturity.'
    elif (key=='D20' and start in {6946,7033}) or (key=='D18' and start==22964) or key=='D37' or (key=='U04' and start==22991):
        kind,reason='SCOPE_AMBIGUITY','Retain the literal and contextual scope alternatives; no single governing date or scope has been established.'
    elif key in {'M01','M02'}:
        kind,reason='MISSING_DEFINITION','The selected source lacks the required definition; a neighboring term cannot fill it.'
    elif key=='U04' and start==17732 or key=='U05' and start==17763:
        kind,reason='TABLE_COLUMN','The exact interval labels the table column; retain its relation to the printed value and distinct overlapping intervals.'
    elif key in {'U08','U09','U10'}:
        kind,reason='CONDITIONAL_ROLE','Initial naming,role replacement,office changes and actual appointment remain separate propositions.'
        if start in {23312,23329,23466}:
            kind,reason='ROLE_LABEL','This label identifies an appointment/office field; retain the associated value or unresolved placeholder and separate final-term authority.'
    elif key=='D40' or key=='U13' or key=='M04':
        kind,reason='CONDITIONAL_ROLE','The source describes a role subject to stated conditions; no actual appointment or identity is inferred.'
    return {'kind':kind,'reason':reason,'open_issues':deepcopy(READINGS[key][1])}

def expected_content(ordinary,decisions):
    prior=ordinary['definition_referent_review'];uses=deepcopy(prior['uses']);records=[]
    selected={r['record']:(i,r) for i,r in enumerate(decisions)}
    for use in uses:use.update(prior_remainder_disposition=use['disposition'],remainder_binding=None)
    for record in prior['records']:
        pair=selected.get(record['id']);indices=list(record['use_indices'])
        if pair is not None:
            row_index,row=pair;expected={(u['interval'],u['start'],u['end']):u for u in row['uses']}
            assert len(expected)==len(indices)
            for i in indices:
                use=uses[i];item=expected[(use['interval'],use['start'],use['end'])]
                assert use['quote']==item['quote'] and use['disposition']=='UNRECONCILED'
                use.update(disposition=item['kind'],remainder_binding={
                    'source_record_index':row_index,'record':row['record'],
                    **{k:deepcopy(item[k]) for k in ('context','source_piece_indices','kind','reason','open_issues')}},
                    remaining=deepcopy(item['open_issues']))
        records.append({**deepcopy(record),'remainder_reviewed':pair is not None,
                        'remainder_use_indices':indices if pair is not None else []})
    return {'records':records,'uses':uses,'source_records':deepcopy(decisions),
        'reviewed_records':44,'reviewed_associations':231,'original_associations':610,'supplemental_associations':2}

def expected_report(ordinary,products,profile,content):
    return {'version':VERSION,'profile_sha256':digest(profile),'products_sha256':digest(products),
        'ordinary_answer_sha256':digest(ordinary),'definition_report_sha256':digest(ordinary['definition_sources']),
        'prior_referent_report_sha256':digest(ordinary['definition_referent_review']),**deepcopy(content),
        'question_links':deepcopy(ordinary['definition_referent_review']['question_links']),
        'assistance':'EXACT_OCCURRENCE_SUPPLIED_SOURCE_REVIEW','prior_answer_preserved':True,
        'all_governing_uses_established':False,'actual_facts_established':False,
        'historical_law_established':False,'automatic_legal_interpretation':False,'whole_task_complete':False}

def verify(actual,ordinary,products,profile,content):
    expected={**ordinary,KEY:expected_report(ordinary,products,profile,content)}
    expected['report_sha256']=digest({k:v for k,v in expected.items() if k!='report_sha256'})
    assert actual==expected,'Whole answer differs from frozen remainder interpretation'
    return {'status':'PASS','whole_answer_equal_to_independent_expectation':True,'reviewed_records':44,'reviewed_associations':231}
