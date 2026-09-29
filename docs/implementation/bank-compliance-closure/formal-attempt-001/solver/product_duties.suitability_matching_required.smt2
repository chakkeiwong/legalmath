; benchmark generated from python API
(set-info :status unknown)
(declare-fun complex_product () Bool)
(declare-fun solicited () Bool)
(declare-fun streamlined () Bool)
(assert
 (let (($x70 (not (and (not solicited) (not complex_product)))))
(let (($x87 (ite streamlined false $x70)))
(let (($x33 (not streamlined)))
(let (($x111 (and (or solicited complex_product) $x33)))
(or (not true) (and (distinct $x111 $x87) true)))))))
(check-sat)
