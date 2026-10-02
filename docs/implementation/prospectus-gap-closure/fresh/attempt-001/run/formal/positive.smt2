; benchmark generated from python API
(set-info :status unknown)
(declare-fun mandatory_common_conversion () Bool)
(declare-fun principal_write_down () Bool)
(declare-fun debt () Bool)
(assert
 (let ((?x13 (+ (ite principal_write_down 1 0) (ite mandatory_common_conversion 1 0))))
(let (($x15 (and debt (> ?x13 0))))
(let (($x21 (and debt (or principal_write_down mandatory_common_conversion))))
(and (distinct $x21 $x15) true)))))
(check-sat)
