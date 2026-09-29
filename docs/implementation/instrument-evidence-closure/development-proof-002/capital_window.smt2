; benchmark generated from python API
(set-info :status unknown)
(declare-fun days_elapsed () Int)
(declare-fun capital_event () Bool)
(declare-fun full_redemption () Bool)
(assert
 (>= days_elapsed 0))
(assert
 (let (($x61 (ite (> days_elapsed 90) false (and full_redemption capital_event))))
(let (($x62 (and capital_event full_redemption (>= 90 days_elapsed))))
(and (distinct $x62 $x61) true))))
(check-sat)
