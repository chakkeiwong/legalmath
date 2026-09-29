; benchmark generated from python API
(set-info :status unknown)
(declare-fun required_minimum_usd_cents () Int)
(declare-fun enhanced_scrutiny () Bool)
(declare-fun senior_foreign_political_figure () Bool)
(declare-fun failure_procedures () Bool)
(declare-fun activity_review_and_reporting () Bool)
(declare-fun funds_and_purpose () Bool)
(declare-fun political_figure_screen () Bool)
(declare-fun owner_identity () Bool)
(assert
 (>= required_minimum_usd_cents 0))
(assert
 (let (($x117 (or (not owner_identity) (not political_figure_screen) (not funds_and_purpose) (not activity_review_and_reporting) (not failure_procedures) (and senior_foreign_political_figure (not enhanced_scrutiny)))))
(let (($x118 (not $x117)))
(let (($x27 (and owner_identity political_figure_screen funds_and_purpose activity_review_and_reporting failure_procedures (or (not senior_foreign_political_figure) enhanced_scrutiny))))
(or (not true) (and (distinct $x27 $x118) true))))))
(check-sat)
