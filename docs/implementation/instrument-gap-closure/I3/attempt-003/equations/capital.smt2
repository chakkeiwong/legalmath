; benchmark generated from python API
(set-info :status unknown)
(declare-fun cet1 () Int)
(declare-fun higher_amount () Int)
(declare-fun rwa () Int)
(assert
 (>= cet1 0))
(assert
 (>= higher_amount 0))
(assert
 (>= rwa 0))
(assert
 (> rwa 0))
(assert
 (let (($x18 (> (/ 7.0 100.0) (/ (to_real (+ cet1 higher_amount)) (to_real rwa)))))
(let (($x25 (> (* rwa 7) (* (+ cet1 higher_amount) 100))))
(and (distinct $x25 $x18) true))))
(check-sat)
