; benchmark generated from python API
(set-info :status unknown)
(declare-fun mandatory_common_conversion () Bool)
(declare-fun principal_write_down () Bool)
(declare-fun coverage_complete () Bool)
(declare-fun debt () Bool)
(assert
 (let (($x17 (not coverage_complete)))
(let (($x16 (not debt)))
(let (($x19 (not (or $x16 $x17 principal_write_down mandatory_common_conversion))))
(let (($x21 (and debt coverage_complete (not principal_write_down) (not mandatory_common_conversion))))
(and (distinct $x21 $x19) true))))))
(check-sat)
