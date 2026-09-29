; benchmark generated from python API
(set-info :status unknown)
(declare-fun covered_savings_association () Bool)
(declare-fun national_bank () Bool)
(assert
 (let (($x79 (and (not national_bank) (not covered_savings_association))))
(let (($x89 (not $x79)))
(let (($x97 (or national_bank covered_savings_association)))
(or (not true) (and (distinct $x97 $x89) true))))))
(check-sat)
