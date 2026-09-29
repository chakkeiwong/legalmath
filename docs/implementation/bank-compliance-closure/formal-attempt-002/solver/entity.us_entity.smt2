; benchmark generated from python API
(set-info :status unknown)
(declare-fun present_in_us () Bool)
(declare-fun organized_under_us_law () Bool)
(assert
 (let ((?x11 (+ (ite organized_under_us_law 1 0) (ite present_in_us 1 0))))
(let (($x12 (> ?x11 0)))
(let (($x13 (or organized_under_us_law present_in_us)))
(or (not true) (and (distinct $x13 $x12) true))))))
(check-sat)
