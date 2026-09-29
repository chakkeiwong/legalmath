; benchmark generated from python API
(set-info :status unknown)
(declare-fun complex_product () Bool)
(declare-fun solicited () Bool)
(declare-fun streamlined () Bool)
(assert
 (let (($x15 (not (and (not solicited) (not complex_product)))))
(let (($x92 (ite streamlined false $x15)))
(let (($x87 (not streamlined)))
(let (($x60 (and (or solicited complex_product) $x87)))
(or (not true) (and (distinct $x60 $x92) true)))))))
(check-sat)
