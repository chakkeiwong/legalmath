; benchmark generated from python API
(set-info :status unknown)
(declare-fun streamlined () Bool)
(declare-fun solicited () Bool)
(declare-fun complex_product () Bool)
(assert
 (let (($x59 (not solicited)))
(let (($x44 (and complex_product $x59 streamlined)))
(or (not true) (and (distinct $x44 $x44) true)))))
(check-sat)
