; benchmark generated from python API
(set-info :status unknown)
(declare-fun attempted_cmic_prohibited_transaction () Bool)
(declare-fun us_financial_institution () Bool)
(assert
 (let (($x80 (ite us_financial_institution attempted_cmic_prohibited_transaction false)))
(let (($x109 (and us_financial_institution attempted_cmic_prohibited_transaction)))
(or (not true) (and (distinct $x109 $x80) true)))))
(check-sat)
