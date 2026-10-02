; benchmark generated from python API
(set-info :status unknown)
(declare-fun paragraph_15_3b_complied () Bool)
(declare-fun paragraph_15_3a_complied () Bool)
(declare-fun corporate_pi () Bool)
(declare-fun institutional_pi () Bool)
(assert
 (let ((?x11 (+ (ite corporate_pi 1 0) (ite paragraph_15_3a_complied 1 0) (ite paragraph_15_3b_complied 1 0))))
(let (($x33 (= ?x11 3)))
(let (($x42 (ite institutional_pi true $x33)))
(let (($x75 (or institutional_pi (and corporate_pi paragraph_15_3a_complied paragraph_15_3b_complied))))
(and (distinct $x75 $x42) true))))))
(check-sat)
