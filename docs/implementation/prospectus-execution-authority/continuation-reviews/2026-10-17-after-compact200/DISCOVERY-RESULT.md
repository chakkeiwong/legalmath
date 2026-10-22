# Bounded official-source discovery

Four search queries and eight top-level official-resource openings were used.
Redirects are retained in the effective URLs below. No challenge was solved,
access control bypassed, package installed, model called or prospectus reread.
The retained files are discovery evidence, not interpreted legal authorities.

| Request | Exact query or URL | Actual outcome |
|---|---|---|
| query01 | Google: `site:bportugal.pt RGICSF 2009 artigos 112 114 imóveis dois anos` | HTTP200,93076bytes; search interstitial, no relevant candidate |
| query02 | Bing: `site:bportugal.pt "RGICSF" "2009" "112"` | HTTP200,120239bytes; unrelated Apple results, unusable |
| query03 | Bing: `site:diariodarepublica.pt "298/92" "114" "1992"` | HTTP200,121180bytes; unrelated Hong Kong results, unusable |
| query04 | DuckDuckGo HTML: `RGICSF Banco Portugal 2009 112 114` | HTTP202,14302bytes; human challenge, no source evidence |
| official01 | `https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32008R1126` | HTTP202,0bytes |
| official02 | `https://www.bportugal.pt/page/regime-geral-das-instituicoes-de-credito-e-sociedades-financeiras-rgicsf` | HTTP403,1002119bytes; security challenge |
| official03 | `https://eur-lex.europa.eu/eli/reg/2008/1126/oj/eng` | HTTP202,0bytes |
| official04 | `https://data.dre.pt/eli/dec-lei/298/1992/12/31/p/dre/pt/html` | HTTP200,2346bytes; official redirect to `https://diariodarepublica.pt/dr/detalhe/decreto-lei/298-1992-448953`; JavaScript shell, no statute text |
| official05 | `https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32008R1126` | HTTP202,0bytes |
| official06 | `https://publications.europa.eu/resource/celex/32008R1126` | HTTP200,3217195bytes; official Cellar RDF metadata; effective URL `http://publications.europa.eu/resource/cellar/275df5e6-576e-4ea9-a81a-b299c0d9e53c/rdf/object/full` |
| official07 | HEAD `https://data.dre.pt/eli/dec-lei/298/1992/12/31/p/dre/pt/pdf` | HTTP405 after redirect to official error page; no PDF identified |
| official08 | `https://publications.europa.eu/resource/oj/JOL_2008_320_R_0001_01.ENG`, Accept `application/rdf+xml` | HTTP200,4057bytes; English-expression metadata; effective URL `http://publications.europa.eu/resource/cellar/275df5e6-576e-4ea9-a81a-b299c0d9e53c.0006/rdf/object/full` |

All curl calls used5second connection and20second total bounds, no retries and
one-second tool yields. The original metadata response exceeded the requested
2097152byte curl size option despite exit0; its actual3217195bytes are retained
and must be charged. A subsequent acquisition must enforce its own actual-byte
bound rather than trust that option or HTTP status alone.

The official metadata independently identifies Commission Regulation1126/2008,
dated3November2008, published/entering into force2December2008, and English
PDF/XHTML/Formex manifestations. The original work links historical consolidated
CELEX02008R1126-20081221 and02008R1126-20091227. These are genuine accounting
source candidates. The complete texts, IFRS5 paragraphs, amendments and annual
period/early-adoption effects have not yet been inspected. A consolidation date
alone cannot establish the standard applicable to a particular financial year.

The Portuguese original decree has an official identity, but neither its
articles112/114 nor their2008/2009 amendment history has been obtained. This
is a specific acquisition gap, not evidence that the law is absent. The report's
two-year/extension account remains a report claim.

Decision: prepare one reviewed cumulative source06 continuation limited to
acquiring and conditionally comparing the official accounting sources. Keep
the Portuguese-law gap separate. Preserve six prior admissions, the complete
source06/006 and source07 answer chains, all59 obligations and44tasks, and the
original003-onward1080second/160MiB limits. No further discovery call is
authorized by this preparation pass.
