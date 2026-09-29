; benchmark generated from python API
(set-info :status unknown)
(declare-fun explanation_requested () Bool)
(declare-fun streamlined () Bool)
(declare-fun complex_product () Bool)
(declare-fun solicited () Bool)
(assert
 (let (($x26 (not (and streamlined (not explanation_requested)))))
(let (($x58 (not (and (not solicited) (not complex_product)))))
(let (($x28 (ite $x58 $x26 false)))
(let (($x18 (or solicited complex_product)))
(let (($x63 (and (distinct (and $x18 (or (not streamlined) explanation_requested)) $x28) true)))
(or (not true) $x63)))))))
(check-sat)
