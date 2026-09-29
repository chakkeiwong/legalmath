; benchmark generated from python API
(set-info :status unknown)
(declare-fun rejection_reported_in_time () Bool)
(declare-fun transaction_rejected () Bool)
(assert
 (let ((?x15 (ite rejection_reported_in_time 1 0)))
(let ((?x86 (ite transaction_rejected 1 0)))
(let (($x29 (= (+ ?x86 ?x15) 2)))
(let (($x93 (and transaction_rejected rejection_reported_in_time)))
(or (not true) (and (distinct $x93 $x29) true)))))))
(check-sat)
