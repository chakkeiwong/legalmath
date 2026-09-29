; benchmark generated from python API
(set-info :status unknown)
(declare-fun principal () Int)
(declare-fun distribution () Int)
(declare-fun trigger () Bool)
(assert
 (>= principal 0))
(assert
 (>= distribution 0))
(assert
 (let ((?x65 (ite trigger principal 0)))
(let ((?x23 (- principal ?x65)))
(let ((?x24 (ite trigger 0 principal)))
(or (not true) (and (distinct ?x24 ?x23) true))))))
(check-sat)
