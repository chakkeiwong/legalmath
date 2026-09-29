; benchmark generated from python API
(set-info :status unknown)
(declare-fun streamlined () Bool)
(declare-fun solicited () Bool)
(declare-fun complex_product () Bool)
(assert
 (let (($x102 (not solicited)))
(let (($x108 (and complex_product $x102 streamlined)))
(or (not true) (and (distinct $x108 $x108) true)))))
(check-sat)
