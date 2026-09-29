; benchmark generated from python API
(set-info :status unknown)
(declare-fun explanation_requested () Bool)
(declare-fun streamlined () Bool)
(declare-fun complex_product () Bool)
(declare-fun solicited () Bool)
(assert
 (let (($x86 (not (and streamlined (not explanation_requested)))))
(let (($x70 (not (and (not solicited) (not complex_product)))))
(let (($x67 (ite $x70 $x86 false)))
(let (($x99 (or solicited complex_product)))
(let (($x31 (and $x99 (or (not streamlined) explanation_requested))))
(or (not true) (and (distinct $x31 $x67) true))))))))
(check-sat)
