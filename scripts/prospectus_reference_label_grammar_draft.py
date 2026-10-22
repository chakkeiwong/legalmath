"""Retain an unevaluated lexical repair and its reviewed execution runner."""
from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[1]
AUTH=ROOT/'docs/implementation/prospectus-execution-authority'
PREP=AUTH/'reviews/reference-label-grammar-347'
(PREP/'candidate').mkdir(parents=True,exist_ok=True)
candidate=PREP/'candidate/reference_addresses.py';assert not candidate.exists()
body=(ROOT/'src/legalmath/prospectus/successor/reference_addresses.py').read_text()
assert body.count('[0-9]+|[a-z]+')==3
body=body.replace('[0-9]+|[a-z]+','[0-9]+|[a-z]|[ivxlcdm]+')
ast.parse(body);candidate.write_text(body)
runner=ROOT/'scripts/prospectus_reference_label_grammar.py';assert not runner.exists()
text=(ROOT/'scripts/prospectus_reference_address_projection.py').read_text()
text=text.replace('OLD_PREP, OLD_HERE = previous.PREP, previous.HERE',
    "from scripts.prospectus_reference_address_projection import costs as prior_costs\nOLD_PREP=AUTH/'reviews/reference-address-projection-346'\nOLD_HERE=AUTH/'attempts/basf-references/attempt-085'")
text=text.replace("PREP = AUTH / 'reviews/reference-address-projection-346'","PREP = AUTH / 'reviews/reference-label-grammar-347'")
text=text.replace("HERE = AUTH / 'attempts/basf-references/attempt-085'","HERE = AUTH / 'attempts/basf-references/attempt-086'")
text=text.replace('prospectus-reference-address-projection-repair-2026-10-19.md','prospectus-reference-label-grammar-repair-2026-10-19.md')
text=text.replace("METHOD = 'scripts/prospectus_reference_address_projection.py'","METHOD = 'scripts/prospectus_reference_label_grammar.py'")
text=text.replace("TARGETS = ('src/legalmath/prospectus/successor/reference_addresses.py',\n           'tests/prospectus_successor/conftest.py')","TARGETS = ('src/legalmath/prospectus/successor/reference_addresses.py',)")
text=text.replace("'scripts/prospectus_reference_address_projection_draft.py', 'scripts/prospectus_reference_addresses_failure.py')",
    "'scripts/prospectus_reference_address_projection_draft.py', 'scripts/prospectus_reference_addresses_failure.py',\n         'scripts/prospectus_reference_label_grammar_draft.py',\n         'scripts/prospectus_reference_address_projection_diagnostic.py',\n         'scripts/prospectus_reference_address_projection_failure.py',\n         'tests/prospectus_successor/test_reference_address_label_grammar.py')")
text=text.replace("return [TEST,'tests/prospectus_successor/test_reference_scope.py',",
    "return [TEST,'tests/prospectus_successor/test_reference_address_label_grammar.py','tests/prospectus_successor/test_reference_scope.py',")
start=text.index('def tests():');end=text.index('def prepare():',start)
text=text[:start]+text[end:]
text=text.replace("assert program['revision']==345","assert program['revision']==346")
text=text.replace('assert len(attempts)==84','assert len(attempts)==85')
text=text.replace("proposal['revision']=346","proposal['revision']=347")
text=text.replace("'revisions/0346.json'","'revisions/0347.json'")
text=text.replace("maximum_new_attempts']=85","maximum_new_attempts']=86")
text=text.replace("routes['baseline_revision']=346","routes['baseline_revision']=347")
text=text.replace("'previous_maximum':84,'new_maximum':85","'previous_maximum':85,'new_maximum':86")
text=text.replace("'revision':346","'revision':347")
text=text.replace('85 admissions;','86 admissions;')
text=text.replace("snapshot=previous.costs()","snapshot=prior_costs()")
text=text.replace("'scripts.prospectus_reference_address_projection',stage","'scripts.prospectus_reference_label_grammar',stage")
text=text.replace('Repair whole-paragraph transformation provenance after reproduced citation-only projection failure',
    'Repair parenthetical prose falsely indexed as a paragraph heading; preserve exact source destinations')
text=text.replace('reference_address_projection_review=', 'reference_label_grammar_review=')
text=text.replace('Verify unchanged structural destinations with exact transformation provenance; retain failed084',
    'Verify unchanged destination readings after narrowing heading labels; retain failed084 and085')
text=text.replace('Preserve current construction provenance for transformed body spans','Distinguish declared label tokens from ordinary parenthetical prose')
text=text.replace('Original destinations,transformation refusals and complete installed equality',
    'Original destinations,lexical and transformation refusals,and complete installed equality')
text=text.replace('084 rejects valid supplied final terms at its citation-only body projector',
    '085 misclassifies parenthetical word etwaiger as a heading and corrupts section9 scope')
text=text.replace('Unchanged destination readings,transformation provenance,complete installed answer',
    'Unchanged destinations,ordinary-word controls,transformation provenance,complete installed answer')
ast.parse(text);runner.write_text(text)
print('Drafted lexical repair only; original source expectations and projection tests retained')
