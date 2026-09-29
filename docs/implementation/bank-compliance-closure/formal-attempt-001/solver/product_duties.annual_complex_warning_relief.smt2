; benchmark generated from python API
(set-info :status unknown)
(declare-fun streamlined () Bool)
(declare-fun solicited () Bool)
(declare-fun complex_product () Bool)
(assert
 (let (($x107 (not solicited)))
(let (($x93 (and complex_product $x107 streamlined)))
(or (not true) (and (distinct $x93 $x93) true)))))
(check-sat)
