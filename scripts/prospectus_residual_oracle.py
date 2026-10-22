"""Reviewed occurrence inventory, independent of the coverage implementation."""
PREFIX = 'basf-base-september-2022-exchange:'
HEADINGS = {
    'p111:l71': '(2) Auflaufende Zinsen.',
    'p111:l75': '(3) Berechnung der Zinsen für Teile von Zeiträumen.',
    'p112:l1': '(4) Zinstagequotient.',
    'p113:l77': '(1) (a) Zahlungen auf Kapital.',
    'p113:l81': '(b) Zahlung von Zinsen.',
    'p114:l29': '(2) Zahlungsweise.',
    'p114:l51': '(3) Erfüllung.',
    'p114:l53': '[(4)] Zahltag.',
    'p114:l77': '[(5)] Bezugnahmen auf Kapital und Zinsen.',
    'p115:l13': '[(6)] Hinterlegung von Kapital und Zinsen.',
    'p123:l82': '(1) Bestellung; bezeichnete Geschäftsstelle.',
    'p128:l56': '(1) Ersetzung.',
    'p129:l39': '(2) Bekanntmachung.',
    'p129:l40': '(3) Ermächtigung der Emittentin.',
    'p129:l54': '(1) Änderung der Anleihebedingungen.',
    'p129:l63': '(2) Mehrheitserfordernisse.',
    'p129:l69': '(3) Beschlüsse der Gläubiger.',
    'p129:l72': '(4) Leitung der Abstimmung ohne Versammlung.',
    'p129:l75': '(5) Stimmrecht.',
    'p131:l45': '(1) Begebung weiterer Schuldverschreibungen.',
    'p131:l50': '(2) Ankauf.',
    'p131:l56': '(3) Entwertung.',
    'p132:l43': '(1) Anwendbares Recht.',
    'p132:l46': '(2) Gerichtsstand.',
}
RESIDUALS = ['p124:l43', 'p124:l44', 'p127:l12', 'p127:l13',
             'p127:l14', 'p127:l15', 'p127:l16']


def predict(products, answer):
    """Use literal headings and source rows, never the candidate evaluator."""
    units = {u['unit']: u for u in products['P2']['payload']['assembly']['units']}
    pending = answer['meaning_coverage']['selected_body_pending']
    assert {r['unit'] for r in pending} == {PREFIX+s for s in (*HEADINGS, *RESIDUALS)}
    count = 0
    for suffix, title in HEADINGS.items():
        unit = units[PREFIX+suffix]
        assert unit['role'] == 'OPERATIVE' and unit['text'].startswith(title)
        assert unit['text'][len(title):].strip(), 'Whole unit was mistaken for a heading'
        row = next(r for r in pending if r['unit'] == PREFIX+suffix)
        chars = sum(not ch.isspace() for ch in title)
        assert row['unknown_characters'] == chars and row['uncovered_characters'] == 0
        count += chars
    residual = [r for r in pending if r['unit'] in {PREFIX+s for s in RESIDUALS}]
    assert len(residual) == 7 and all(r['role_unresolved'] for r in residual)
    return {'heading_units': sorted(PREFIX+s for s in HEADINGS),
            'heading_nonspace_characters': count,
            'substantive_pending': residual, 'original_pending_count': 31,
            'default_conditionally_modeled_units': [PREFIX+s for s in RESIDUALS[2:]],
            'missing_agent_units': [PREFIX+s for s in RESIDUALS[:2]],
            'unresolved_nonspace_characters': sum(r['unknown_characters'] for r in residual)}
