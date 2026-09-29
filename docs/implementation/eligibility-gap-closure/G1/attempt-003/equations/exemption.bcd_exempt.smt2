; benchmark generated from python API
(set-info :status unknown)
(declare-fun paragraph_15_3b_complied () Bool)
(declare-fun paragraph_15_3a_complied () Bool)
(declare-fun corporate_pi () Bool)
(declare-fun institutional_pi () Bool)
(assert
 (let ((?x22 (ite paragraph_15_3b_complied 1 0)))
(let ((?x68 (ite paragraph_15_3a_complied 1 0)))
(let ((?x26 (ite corporate_pi 1 0)))
(let (($x85 (ite institutional_pi true (= (+ ?x26 ?x68 ?x22) 3))))
(let (($x65 (or institutional_pi (and corporate_pi paragraph_15_3a_complied paragraph_15_3b_complied))))
(and (distinct $x65 $x85) true)))))))
(check-sat)
