; benchmark generated from python API
(set-info :status unknown)
(declare-fun portfolio () Int)
(declare-fun net_assets () Int)
(assert
 (>= portfolio 0))
(assert
 (>= net_assets 0))
(assert
 (let (($x16 (not (and (< portfolio 4000000000) (< net_assets 8000000000)))))
(let (($x34 (<= 8000000000 net_assets)))
(let (($x32 (<= 4000000000 portfolio)))
(let (($x65 (or $x32 $x34)))
(or (not true) (and (distinct $x65 $x16) true)))))))
(check-sat)
