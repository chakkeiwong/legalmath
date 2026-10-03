; benchmark generated from python API
(set-info :status unknown)
(declare-fun paragraph_15_3b_complied () Bool)
(declare-fun paragraph_15_3a_complied () Bool)
(declare-fun corporate_pi () Bool)
(declare-fun institutional_pi () Bool)
(assert
 (let ((?x21 (ite paragraph_15_3b_complied 1 0)))
(let ((?x82 (ite paragraph_15_3a_complied 1 0)))
(let ((?x35 (ite corporate_pi 1 0)))
(let (($x33 (ite institutional_pi true (= (+ ?x35 ?x82 ?x21) 3))))
(let (($x78 (or institutional_pi (and corporate_pi paragraph_15_3a_complied paragraph_15_3b_complied))))
(and (distinct $x78 $x33) true)))))))
(check-sat)
