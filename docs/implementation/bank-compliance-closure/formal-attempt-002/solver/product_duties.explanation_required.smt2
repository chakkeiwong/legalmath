; benchmark generated from python API
(set-info :status unknown)
(declare-fun explanation_requested () Bool)
(declare-fun streamlined () Bool)
(declare-fun complex_product () Bool)
(declare-fun solicited () Bool)
(assert
 (let (($x90 (not (and streamlined (not explanation_requested)))))
(let (($x15 (not (and (not solicited) (not complex_product)))))
(let (($x57 (ite $x15 $x90 false)))
(let (($x91 (or solicited complex_product)))
(let (($x66 (and $x91 (or (not streamlined) explanation_requested))))
(or (not true) (and (distinct $x66 $x57) true))))))))
(check-sat)
