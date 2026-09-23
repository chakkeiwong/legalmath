# Ensemble and uncertainty additions for the monograph

22 September 2026. These notes extend the existing technical reading notes and
`docs/research/interpretation-search.md`. Full texts are retained in `docs/papers`
with hashes and edition metadata in `manifest.json`. The three additions were
parsed through the adjacent ResearchAssistant parsing modules; retained parse
records are in `.localresources/monograph/text`. No published benchmark was rerun.

## Self-consistency: Wang et al., ICLR 2023

Inspected arXiv 2203.11171v4, 24 pages: section 2 sampling and aggregation, section 3
experimental setup/results, and relevant sampling/aggregation appendix material.
The method samples reasoning paths and marginalizes/aggregates final answers,
contrasting this with one greedy path. The evaluation uses particular reasoning
benchmarks, prompt settings, sample counts and repeated runs. Those are empirical
results on those tasks, not evidence of independent legal readers.

Borrow the distinction between path generation and answer aggregation, and retain
the initial samples before deliberation. Do not equate sample count with independent
expert count or interpret an answer frequency as calibrated legal correctness.
No original-author method implementation was established as a separate verified
library in this review; the monograph makes no source-code fidelity claim for it.

## Semantic uncertainty: Kuhn, Gal and Farquhar, ICLR 2023

Inspected arXiv 2302.09664v3, 19 pages: sections 3–4 (meaning classes, probability
aggregation and entropy), section 6 (evaluation), section 7 limitations, appendix
A.1–A.2 (clustering and estimation). Meaning classes aggregate surface strings;
uncertainty in that model distribution is not uncertainty about an externally
adjudicated legal truth. The paper's evaluation includes answer-quality proxies
and ranking metrics; it does not establish legal probability calibration.

The NLI approximation to meaning classes can be nontransitive and order-sensitive.
This prevents treating it as a formal equivalence relation on interpretations.
Use clustering to propose review groups; do not erase dissent or merge source
assumptions solely because an NLI model groups the text.

Official source inspected:
`lorenzkuhn/semantic_uncertainty`, commit
`20e0ee1388e776e48c1ee285e00462aabc6cf35a`,
`code/get_semantic_similarities.py`, especially lines 99–114. The branch rejects a
pair when either directional prediction is label 0; otherwise it merges. The
separately retrieved `microsoft/deberta-large-mnli` configuration maps 0 to
contradiction, 1 to neutral and 2 to entailment. Thus the inspected source permits
neutral predictions, a broader condition than mutual entailment. The code also
uses `list(set(...))` and pairwise label reassignment; it is not a formally checked
semantic partition algorithm. No GPU/model execution was performed.

Retained files: `.localresources/monograph/semantic-code.py`,
`semantic-code-tree.json`, `deberta-mnli-config.json`. The model configuration was
retrieved from its public current URL, not the historical code commit. Its local
hash is retained in the final review manifest. A deployment must pin both.

## Conformal prediction: Angelopoulos and Bates, reviewed 2022 edition

Inspected arXiv 2107.07511v6, 51 pages: section 1.1 score/quantile/set construction,
section 3 marginal versus conditional coverage, shift discussion, and appendix D
coverage proof. The monograph derives the rank argument for a fixed scoring rule
with exchangeable calibration and test scores, using the kth order statistic with
k=ceil((n+1)(1-alpha)), an infinite threshold when k=n+1, and inclusive set membership.

The paper's theorem is a statistical coverage result under its assumptions.
Borrow set-valued output only for a precisely defined target with suitable heldout
calibration. The result does not guarantee every circular's conditional coverage,
withstand arbitrary distribution shift, or recover a legal reading absent from
the candidate label space. Labels and adjudication quality remain assumptions.

Inspected the official tutorial notebook
`aangelopoulos/conformal-prediction/notebooks/imagenet-smallest-sets.ipynb` as
source, retained at `.localresources/monograph/conformal-code.ipynb`. Its score is
based on the heldout true-class output and its set threshold uses the calibrated
quantile. No image experiment was run, and its model or dataset settings are not
proposed legal defaults. The monograph specifies the order statistic directly
rather than depending on a library's interpolation conventions.

## Dependence calculation and inaccessible lead

The common-failure mixture q+(1-q)p^m and equicorrelation variance calculation are
local derivations under explicitly stated illustrative assumptions. They are not
empirical estimates of model dependence. The Knight–Leveson N-version-programming
paper was identified as a relevant lead, but the attempted author-hosted full
text timed out in both restricted and trusted retrieval. Metadata is retained;
its uninspected empirical results are not used as evidence in the manuscript.

## Earlier sources and software

The monograph also uses the technically inspected sources in `reading-notes.md`,
`reading-notes-v2.md` and `docs/research/interpretation-search.md`. It preserves
restrictions on Catala's mechanization, Stipula/KeY event abstractions, the distinct
reachability restrictions, eFLINT versions, ARc's empirical denominator, AGATHA's
search/evaluation assumptions, ASPIC+ corrections, Carneades version differences,
and ToT/LATS/GBS transfer limits. Retained original code inspection is not described
as replay of those tools' proofs or experiments.
