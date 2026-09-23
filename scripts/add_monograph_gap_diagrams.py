"""Add specific diagrams where rendered review found long teaching gaps."""
from pathlib import Path
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[1]
BOOK=ROOT/'docs/monograph'
REG=BOOK/'review/revision/text-edits.json'


def main():
    data=json.loads(REG.read_text())
    def put(file,ident,anchor,shape,a,b,c,caption,table=False):
        if ident in data['additions']:
            if table:
                entry=data['additions'][ident]
                path=ROOT/entry['path'];s=path.read_text()
                body=(ROOT/entry['content_file']).read_text()
                pattern=r'(% BEGIN REVISION ADDITION '+re.escape(ident)+r'\n).*?(% END REVISION ADDITION '+re.escape(ident)+r'\n)'
                s,n=re.subn(pattern,lambda m:m[1]+body+m[2],s,flags=re.S)
                assert n==1
                path.write_text(s)
                entry['sha256']=hashlib.sha256(body.encode()).hexdigest()
                REG.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
            return
        path=BOOK/'chapters'/file;s=path.read_text()
        assert s.count(anchor)==1,(file,anchor[:80],s.count(anchor))
        at=s.index(anchor)
        figure='\\begin{figure}[H]\n\\centering\n\\Teaching'+shape+'{'+a+'}{'+b+'}{'+c+'}\n\\caption{'+caption+'}\\label{fig:'+ident+'}\n\\end{figure}\n\n'
        if table:
            begins=list(re.finditer(r'\\begin\{longtable\}[^\n]*\n',s[:at]))
            begin=begins[-1]
            header=s[s.index('\\endfirsthead',begin.end())+len('\\endfirsthead'):s.index('\\endhead',begin.end())]
            figure='\\bottomrule\n\\end{longtable}\n\\begingroup\\normalsize\n'+figure+'\\endgroup\n'+begin[0]+header+'\\endhead\n'
        target=BOOK/'teaching'/(ident+'.tex');target.write_text(figure)
        # An input macro at a row boundary enters the next alignment cell before
        # bottomrule's noalign can execute. Keep table boundaries inline.
        body=figure if table else '\\input{\\LegalMathRoot teaching/'+ident+'}\n'
        addition='% BEGIN REVISION ADDITION '+ident+'\n'+body+'% END REVISION ADDITION '+ident+'\n'
        path.write_text(s[:at]+addition+s[at:])
        data['additions'][ident]={'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(body.encode()).hexdigest(),
            'reason':caption,'content_file':str(target.relative_to(ROOT)),'table_rows_removed':0}
        REG.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
    put('02-circular.tex','gap-spi-financial','\\caseheading{A one-word error changes the financial condition}',
        'Branch','Financial subcondition','Qualifying portfolio at least HK\\$40m','Qualifying net assets at least HK\\$80m','The two inclusive wealth routes remain alternatives.')
    put('02-circular.tex','gap-spi-consent','\\caseheading{Consent and continuing obligations outlive the initial decision}',
        'Flow','Selected category and agreed threshold','Written consent and explanation','Continuing review and withdrawal history','Qualification, agreement and continued availability are different questions.')
    put('02-circular.tex','gap-spi-dispositions','8.4--8.5 &',
        'Compare','Qualification and category','Exposure and transaction relief','Records, consent and continuing review','The provision inventory preserves responsibilities beyond the financial test.',True)
    put('02-circular.tex','gap-spi-inputs','Acknowledgment and consent &',
        'Compare','Reviewed client attributes','Transaction and exposure evidence','Consent and completed actions','The input table joins facts supplied by different operational owners.',True)
    put('04-languages.tex','gap-nli-evidence','ContractNLI adds a complementary annotation pattern.',
        'Compare','Entailed by the document','Contradicted by the document','Not mentioned','Evidence-based classification preserves the difference between contradiction and silence.')
    put('06-ensemble.tex','gap-resolution-table','Disputed',
        'Flow','Classify the discrepancy','Obtain the relevant evidence','Close only the question answered','Resolution requires evidence of the appropriate kind.',True)
    put('08a-executed-workbench.tex','gap-execution-original','The released original class is',
        'Flow','Original September decision','Synthetic one-cent amendment','Historical September replay','The retained execution checks change and historical reconstruction.')
    put('08a-executed-workbench.tex','gap-execution-tasks','T11 &',
        'Flow','Validate and evaluate typed rules','Build and check Java','Review, release and retain history','The completed tasks connect semantics to a controlled release.',True)
    put('08a-executed-workbench.tex','gap-execution-reproduce','The retained commands for engineering acceptance are:',
        'Flow','Fresh isolated demonstration','Inspect exact execution evidence','Keep prior accepted records intact','Reproduction creates new evidence without overwriting the original run.')
    put('08a-executed-workbench.tex','gap-execution-api','POST \\path|/fact-records|',
        'Flow','Prepare the tested release','Obtain exact-manifest approvals','Activate the approved version','The historical API separates preparation, approval and activation.',True)
    put('08a-executed-workbench.tex','gap-execution-limits','The operational limits are concrete.',
        'Compare','Synthetic local identity','In-memory host integration','Scripted drafting provider','The executed workbench still needs production identity, host and model evidence.')
    put('09-evaluation.tex','gap-evaluation-quality','Zero unresolved critical false approvals or missed duties',
        'Flow','Independent defect adjudication','Quality requirement satisfied','Compare total review effort','A time saving becomes relevant only after the required quality checks pass.')
    print('Registered gap diagrams without deleting table rows.')


if __name__=='__main__':main()
