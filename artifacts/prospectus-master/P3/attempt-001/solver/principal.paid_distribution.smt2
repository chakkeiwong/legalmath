; benchmark generated from python API
(set-info :status unknown)
(declare-fun principal () Int)
(declare-fun distribution () Int)
(declare-fun dividend_declared () Bool)
(assert
 (>= principal 0))
(assert
 (>= distribution 0))
(assert
 (let ((?x25 (ite dividend_declared 0 distribution)))
(let ((?x54 (- distribution ?x25)))
(let ((?x24 (ite dividend_declared distribution 0)))
(or (not true) (and (distinct ?x24 ?x54) true))))))
(check-sat)
