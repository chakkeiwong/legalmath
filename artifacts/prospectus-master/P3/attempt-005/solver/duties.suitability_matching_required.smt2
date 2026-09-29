; benchmark generated from python API
(set-info :status unknown)
(declare-fun complex_product () Bool)
(declare-fun solicited () Bool)
(declare-fun streamlined () Bool)
(assert
 (let (($x58 (not (and (not solicited) (not complex_product)))))
(let (($x34 (ite streamlined false $x58)))
(let (($x60 (not streamlined)))
(let (($x16 (and (or solicited complex_product) $x60)))
(or (not true) (and (distinct $x16 $x34) true)))))))
(check-sat)
