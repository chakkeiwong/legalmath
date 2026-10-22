"""Finite exposed source review; these labels are not inferred legal effects."""
DOCUMENT = 'basf-base-september-2022-exchange'

# page, line -> (selected start, selected end or whole remainder, role, text).
# Text is whitespace-normalized for the reviewed caption only. Exact original
# and selected whitespace remains in the bound profile and consumer output.
REVIEW = {}


def whole(page, lines, role):
    for line, text in lines.items():
        REVIEW[(page, line)] = [(0, None, role, text)]


whole(108, {1:'OPTION I – Anleihebedingungen für Schuldverschreibungen mit fester',
            2:'Verzinsung',3:'ANLEIHEBEDINGUNGEN DER SCHULDVERSCHREIBUNGEN',
            4:'DEUTSCHSPRACHIGE FASSUNG'}, 'TITLE')
for page, lines in {
    108:{5:'§ 1',6:'WÄHRUNG, STÜCKELUNG, FORM, BESTIMMTE DEFINITIONEN'},
    110:{46:'§ 2',47:'STATUS, NEGATIVVERPFLICHTUNG'},
    111:{22:'§ 3',23:'ZINSEN'},113:{68:'§ 4',69:'ZAHLUNGEN'},
    123:{79:'§ 6',80:'DER FISCAL AGENT, DIE ZAHLSTELLE UND DIE',81:'BERECHNUNGSSTELLE'},
    125:{1:'§ 7',2:'STEUERN'},126:{28:'§ 8',29:'VORLEGUNGSFRIST',32:'§ 9',33:'KÜNDIGUNG'},
    128:{47:'§ 10',48:'ERSETZUNG'},
    129:{51:'§ 11',52:'ÄNDERUNG DER ANLEIHEBEDINGUNGEN, GEMEINSAMER VERTRETER'},
    131:{42:'§ 12',43:'BEGEBUNG WEITERER SCHULDVERSCHREIBUNGEN,',44:'ANKAUF UND ENTWERTUNG'},
    133:{11:'§ 15',12:'SPRACHE'},
}.items(): whole(page, lines, 'SECTION_HEADING')

for page, lines in {
    111:{24:'(1) Zinssatz und Zinszahlungstage.'},
    130:{2:'(6) Gemeinsamer Vertreter.',31:'(7) Verfahrensrechtliche',32:'Gläubigerversammlung.',
         33:'Bestimmungen',34:'über',35:'Gläubigerbeschlüsse',36:'in',37:'einer',
         38:'(a) Frist, Anmeldung, Nachweis.',66:'(b) Inhalt der Einberufung, Bekanntmachung.'},
    131:{5:'(c) Auskunftspflicht, Abstimmung.',13:'(d) Bekanntmachung von Beschlüssen.',
         24:'(e) Abstimmung ohne Versammlung.'},
}.items(): whole(page, lines, 'SUBSECTION_CAPTION')

for page, line, end, text in [
    (111,71,23,'(2) Auflaufende Zinsen.'),
    (111,75,51,'(3) Berechnung der Zinsen für Teile von Zeiträumen.'),
    (112,1,21,'(4) Zinstagequotient.'),
    (113,77,30,'(1) (a) Zahlungen auf Kapital.'),(113,81,23,'(b) Zahlung von Zinsen.'),
    (114,29,18,'(2) Zahlungsweise.'),(114,51,14,'(3) Erfüllung.'),
    (114,53,14,'[(4)] Zahltag.'),(114,77,41,'[(5)] Bezugnahmen auf Kapital und Zinsen.'),
    (115,13,42,'[(6)] Hinterlegung von Kapital und Zinsen.'),
    (128,56,14,'(1) Ersetzung.'),(129,39,19,'(2) Bekanntmachung.'),
    (129,40,32,'(3) Ermächtigung der Emittentin.'),(129,54,36,'(1) Änderung der Anleihebedingungen.'),
    (129,63,27,'(2) Mehrheitserfordernisse.'),(129,69,29,'(3) Beschlüsse der Gläubiger.'),
    (129,72,44,'(4) Leitung der Abstimmung ohne Versammlung.'),(129,75,15,'(5) Stimmrecht.'),
    (131,45,44,'(1) Begebung weiterer Schuldverschreibungen.'),(131,50,11,'(2) Ankauf.'),
    (131,56,15,'(3) Entwertung.'),(132,43,22,'(1) Anwendbares Recht.'),(132,46,18,'(2) Gerichtsstand.'),
]: REVIEW[(page,line)] = [(0,end,'SUBSECTION_CAPTION',text)]

REVIEW[(123,82)] = [(0,44,'SUBSECTION_CAPTION','(1) Bestellung; bezeichnete Geschäftsstelle.'),
    (45,None,'UNRESOLVED_AGENT_INTRODUCTION','Der anfänglich bestellte Fiscal Agent ,')]
whole(123,{83:'die anfänglich bestellte Zahlstelle und die anfänglich bestellte',
           84:'Berechnungsstelle und deren bezeichnete Geschäftsstellen lauten wie folgt:'},
      'UNRESOLVED_AGENT_INTRODUCTION')
whole(124,{43:'Berechnungsstelle:',44:'[Name und bezeichnete Geschäftsstelle]'},'UNRESOLVED_AGENT_FIELD')
whole(127,{
    12:'(f) die Emittentin ihre Geschäftstätigkeit ganz oder überwiegend einstellt, alle oder den',
    13:'wesentlichen Teil ihres Vermögens veräußert oder anderweitig abgibt und (i)',
    14:'dadurch den Wert ihres Vermögens wesentlich vermindert und (ii) es dadurch',
    15:'wahrscheinlich wird, dass die Emittentin ihre Zahlungsverpflichtungen gegenüber',
    16:'den Gläubigern nicht mehr erfüllen kann; oder'},'UNRESOLVED_DEFAULT_F')

STRUCTURAL = {'TITLE','SECTION_HEADING','SUBSECTION_CAPTION'}
MEETING_ORDER = [31,33,34,35,36,37,32]
MEETING_TEXT = '(7) Verfahrensrechtliche Bestimmungen über Gläubigerbeschlüsse in einer Gläubigerversammlung.'
QUESTIONS = {
    'UNRESOLVED_AGENT_INTRODUCTION': {
        'question':'How does the selected appointment introduction attach to the supplied fiscal/paying-agent details and unresolved calculation-agent designation?',
        'next_action':'Review the full introduction together with the retained office/capacity alternatives; distinguish introductory association from actual appointment authority.'},
    'UNRESOLVED_AGENT_FIELD': {
        'question':'Which source authoritatively supplies the calculation agent and its designated office for this instrument?',
        'next_action':'Retain the label and unfilled placeholder with the existing conditional office readings; obtain actual designation authority before choosing an office.'},
    'UNRESOLVED_DEFAULT_F': {
        'question':'How are cessation and asset disposal related, and to which alternatives do diminution and payment-risk conditions attach in the governing German clause?',
        'next_action':'Compare explicit conditional constructions against the complete German and English clauses, preserving German priority and without selecting a translation as authority.'},
}
