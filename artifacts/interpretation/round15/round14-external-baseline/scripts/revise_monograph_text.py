"""Apply documented corrections without deleting the retained source units."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / 'docs/monograph'
REG = BOOK / 'review/revision/text-edits.json'


def main():
    record = json.loads(REG.read_text()) if REG.exists() else {'edits': [], 'additions': {}}
    def edit(file, old, new, reason):
        path = BOOK / file
        if any(e['path'] == str(path.relative_to(ROOT)) and e['old'] == old
               and e['new'] == new for e in record['edits']):
            return  # Later registered corrections may refine this replacement.
        text = path.read_text()
        if new in text and old not in text:
            return
        assert text.count(old) == 1, (file, old[:80], text.count(old))
        path.write_text(text.replace(old, new, 1))
        record['edits'].append({'path': str(path.relative_to(ROOT)), 'old': old,
                                'new': new, 'reason': reason})
        REG.write_text(json.dumps(record, indent=2, ensure_ascii=False)+'\n')

    edit('chapters/06-ensemble.tex',
         'If $q=0.02$, $p=0.1$ and $m=3$, the expression gives $0.02098$. Treating the three\n'
         'members as unconditionally independent would instead give $0.001$. Adding',
         'If $q=0.02$, $p=0.1$ and $m=3$, the expression gives $0.02098$. Each\n'
         'member then has marginal error probability $r=q+(1-q)p=0.118$. A fair\n'
         'independence comparison holds that marginal probability fixed: three\n'
         'independent members would all fail with probability $r^3=0.001643032$.\n'
         'The smaller value $0.001=p^3$ describes residual errors conditional on\n'
         'the common failure being absent; it is a different comparison. Adding',
         'Correct a conditional-versus-marginal comparator error; retain and explain the original numerical value.')
    edit('chapters/06-ensemble.tex',
         'Suppose $X_i$ records whether member $i$ makes a particular error, all have variance\n'
         '$\\sigma^2$, and every pair has correlation $\\rho$. Expanding the variance of their\n'
         'mean gives',
         'Suppose $X_i$ records whether member $i$ makes a particular error. For\n'
         '$m\\geq2$, assume equal nonzero variance $\\sigma^2$ and common pairwise\n'
         'correlation $\\rho$. These must describe an attainable joint distribution.\n'
         'In particular, its correlation matrix requires\n'
         '$-1/(m-1)\\leq\\rho\\leq1$; Bernoulli indicators can impose further\n'
         'restrictions. There are $m$ variance terms and $m(m-1)$ ordered covariance\n'
         'terms when the squared sum is expanded, giving',
         'State nondegeneracy and feasible-correlation assumptions and expose the covariance count.')
    edit('monograph.tex', '22 September 2026\\hfill Unified author draft, version 1.1',
         '23 September 2026\\hfill Expanded author draft, version 1.2', 'Date the present revision.')
    edit('monograph.tex',
         'walkthrough. Its drafting provider is a deterministic fixture. The ensemble\n'
         'extension E01--E14 is a specified next development, with ten companion schemas,\n'
         'finite control flow and acceptance cases.',
         'walkthrough. On 23 September, the E01--E09 interpretation extension completed\n'
         'a scripted engineering increment: the retained acceptance records 205 tests,\n'
         '35 RuleIR cases, 42 generated contracts and a 33-path API. It executes\n'
         'supplied proposals and repairs under bounded control. E10--E14 still concern\n'
         'live providers, independent reference construction, comparative evaluation,\n'
         'optional search and bank integration.',
         'Separate the retained 22 September evidence from the inspected E01–E09 execution report.')
    edit('chapters/07-verification.tex',
         'MVP test suite and the separate second-circular exercise. The new ensemble is not\n'
         'yet an implemented live-model product. The appropriate next engineering step is\n'
         'to implement its controller and contracts, then run deterministic acceptance\n'
         'scenarios, then evaluate interpretation performance with independent reference\n'
         'judgments.',
         'MVP test suite, the separate second-circular exercise and the later E01--E09\n'
         'scripted controller acceptance. The controller and its deterministic\n'
         'acceptance scenarios now exist. The next empirical step requires independent\n'
         'reference judgments and restricted live-provider evaluation. No implemented\n'
         'live-model product has yet established legal-interpretation performance.',
         'Update the next step without promoting scripted checks into live-model evidence.')
    edit('chapters/08-implementation.tex',
         'The companion contracts define the proposed \\texttt{interpretation.v1} extension.\n'
         'They are stored in \\texttt{docs/monograph/contracts}. These are design contracts\n'
         'and examples, not\n'
         'a claim that the service is already implemented.',
         'The companion contracts define the \\texttt{interpretation.v1} extension.\n'
         'They are stored in \\texttt{docs/monograph/contracts}. E01--E09 now implement\n'
         'the public-source, scripted increment described below. The retained task\n'
         'descriptions state its obligations; provider integration, independent\n'
         'evaluation and bank deployment remain later work.',
         'Remove a stale assertion that the interpretation service is wholly unimplemented.')
    edit('chapters/08-implementation.tex',
         'These paths are proposed additions, not descriptions of endpoints already present\n'
         'in the retained OpenAPI file. The implementation task must generate a new OpenAPI\n'
         'contract from actual request models and test it against the service.',
         'These paths preserve the original design sketch. The executed E01--E09\n'
         'increment has a generated 33-path OpenAPI contract whose exact request\n'
         'models govern the implemented interface. Some proposed paths were\n'
         'consolidated or renamed; a caller must use that generated contract.',
         'Keep the original interface concept while preventing use of stale endpoint sketches.')
    edit('chapters/08-implementation.tex',
         '\\caption{Ordered work packages for the proposed extension.}',
         '\\caption{Extension work packages. E01--E09 have scripted engineering acceptance;\n'
         'E10--E14 remain prospective.}',
         'Make task-table status intelligible at the point of reading.')
    edit('chapters/08a-executed-workbench.tex',
         '\\section{What the complete local execution actually established}',
         '\\section{What the 22 September local execution established}',
         'Identify the historical evidence date instead of conflating it with the newer increment.')
    edit('chapters/08a-executed-workbench.tex',
         'These paths supply the current execution route. The interpretation-run and\n'
         'issue-adjudication paths later in this chapter are proposed additions with\n'
         'separate records and budgets. In particular, the current drafting endpoint is\n'
         'not the ensemble controller described in Chapter~\\ref{ch:ensemble}.',
         'These paths supply the earlier 22-path execution route. The later E01--E09\n'
         'increment adds interpretation operations with separate records and budgets,\n'
         'bringing the generated API to 33 paths. The original drafting endpoint\n'
         'retains its separate deterministic-fixture behavior.',
         'Preserve the historical API while explaining its relation to the current extension.')
    edit('chapters/09-evaluation.tex',
         'The immediate conclusion remains limited: the proposed method is ready to be\n'
         'implemented as a bounded, testable extension, and its empirical legal-interpretation\n'
         'performance remains to be established.',
         'The bounded controller now has scripted engineering acceptance. Its\n'
         'empirical legal-interpretation performance remains to be established by\n'
         'the independently adjudicated study described here.',
         'Bring the research conclusion into agreement with the executed engineering status.')
    edit('chapters/10-operation.tex',
         "convention: the title, a comma, the first author's surname and the year in",
         "convention: the title, an underscore, the first author's surname and the year in",
         'Use the filename convention explicitly requested for this audit.')
    edit('chapters/10-operation.tex',
         'The first step is contract implementation with public sources and scripted\n'
         'members. This establishes that the ensemble can preserve alternatives, detect',
         'The first step, implemented in E01--E09, uses public sources and scripted\n'
         'members. Its acceptance checks show that the controller can preserve alternatives, detect',
         'Update the implementation sequence while retaining the ordered research stages.')
    edit('chapters/10-operation.tex',
         'A completed deterministic prototype will establish that the specified records,\n'
         'controller, budgets, reports and release checks behave as tested. It will produce\n'
         'actual Java packages from accepted RuleIR and preserve the existing deterministic\n'
         'execution contract. It will demonstrate that known omissions and persistent\n'
         'ambiguities lead to the intended different outcomes in scripted scenarios.',
         'The completed E01--E09 deterministic increment supplies test evidence for\n'
         'the specified records, controller, budgets, reports and release checks.\n'
         'It produces Java packages from accepted RuleIR and preserves the existing\n'
         'execution contract. Its scripted scenarios distinguish repair of a known\n'
         'encoding omission from an ambiguity that remains unresolved.',
         'State the actual completed increment precisely; preserve the limitation to supplied scripts.')
    edit('chapters/04-languages.tex',
         '\\citep[sec.~4]{legalinterpretations2014,legalruleml2021}. This is a strong basis',
         '\\citep[sec.~4]{legalinterpretations2014}. The standard describes the relevant\n'
         'requirements and contextual annotations in sections 2.2--2.3\n'
         '\\citep{legalruleml2021}. This is a strong basis',
         'Give the interpretation paper and later standard their separately checked source anchors.')
    edit('chapters/05-search.tex',
         'A concentration on one class produces lower entropy than an even distribution',
         'Here the nonnegative class probabilities sum to one, and a zero-probability\n'
         'class contributes zero, using the limiting convention $0\\log 0=0$.\n'
         'A concentration on one class produces lower entropy than an even distribution',
         'State the probability normalization and zero-mass convention required by entropy.')
    edit('chapters/04-languages.tex',
         'Four contract examples establish feasibility for the\nreported translation and properties.',
         'The authors report automatic verification of four contract examples for the\n'
         'selected translation and properties. This is reported feasibility evidence\n'
         'whose exact executable inputs must still be reconciled with the appendix.',
         'Distinguish the reported result from an independently reproduced result after finding invalid Java in the retained appendix.')
    edit('chapters/04-languages.tex',
         'This is worth a bounded experiment if workflow verification proves important.',
         'The retained extended version also contains a concrete reproducibility\n'
         'problem. Appendix B.3 declares Boolean parameters in methods that add\n'
         'those parameters to integer asset balances. Java rejects that arithmetic;\n'
         'the printed example is not compilable as written. A rendering check\n'
         'confirmed the declarations, and a minimal compiler diagnostic confirmed\n'
         'the type error. This does not determine what files were used for the\n'
         'reported experiment. Adoption requires the exact verified sources,\n'
         'correction of the discrepancy and a replay of the proof obligations\n'
         '\\citep[app.~B.3, pp.~31--32]{stipulakey2025}.\n\n'
         'This is worth a bounded experiment if workflow verification proves important.',
         'Expose a checked appendix defect without claiming that it disproves an unreproduced experiment.')
    edit('chapters/04-languages.tex',
         'the type error. This does not determine what files were used for the\n',
         'the type error. The pinned official repository also contains the same\n'
         'Boolean parameters in \\texttt{Deposit.java}; compiling that complete\n'
         'file produces eleven Java type errors \\citep{stipulakeycode}.\n'
         'This does not determine what files were used for the\n',
         'Report a direct compiler check of the pinned official example, distinct from the minimal diagnostic.')
    edit('chapters/04-languages.tex',
         'and states that the liquidity implementation is still being developed. Borrowing\n',
         'and states that the liquidity implementation is still being developed.\n'
         'That is the paper\'s historical status: the separately retained workbench\n'
         'repository includes a Python liquidity analyzer and a configurable bound\n'
         'on function repetitions \\citep{stipulacode}. Source inspection confirms\n'
         'its presence, but neither its correctness nor production suitability has\n'
         'been established by execution here. Borrowing\n',
         'Distinguish the historical paper status from the subsequently inspected repository implementation.')
    edit('chapters/05-search.tex',
         'not exhaustive breadth-first enumeration. String deduplication in the code does\n'
         'not ensure that the retained thoughts express different legal hypotheses.',
         'not exhaustive breadth-first enumeration. In the value-based branch,\n'
         'an exact duplicate string receives a zero score; it is not necessarily\n'
         'removed from the candidate list. This check cannot establish that the\n'
         'retained thoughts express different legal hypotheses.',
         'Match the pinned official BFS code: duplicate values are suppressed, not necessarily removed.')
    edit('chapters/05-search.tex',
         'For the first prototype, a deterministic scheduler with family coverage and',
         'Tree search also assumes that trial actions can be undone or replayed.\n'
         'The LATS paper makes this environmental assumption explicit. A bank\n'
         'cannot treat a completed payment or a disclosure of client information\n'
         'as a reversible trial. Here, search operates on hypothetical cases and\n'
         'retained evidence; authority to perform a real transaction belongs to\n'
         'the separately controlled host workflow.\n\n'
         'For the first prototype, a deterministic scheduler with family coverage and',
         'State the source method’s rollback assumption at the point of proposed bank reuse.')
    edit('chapters/04-languages.tex',
         'works. The unified library now retains 50 editions representing 49 works,\n'
         'including the later legal-search and uncertainty studies.',
         'works. The first unified library retained 50 editions representing 49 works,\n'
         'including the later legal-search and uncertainty studies. The present\n'
         'audit adds two legal-reliability studies, bringing the academic collection\n'
         'to 52 editions representing 51 works. Regulatory documents, standards\n'
         'and software records are retained alongside them.',
         'Preserve the historical library count while stating the expanded collection accurately.')
    edit('chapters/04-languages.tex',
         'Permissions add another distinction. A weak permission is obtained when an\n'
         'opposite obligation cannot be established; a strong permission has explicit\n'
         'normative support.',
         'Permissions add another distinction. In this proof theory, a weak permission\n'
         'requires a derivation establishing that the opposite obligation is not\n'
         'derivable; an unfinished search or an empty database response is insufficient.\n'
         'A strong permission has explicit normative support.',
         'Match Definition 33: constructive negative proof is stronger than mere failure to find a positive proof.')
    edit('chapters/04-languages.tex',
         'is a substantive modeling step, not something the taxonomy infers from prose.\n'
         'The MVP consequently supports',
         'is a substantive modeling step, not something the taxonomy infers from prose.\n'
         'The printed definition of maintenance violation also needs correction:\n'
         'Definition 14 on page 15 uses membership in the set of fulfilled conditions\n'
         'where the adjacent prose and Figure 3.5 require non-membership. As printed,\n'
         'a trace that satisfies the duty throughout could be called a violation.\n'
         'An implementation must check the intended condition explicitly instead of\n'
         'copying that formula.\n'
         'The MVP consequently supports',
         'Expose a source formula/prose inconsistency confirmed on the rendered source page; retain the substantive taxonomy.')
    edit('chapters/05-search.tex',
         'An argument is a chain from premises to a conclusion. Some steps are strict:',
         'An argument is a chain or tree from premises to a conclusion. A tree joins\n'
         'the separate reasons needed for a conclusion with several premises. Some steps are strict:',
         'Preserve conjunctive premise structure in the inspected argumentation framework.')
    edit('chapters/01-problem.tex',
         'The broader application acceptance contains 154 passing tests, but its drafting\n',
         'The 22 September application acceptance contains 154 passing tests, but its drafting\n',
         'Date the historical count so it does not contradict the later E01–E09 increment.')
    edit('chapters/09-evaluation.tex',
         'trials with unknown error probability $p$. Under this simplified binomial model,',
         'trials, where $n\\geq1$, with unknown error probability $p$. Choose\n'
         '$0<\\alpha<1$. Under this simplified binomial model,',
         'State the domain required by the zero-error binomial upper bound.')
    edit('chapters/09-evaluation.tex',
         'Choose a target miscoverage level $\\alpha$ and define',
         'For an integer $n\\geq1$, choose a target miscoverage level\n'
         '$0<\\alpha<1$ and define',
         'Exclude undefined order-statistic and probability boundary cases.')
    edit('chapters/09-evaluation.tex',
         'The business case should use measured labor and maintenance effort. Let $K$ be',
         'The business case should use measured labor and maintenance effort. Let $K>0$ be',
         'Make the positive setup-cost assumption explicit for the no-break-even conclusion.')
    edit('chapters/09-evaluation.tex',
         '$nM=K+nA$. It is a planning relation, not an estimated return.',
         '$nM=K+nA$. For a whole number of changes, the first cost-saving or\n'
         'cost-neutral count is the ceiling of this ratio. It is a planning\n'
         'relation, not an estimated return.',
         'Distinguish the continuous cost intersection from the first attainable integer count.')
    edit('chapters/05-search.tex',
         'With equal weights, this simply counts separated pairs.',
         'With unit weights, this simply counts separated pairs. A different common\n'
         'weight multiplies that count by the square of the weight.',
         'Correct the scale of the weighted disagreement count; equal weights need not equal one.')
    edit('monograph.tex',
         'research collection contains 50 paper editions representing\n49 works, including',
         'research collection now contains 52 paper editions representing\n51 works, including',
         'Synchronize the front-matter library count with the two added legal-reliability studies.')
    print(f"Registered {len(record['edits'])} reversible corrections.")


if __name__ == '__main__':
    main()
