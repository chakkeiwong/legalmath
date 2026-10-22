"""Reviewed timing relations, with exact source fragments kept separately."""
RULES = [
    {'id':'principal_presentation','source_index':0,
     'quote':'Der Anspruch aus einer Schuldverschreibung auf den Inhaber erlischt mit dem Ablauf von 30 Jahren nach dem Eintritt der für die Leistung bestimmten Zeit, wenn nicht die Urkunde vor dem Ablauf der 30 Jahre dem Aussteller zur Einlösung vorgelegt wird.',
     'meaning':{'clock':'PRESENTATION','default_years':30,'origin':'PERFORMANCE_DUE',
                'effect':'EXTINCTION_IF_NOT_PRESENTED_WITHIN_PERIOD','deed_variation':'SUBJECT_TO_801_3'}},
    {'id':'limitation_after_presentation','source_index':0,
     'quote':'Erfolgt die Vorlegung, so verjährt der Anspruch in zwei Jahren von dem Ende der Vorlegungsfrist an.',
     'meaning':{'clock':'LIMITATION','years':2,'origin':'END_OF_PRESENTATION_PERIOD',
                'condition':'PRESENTATION_WITHIN_PERIOD','presentation_date_is_origin':False}},
    {'id':'judicial_equivalence','source_index':0,
     'quote':'Der Vorlegung steht die gerichtliche Geltendmachung des Anspruchs aus der Urkunde gleich.',
     'meaning':{'judicial_assertion_of_instrument_claim':'EQUIVALENT_TO_PRESENTATION'}},
    {'id':'coupon_presentation','source_index':0,
     'quote':'Bei Zins-, Renten- und Gewinnanteilscheinen beträgt die Vorlegungsfrist vier Jahre. Die Frist beginnt mit dem Schluss des Jahres, in welchem die für die Leistung bestimmte Zeit eintritt.',
     'meaning':{'clock':'PRESENTATION','claim_types':['INTEREST_COUPON','ANNUITY_COUPON','PROFIT_SHARE_COUPON'],
                'default_years':4,'origin':'END_OF_YEAR_PERFORMANCE_DUE','deed_variation':'SUBJECT_TO_801_3'}},
    {'id':'deed_variation','source_index':0,
     'quote':'Die Dauer und der Beginn der Vorlegungsfrist können von dem Aussteller in der Urkunde anders bestimmt werden.',
     'meaning':{'clock':'PRESENTATION','issuer_may_vary_in_deed':['DURATION','BEGINNING']}},
    {'id':'payment_stop_suspension','source_index':1,
     'quote':'Der Beginn und der Lauf der Vorlegungsfrist sowie der Verjährung werden durch die Zahlungssperre zugunsten des Antragstellers gehemmt. Die Hemmung beginnt mit der Stellung des Antrags auf Zahlungssperre; sie endigt mit der Erledigung des Aufgebotsverfahrens und, falls die Zahlungssperre vor der Einleitung des Verfahrens verfügt worden ist, auch dann, wenn seit der Beseitigung des der Einleitung entgegenstehenden Hindernisses sechs Monate verstrichen sind und nicht vorher die Einleitung beantragt worden ist. Auf diese Frist finden die Vorschriften der §§ 206, 210, 211 entsprechende Anwendung.',
     'meaning':{'clocks':['PRESENTATION','LIMITATION'],'effect':'SUSPENSION_OF_BEGINNING_AND_RUNNING',
                'beneficiary':'APPLICANT','begins':'APPLICATION_FOR_PAYMENT_STOP',
                'ends':['COMPLETION_OF_PUBLIC_NOTICE_PROCEEDINGS',
                    'IF_STOP_PRECEDES_PROCEEDINGS_SIX_MONTHS_AFTER_IMPEDIMENT_REMOVED_WITHOUT_PRIOR_INITIATION_APPLICATION'],
                'onward_provisions':[206,210,211],'onward_application':'UNRESOLVED'}},
]

READING = '''H28 — BGB801, presentation and limitation

The retained801(1) sentence1 gives the default bearer-note presentation period
as30years from the time fixed for performance, with extinction if the instrument
is not presented for redemption before that period ends. If presentation occurs,
sentence2 measures the separate two-year limitation period FROM THE END OF THE
PRESENTATION PERIOD, not from the presentation date. Sentence3 equates judicial
assertion of the claim from the instrument with presentation.

801(2) separately gives interest,annuity and profit-share coupons a four-year
presentation period beginning at the end of the year when performance falls due.
801(3) permits the issuer to change the presentation period's duration and
beginning in the deed. The selected contract shortens the801(1) sentence1
presentation period to ten years;it does not replace every statutory clock.

802 suspends the beginning and running of BOTH the presentation and limitation
periods for the applicant. It starts with the payment-stop application and ends
under the stated proceedings/six-month conditions,with analogous206/210/211
dependencies. Those onward conditions are not assumed satisfied.

Historical wording,claim type,due date,valid presentation or judicial assertion,
deed variation,payment-stop events and civil counting conventions remain open.
These source relations do not compute an actual expiry date or establish
extinction,a limitation defence or an effective historical application.
'''
