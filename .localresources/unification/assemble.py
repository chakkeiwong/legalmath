"""One-time source integration from protected baselines; review before rerunning."""
from pathlib import Path
from collections import defaultdict
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / '.localresources/unification/baseline'
BOOK = ROOT / 'docs/monograph'
OUT = BOOK / 'review/unification'
HEADING = re.compile(r'^\\(section|subsection|subsubsection)(?:\[[^\]]*\])?\{([^\n]+)\}', re.M)

def digest(s):
    return hashlib.sha256(s.encode()).hexdigest()

units = {}
cores = {}
headers = {}
insertions = defaultdict(list)
edits = defaultdict(list)
notes = defaultdict(str)
mapping = []

def collect(path, prefix, pattern):
    source = path.read_text()
    hits = list(pattern.finditer(source))
    if not hits:
        positions = [0]
    else:
        positions = [m.start() for m in hits]
    result = []
    for i, start in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(source)
        raw = source[start:end]
        identifier = f'{prefix}:{i:02}'
        title_match = HEADING.match(raw)
        units[identifier] = {
            'id': identifier,
            'source': str(path.relative_to(BASE)),
            'source_start_line': source.count('\n', 0, start) + 1,
            'source_end_line': source.count('\n', 0, end) + 1,
            'title': title_match[2] if title_match else 'Contract amendment and platform analysis',
            'raw': raw,
        }
        result.append(identifier)
    return source[:positions[0]], result

for p in sorted((BASE / 'docs/monograph/chapters').glob('*.tex')):
    chapter = int(p.name[:2])
    header, ids = collect(p, f'M{chapter:02}', re.compile(r'^\\section\{[^\n]+\}', re.M))
    headers[chapter] = (p.name, header)
    cores[chapter] = ids

for p in sorted((BASE / 'docs/proposal').glob('*.tex')):
    if p.name != 'proposal.tex':
        collect(p, 'P-' + p.stem, HEADING)

def pid(file, i):
    return f'P-{file}:{i:02}'

def put(file, indices, chapter, core, position='after', level='subsection', titles=None):
    if isinstance(indices, int):
        indices = [indices]
    for i in indices:
        identifier = pid(file, i)
        assert identifier in units, identifier
        insertions[(chapter, core, position)].append((identifier, level, (titles or {}).get(i)))

def change(file, i, old, new, why):
    identifier = pid(file, i)
    assert old in units[identifier]['raw'], (identifier, old[:100])
    edits[identifier].append({'old': old, 'new': new, 'reason': why})

def lead(file, i, text):
    notes[pid(file, i)] += text.strip() + '\n\n'

# The destination is determined by the question addressed, not proposal order.
put('01-problem', [0, 1], 1, 0, level='section', titles={0: 'The bank workflow and its regulatory perimeter'})
put('01-problem', 5, 1, 2, level='subsection')
put('01-problem', 2, 2, 0, 'before', 'section', {2: 'SPI qualification: the conditions a wealth flag conceals'})
put('01b-complete-dry-run', list(range(7)), 2, 0, 'before', 'subsection')
# The dry run is a major argument section; its child questions remain subsections.
insertions[(2, 0, 'before')][1] = (pid('01b-complete-dry-run', 0), 'section', None)
put('01-problem', 4, 2, 0, 'before', 'section')
put('03-product', 5, 3, 0, level='subsection', titles={5: 'The computational preservation objective'})
put('01a-language-lesson', [0, 1], 3, 3, level='subsection', titles={0: 'Why written agreement needs an executable meaning'})
put('03-product', 3, 3, 4, level='subsection')
put('03-product', 6, 3, 9, level='subsection', titles={6: 'A concrete SPI witness and its knownness encoding'})
put('01a-language-lesson', 5, 3, 9, level='subsection')
put('02-literature', [0, 1], 4, 0, level='subsection', titles={0: 'The research families behind the design'})
put('02a-foundations', 0, 4, 1)
put('02-literature', 2, 4, 2, level='subsection', titles={2: 'Statutory programs, literate rules and collaboration evidence'})
put('01a-language-lesson', 2, 4, 3, titles={2: 'Applying the exception model to SPI explanations'})
put('01a-language-lesson', 3, 4, 5, titles={3: 'Applying the state model to client consent'})
put('01a-language-lesson', 4, 4, 7, titles={4: 'From a consent property to a Java verification model'})
put('02-literature', 5, 4, 7, titles={5: 'The evidence and restrictions behind Stipula verification'})
put('02b-contract-evolution', 0, 4, 7, titles={0: 'Amendment and resource analysis'})
put('02-literature', 4, 4, 8, titles={4: 'Authority, default negation and competing normative backends'})
put('02-literature', 8, 4, 9, titles={8: 'Software adoption and interchange standards'})
put('02-literature', 7, 4, 10)
put('02-literature', [3, 6], 4, 13)
put('03-product', 8, 5, 0, titles={8: 'What a drafting service should propose'})
put('04-prototype', 3, 5, 10, titles={3: 'Adapter boundaries and the earlier reuse assessment'})
put('03-product', 2, 7, 0, level='section')
put('03a-rule-contract', 0, 7, 0)
put('03a-rule-contract', 1, 7, 1)
put('03a-rule-contract', 2, 7, 3)
put('03c-storage-review', 1, 7, 5)
put('04-prototype', 5, 7, 6)
put('03d-java-delivery', list(range(5)), 7, 9, 'before', 'subsection', {0: 'The earlier SPI compiler: a concrete deployment lesson', 1: 'SPI-Demo1: the narrower retained demonstration', 2: 'The SPI-Demo1 input and output boundary'})
insertions[(7, 9, 'before')][0] = (pid('03d-java-delivery', 0), 'section', 'The earlier SPI compiler: a concrete deployment lesson')
put('03-product', 4, 7, 11)
put('03b-event-contract', 0, 7, 11)
put('03d-java-delivery', 5, 7, 13)
put('03-product', [0, 1, 7], 8, 0, 'before', 'section', {0: 'The shared workbench and its users', 7: 'The execution architecture and its deliberate limits'})
put('03c-storage-review', 0, 8, 0, 'before')
put('04-prototype', 2, 8, 0, 'before', 'section', {2: 'The original work packages and their execution'})
put('03d-java-delivery', 6, 8, 0, 'before')
put('05-evidence', 1, 8, 0, 'before', titles={1: 'Distinguishing specification fixtures from executed evidence'})
put('03c-storage-review', 2, 8, 0, 'before', 'section', {2: 'The implemented authoring service and its current boundary'})
put('04-prototype', 0, 9, 0, titles={0: 'The product decision and initial comparison scope'})
put('05-evidence', 0, 9, 3, titles={0: 'Fifteen cross-circular acceptance scenarios'})
put('04-prototype', 4, 9, 4, titles={4: 'The separate comparison of whole review workflows'})
put('04-prototype', 6, 9, 11, level='section')
put('04-prototype', 1, 10, 1)
put('01-problem', 3, 10, 4, level='section')
put('03-product', 9, 10, 4)
put('04-prototype', 7, 10, 8, 'before', 'section')
put('02-literature', 9, 10, 13)
put('05-evidence', 2, 10, 13)
put('05-evidence', 3, 10, 14, 'before', 'section')

# Preserve the lesson while reconciling the demonstrator, implemented MVP and future ensemble.
change('01a-language-lesson', 2,
       'The delivered Java example uses the equivalent\nexplicit Boolean condition for this one requirement; its compiler rejects the\ngeneral default operator until that operator has its own implementation tests.',
       'The earlier SPI-Demo1 Java example uses the equivalent explicit Boolean\ncondition for this one requirement and rejects the general default operator.\nThe subsequently completed v0.1 runtime implements that operator with its own\nconformance tests; the two compiler profiles remain distinct.',
       'The accepted MVP now implements defaults; preserve the smaller demonstration restriction.')
change('02-literature', 1,
       'The local library contains 38 paper editions representing 37 distinct works.',
       'The initial proposal retained 38 paper editions representing 37 distinct\nworks. The unified library now retains 50 editions representing 49 works,\nincluding the later legal-search and uncertainty studies.',
       'Retain the original review scope and state the current combined library count.')
change('01b-complete-dry-run', 6,
       'the reviewer application, and production integration.\nThe product plan below turns those remaining activities into testable modules.',
       'and production integration. The reviewer application and the broader\nengineering modules were subsequently implemented in the local MVP;\nChapter~\\ref{ch:implementation} records their evidence and the distinct ensemble\nextension that remains to be built.',
       'Do not present the implemented review application as unfinished.')
lead('01b-complete-dry-run', 0, r'''The retained SPI example provides the first end-to-end execution lesson.
Its original standalone compiler is called SPI-Demo1. The later local workbench
extends that lesson through authenticated synthetic review, attributed events,
release and archive restoration. This chapter first makes the business meaning
and the small executable example explicit; Chapters~\ref{ch:verification} and
\ref{ch:implementation} distinguish the two interfaces and their actual evidence.''')
lead('03d-java-delivery', 0, r'''The API and commands in the next five subsections belong to the retained
\emph{SPI-Demo1} teaching example under \path{examples/java-dry-run/}. They remain
reproducible, but are not the current v0.1 SDK. The subsequent section on the actual
generated interface supplies the current String/Map API. Keeping both makes the
translation mechanism inspectable without directing an implementer to the wrong
library.''')
change('03d-java-delivery', 1,
       'Dates, arithmetic expressions, general defaults, conditionals and the full\nobligation language remain part of the proposed RuleIR implementation; the demo\ncompiler rejects them.',
       'The demo compiler rejects dates, arithmetic expressions, general defaults,\nconditionals and the full obligation language. The later RuleIR implementation\nsupports the specified decision operators and its finite duty profile; those\nfeatures are outside this earlier demo API.',
       'Retain the original subset without incorrectly restricting the current implementation.')
change('03d-java-delivery', 1,
       'Those fixtures\nremain the completion target for the full interpreter and backend.',
       'Those fixtures were the completion target for the full interpreter and\nbackend and were subsequently executed by the accepted MVP.',
       'The 35 RuleIR fixtures are now executed, separately from the earlier demonstration.')
change('03d-java-delivery', 2,
       'The full RuleIR implementation additionally\nprovides expression-node traces, standardized diagnostics and engine identity\nas specified in Section~\\ref{sec:product}.',
       'The current RuleIR implementation provides expression-node traces,\nstandardized diagnostics and engine identity through the different v0.1 API\ndocumented later in this chapter.',
       'Point directly to the actual implemented interface after relocating the product section.')
lead('03d-java-delivery', 6, r'''The W-package names below identify the original allocation of responsibilities.
They explain the acceptance obligations that drove the implemented T00--T22
tasks; they are not an additional unfinished backlog. The execution account that
follows maps those obligations to the delivered workbench. The E tasks later in
this chapter specify the new ensemble work.''')
change('03-product', 0,
       'The first release should support a narrow end-to-end task:',
       'The first local release was designed around a narrow end-to-end task:',
       'The local release now exists; the retained requirement explains its scope.')
change('03-product', 0,
       'Integration into bank systems follows the bank\'s ordinary change process.',
       'That local path is now implemented with public sources and synthetic\nidentities. Integration into bank systems still follows the bank\'s ordinary\nchange process.',
       'Separate completed local execution from pending real bank integration.')
change('04-prototype', 2,
       'the proposal does not claim those dependencies have been integrated already.',
       'the current local MVP has integrated and locked its selected dependencies.\nThe retained W-package descriptions below explain the original work division.',
       'The environment was implemented; preserve the original bootstrap requirements.')
change('04-prototype', 2,
       'The second command is a future completion check for the full RuleIR interpreter,\nnot an executed result. The narrower Java command in Section~\\ref{sec:java}\nis already executable. This\ndistinction makes it possible to hand the proposal to an agent without confusing\nthe written test expectations with a functioning compliance engine.',
       'The second command became an executed check in the accepted MVP: all 35\ndecision cases passed. Its event-and-release flag describes only this particular\nharness; separate tests and the complete walkthrough execute those components.\nThe narrower SPI-Demo1 command in Section~\\ref{sec:java} remains a separate\nreproduction route. Neither result establishes automatic legal translation.',
       'Reconcile the old future command with the actual retained acceptance evidence.')
lead('04-prototype', 2, r'''The original W packages specified the route from a document-only contract to
a working system. Their requirements are retained because they explain what the
implementation must preserve. The next section records their completed T-task
realization and identifies the optional research and human-evaluation work that
remains. The twelve-week allocation was a planning assumption, not measured
development effort or evidence of bank readiness.''')
change('05-evidence', 1,
       'The delivered checker validates all three JSON schemas, the 35 decision fixture\ncontracts, six negative examples, event-record structure, original/derivative/span\nhashes and the SQLite table definitions. It does not execute the planned decision,\nevent or release engines. Its report says so explicitly. W03, W04 and W05 provide\nthe corresponding full-runtime acceptance commands.',
       'The original specification checker validates three initial JSON schemas,\nthe 35 decision fixture contracts, six negative examples, event-record structure,\nsource/derivative/span hashes and the SQLite definitions. Its static mode alone\ndoes not execute the engines. The accepted MVP subsequently executed all 35\ndecision cases in runtime mode and exercised event and release behavior through\nseparate tests and the complete walkthrough. The recorded acceptance also checked\nregeneration of 31 JSON contracts, including OpenAPI. Static fixture checks and\nthose later execution results remain different evidence.',
       'Preserve all fixture counts while accurately recording later implementation.')
change('05-evidence', 2,
       'bibliography are in \\path{docs/proposal/}.',
       'bibliography are now canonical in \\path{docs/monograph/}; the earlier\nproposal entry point builds the same unified work.',
       'One canonical document after integration.')
lead('04-prototype', 4, r'''The baseline ladder above compares automatic interpretation methods. A second
experiment is needed for the product decision: does the complete workbench help
people carry a change through review? The four workflow conditions below answer
that broader question. They must not be pooled with repeated model calls as if
both experiments had the same observational unit.''')
lead('04-prototype', 3, r'''The earlier repository inspection contributes the adapter requirements below.
The preceding analysis identifies the actual search-controller differences;
references here to historical UCB-style investigations do not override that
finding or establish that a generic MCTS service is already available.''')

# The old API table predates T00 closure. Preserve its responsibilities, with
# explicit local corrections rather than two incompatible current contracts.
lead('03c-storage-review', 2, r'''The original service design below names the core responsibilities and transport
conventions. T00--T22 implemented a larger 22-path API; the retained generated
OpenAPI and the exact runtime closure resolve the original sketches. Reviewer
identity is derived from authentication, every mutation uses a caller-scoped
idempotency key, and the build--verification--release sequence is acyclic.
The table is a design summary, not a substitute for the current request models.''')
change('03c-storage-review', 2,
       'Decision, reviewer identity/role, comment and expected revision;',
       'Decision, comment and expected revision; reviewer identity/role derived from authentication;',
       'Current authorization rejects caller-supplied roles as authority.')
change('03c-storage-review', 2,
       'Evidence-report hash, Java-release-manifest hash and expected revision;',
       'Java-release-manifest hash, expected revision and activation time;',
       'Match the implemented Release request; build and verification are prepared separately.')
change('03c-storage-review', 2,
       'Its response includes the tagged outcome, exact value if any, reason codes,',
       'The evaluation response includes the tagged outcome, exact value if any, reason codes,',
       'Clarify referent after integration.')
change('03c-storage-review', 2,
       'The local authoring service uses the following endpoints.',
       'The original authoring-service sketch assigns the following endpoint responsibilities.',
       'Explicitly mark the retained early transport table as design history.')

change('01b-complete-dry-run', 5,
       'The generated class and a small support library are compiled into\n\\texttt{spi-controls-demo.jar}. A separate host example is',
       'The generated class and its small support library form the JAR\n\\path{spi-controls-demo.jar}. A separate host example is',
       'Preserve the build description while permitting a clean line break.')

change('01a-language-lesson', 1,
       r'\ref{sec:product}', r'\ref{merge:P-03-product:02}',
       'The JSON expression moved to the intermediate-representation section in chapter 7.')
change('01a-language-lesson', 5,
       r'\ref{sec:prototype}', r'\ref{merge:P-04-prototype:03}',
       'Point to the actual local-project reuse discussion, now in chapter 5.')

edits['M01:07'].append({
    'old': 'The next chapter follows the second circular through that\nentire route. Its apparent simplicity is useful: a small formula is sufficient\nto expose why independent source judgment, explicit scope and uncertainty cannot\nbe replaced by a large number of successful program evaluations.',
    'new': 'The next chapter follows two circulars through that route. The complete\nSPI transaction makes execution concrete; the smaller marketing restriction\nthen exposes why independent source judgment, explicit scope and uncertainty\ncannot be replaced by a large number of successful program evaluations.',
    'reason': 'Repair the chapter transition after adding the full SPI case before 23EC46.'})

def emit(identifier, chapter, level=None, title=None):
    unit = units[identifier]
    body = unit['raw']
    applied = []
    # Nested inputs are independently accounted units, placed by the map above.
    inputs = re.findall(r'^\\input\{([^}]+)\}\s*$', body, re.M)
    body = re.sub(r'^\\input\{[^}]+\}\s*$', '', body, flags=re.M)
    for edit in edits[identifier]:
        assert edit['old'] in body, identifier
        body = body.replace(edit['old'], edit['new'], 1)
        applied.append(edit)
    match = HEADING.match(body)
    if level:
        heading = '\\' + level + '{' + (title or unit['title']) + '}'
        body = heading + (body[match.end():] if match else '\n\n' + body)
    match = HEADING.match(body)
    at = match.end() if match else 0
    body = body[:at] + '\n\\label{merge:' + identifier + '}\n' + body[at:]
    if notes[identifier]:
        match = HEADING.match(body)
        at = match.end() if match else 0
        # Labels remain attached to the same heading even when teaching prose is inserted.
        body = body[:at] + '\n\n' + notes[identifier] + body[at:]
    # Article-sized tables retain their contents; widths have enough room for spacing.
    # Use wrapped paths only when diagnostics confirm a problem after the first build.
    body = body.strip() + '\n'
    mapping.append({k:v for k,v in unit.items() if k != 'raw'} | {
        'source_sha256': digest(unit['raw']),
        'destination': 'docs/monograph/chapters/' + headers[chapter][0],
        'destination_chapter': chapter,
        'destination_label': 'merge:' + identifier,
        'destination_sha256': digest(body),
        'disposition': 'RETAINED_WITH_EXPLICIT_UPDATES' if applied else 'RETAINED_BODY',
        'heading_level': level,
        'heading_title': title,
        'nested_inputs_relocated': inputs,
        'editorial_updates': applied,
        'added_bridge': notes[identifier],
    })
    return f'% BEGIN SOURCE UNIT {identifier}\n' + body + f'% END SOURCE UNIT {identifier}\n\n'

used = [identifier for items in insertions.values() for identifier,_,_ in items]
expected = [i for i in units if i.startswith('P-')]
assert len(used) == len(set(used)) and set(used) == set(expected), (set(expected)-set(used),set(used)-set(expected))
for chapter in range(1,11):
    name, header = headers[chapter]
    if chapter == 2:
        header = header.replace('The second circular, from source to an unreleased control',
                                'Two circulars, from business meaning to executable controls')
        header += r'''
The two cases answer different questions. Circular 23EC35 shows a complete
selected transaction profile: qualification, evidence, consent, execution and
change. Circular 23EC46 then exposes why successful execution cannot settle an
uncertain classification. Both examples use retained public editions and
synthetic facts. Their different approval states are part of the lesson.

'''
    if chapter == 8:
        header = header.replace('An implementation contract for the interpretation workbench',
                                'The complete workbench and its interpretation extension')
    text = header
    for index, identifier in enumerate(cores[chapter]):
        for ident,level,title in insertions[(chapter,index,'before')]:
            text += emit(ident,chapter,level,title)
        if chapter == 8 and index == 0:
            text += '\\input{\\LegalMathRoot chapters/08a-executed-workbench}\n\n'
        text += emit(identifier,chapter)
        for ident,level,title in insertions[(chapter,index,'after')]:
            text += emit(ident,chapter,level,title)
    (BOOK/'chapters'/name).write_text(text)

OUT.mkdir(exist_ok=True)
(OUT/'source-retention.json').write_text(json.dumps({
    'status':'INTEGRATED_AUTHOR_DRAFT',
    'baseline_manifest':'.localresources/unification/baseline/manifest.json',
    'source_units':mapping,
    'source_unit_count':len(mapping),
    'proposal_unit_count':len(expected),
    'original_monograph_section_count':sum(len(x) for x in cores.values()),
    'unmapped_substantive_units':[],
    'front_matter_disposition':'One unified title, introduction and contents replace duplicate front matter. Proposal investment claims, counts and scope are accounted in front-matter-map.md.',
    'limits':'A retained unit and matching hash establish inclusion, not readability or legal validity.'
},indent=2)+'\n')
print(json.dumps({'integrated_units':len(mapping),'proposal_units':len(expected),'monograph_sections':sum(map(len,cores.values()))}))
