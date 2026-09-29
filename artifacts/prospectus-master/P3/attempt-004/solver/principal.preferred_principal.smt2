; benchmark generated from python API
(set-info :status unknown)
(declare-fun principal () Int)
(declare-fun distribution () Int)
(assert
 (>= principal 0))
(assert
 (>= distribution 0))
(assert
 (or (not true) (and (distinct principal principal) true)))
(check-sat)
