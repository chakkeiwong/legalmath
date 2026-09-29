; benchmark generated from python API
(set-info :status unknown)
(declare-fun contractual_write_down () Bool)
(declare-fun contingent_conversion () Bool)
(declare-fun subordinated () Bool)
(declare-fun perpetual () Bool)
(declare-fun bond () Bool)
(assert
 (let ((?x16 (+ (ite perpetual 1 0) (ite subordinated 1 0) (ite contingent_conversion 1 0) (ite contractual_write_down 1 0))))
(let (($x18 (and bond (>= ?x16 1))))
(let (($x20 (or perpetual subordinated contingent_conversion contractual_write_down)))
(let (($x21 (and bond $x20)))
(or (not true) (and (distinct $x21 $x18) true)))))))
(check-sat)
