"""Bind the specifically reviewed round-14 source claims; no general auto-approval."""
from pathlib import Path
import hashlib
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
from bind_monograph_citation_claims import record_digest

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,value):
 p.parent.mkdir(parents=True,exist_ok=True)
 tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(p)

# These four exact contexts received the scoped author judgments below.
# A matching citation key alone never authorizes a new or changed claim.
REVIEWED_CONTEXTS={
 'sfcstr2026':'50057be3a797ee68d5ee1b9e05d52de0954f5fe1b182d03bb842ff0ecc7d4ff7',
 'jfiu2026transition':'1775cc8269006f460c0551db235173af391933526d2b34c81c649945cf89a533',
 'sfcgiftfaq':'1775cc8269006f460c0551db235173af391933526d2b34c81c649945cf89a533',
 'sfctokenised2023':'e6d3cffcabe9391a68f5b61572731232aa3b597ddaa929312c9b9c34d8a2d9e4'}
SPACING_PREDECESSORS={
 'jfiu2026transition':'8deb1eccf25fbadab4706b0f9718f972eeb74f832129008ba15454e0a6497cc5',
 'sfcgiftfaq':'8deb1eccf25fbadab4706b0f9718f972eeb74f832129008ba15454e0a6497cc5',
 'sfctokenised2023':'59006ab719477d38d731398978017b7e155d87a496d5a712ee7be086d2f2ee72'}

SOURCES={
 'sfctokenised2023':{
  'title':'Circular on intermediaries engaging in tokenised securities-related activities',
  'author_filename':'SFC','year':'2023','source':'23ec52.json',
  'url':'https://apps.sfc.hk/edistributionWeb/api/circular/content?refNo=23EC52&lang=EN',
  'read_scope':'Complete official circular HTML body and footnotes; particularly paragraphs 5-7, 17-18, 24, 28-29 and footnote 7. Separate Appendix not part of this source inspection.',
  'support':'Paragraph 28 distinguishes tokenised securities from AMLO virtual assets for the Terms and Conditions. Footnote 7 states the objective-or-intention threshold, with GAV as denominator. Classification of instruments and the complete incorporated authority are not automated by this inspection.',
  'limitations':'Author-created reference cases interpret this selected provision. The separately linked Appendix and referenced legislation are not thereby formalized. Pretraining exposure is unknown; this is not an independent accuracy experiment.',
  'quote':'the intention of a fund is to invest 10% or more of its gross asset value (GAV) in virtual assets'},
 'jfiu2026transition':{
  'title':'Announcement of the launch of STREAMS 2 on 2026-02-02',
  'author_filename':'JFIU','year':'2026','source':'jfiu-home.html','url':'https://www.jfiu.gov.hk/en/',
  'read_scope':'Complete retained launch announcement: background, methods, registration, four transition arrangements and enquiries; navigation and unrelated fraud announcement separated.',
  'support':'The announcement corroborates method-specific electronic-certificate requirements, the 09:00 resumption, urgent direct contact, migration and separately supplied XML information. Its wording does not supply operational certificate mechanics or the XML specification.',
  'limitations':'This announcement is not a technical interface specification or a resubmission deadline. The inspection does not prove the absence of later or private technical guidance.',
  'quote':'liaise with JFIU as soon as possible for arrangement of technical test'},
}

def archive_sources():
 archive_path=ROOT/'docs/papers/monograph-citation-archive.json';archive=read(archive_path)
 reading_path=ROOT/'docs/monograph/review/revision/citation-reading.json';reading=read(reading_path)
 bib=ROOT/'docs/monograph/references.bib';bib_text=bib.read_text()
 for key,s in SOURCES.items():
  original=ROOT/'artifacts/interpretation/round14/sources-official'/s['source']
  path=ROOT/'docs/papers'/(s['title']+'_'+s['author_filename']+'('+s['year']+')'+original.suffix)
  if path.exists() and path.read_bytes()!=original.read_bytes():raise ValueError('Archived edition changed')
  path.write_bytes(original.read_bytes())
  row={'key':key,'title':s['title'],'author_filename':s['author_filename'],'year':s['year'],
   'path':str(path.relative_to(ROOT)),'sha256':sha(path),'source_url':s['url'],
   'retained_inputs':[str(original.relative_to(ROOT))],'status':'local_copy_retained',
   'claim_support':'scoped_author_review_round14','currentness':'Retained edition; no later-authority exclusion claim',
   'publication_status':'Official regulator or government publication','extraction_tool':'HTMLParser over exact retained bytes'}
  existing=next((r for r in archive['sources'] if r['key']==key),None)
  if existing and existing!=row:raise ValueError('Existing citation source differs')
  if not existing:archive['sources'].append(row)
  record={'read_scope':s['read_scope'],'support':s['support'],'limitations':s['limitations'],
          'quotes':[{'location':s['read_scope'],'text':s['quote']}]}
  if key in reading['sources'] and reading['sources'][key]!=record:raise ValueError('Existing reading record differs')
  reading['sources'][key]=record
  if '{'+key+',' not in bib_text:
   author='Securities and Futures Commission' if s['author_filename']=='SFC' else 'Joint Financial Intelligence Unit'
   bib_text+='\n@misc{'+key+',\n  author = {{'+author+'}},\n  title = {'+s['title']+'},\n  year = {'+s['year']+'},\n  url = {'+s['url']+'}\n}\n'
 archive['round14_addition']={'keys':list(SOURCES),'basis':'Exact public-authority bytes; scoped author reading'}
 save(archive_path,archive);save(reading_path,reading);bib.write_text(bib_text)


def bind_unit(*, refresh=False):
 from check_reader_facing_monograph import occurrences
 book=ROOT/'docs/monograph';unit=book/'chapters/06d-invariant-decisions.tex'
 occurrences_new=occurrences(unit,book)
 archive={r['key']:r for r in read(ROOT/'docs/papers/monograph-citation-archive.json')['sources']}
 readings=read(book/'review/revision/citation-reading.json')['sources']
 reviews_path=book/'review/reader-facing/citation-occurrence-review.json';reviews=read(reviews_path)
 judgments={
  'sfcstr2026':'The retained circular supplies the calendar wording and explicit 09:00 operational time. The competing applicability example is a local hypothesis, not a claim that the regulator endorsed both readings.',
  'jfiu2026transition':SOURCES['jfiu2026transition']['support']+' '+SOURCES['jfiu2026transition']['limitations'],
  'sfcgiftfaq':'Q1 addresses promotions linked to product type or fund house. Its four retained answers do not specify a dominant-character or inseparability test for a mixed package. The statement is bounded to this inspected FAQ, not all applicable law.',
  'sfctokenised2023':SOURCES['sfctokenised2023']['support']+' '+SOURCES['sfctokenised2023']['limitations']}
 if {c['key'] for c in occurrences_new}!=set(judgments) or len(occurrences_new)!=4:
  raise ValueError('New claims changed; scoped review required')
 prior=sha(reviews_path);changed=False
 for c in occurrences_new:
  if c['context_sha256']!=REVIEWED_CONTEXTS[c['key']]:
   raise ValueError('Unreviewed source claim; a new scoped author judgment is required')
  if any(r['id']==c['id'] for r in reviews['occurrences']):
   old=next(r for r in reviews['occurrences'] if r['id']==c['id'])
   if old['context_sha256']!=c['context_sha256']:
    if not refresh or old['context_sha256']!=SPACING_PREDECESSORS.get(c['key']):
     raise ValueError('Changed reviewed context is not the inspected spacing repair')
    old['context_sha256']=c['context_sha256']
    old['context_refresh_reason']='Round-14 typographic spacing repair; source claim and wording unchanged.'
    changed=True
   continue
  reviews['occurrences'].append({'id':c['id'],'key':c['key'],'context_sha256':c['context_sha256'],
    'source_sha256':archive[c['key']]['sha256'],'reading_record_sha256':record_digest(readings[c['key']]),
    'review_group':'round14-conditional-invariance','decision':'supported_in_stated_scope',
    'judgment':judgments[c['key']]})
  changed=True
 if changed:
  reviews['round14_review']={'prior_sha256':prior,'claims':4,
     'basis':'Explicit author inspection of four fixed passages; no independent legal adjudication'}
  save(reviews_path,reviews)
 print('Verified four explicitly reviewed citation occurrences'+(' and saved their binding' if changed else ' without changing the review'))

if __name__=='__main__':
 if len(sys.argv)==2 and sys.argv[1]=='--archive-only':archive_sources()
 elif len(sys.argv)==1:bind_unit()
 elif len(sys.argv)==2 and sys.argv[1]=='--refresh':bind_unit(refresh=True)
 else:raise SystemExit('Supported arguments: --archive-only, --refresh, or none to bind reviewed unit')
