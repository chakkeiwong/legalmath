; benchmark generated from python API
(set-info :status unknown)
(declare-fun lawful_funds () Bool)
(declare-fun declared () Bool)
(assert
 (let (($x15 (= (+ (ite declared 1 0) (ite lawful_funds 1 0)) 2)))
(let (($x23 (and declared lawful_funds)))
(and (distinct $x23 $x15) true))))
(check-sat)
