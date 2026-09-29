; benchmark generated from python API
(set-info :status unknown)
(declare-fun portfolio () Int)
(declare-fun net_assets () Int)
(assert
 (>= portfolio 0))
(assert
 (>= net_assets 0))
(assert
 (let (($x58 (not (and (< portfolio 4000000000) (< net_assets 8000000000)))))
(or (not true) (and (distinct (or (<= 4000000000 portfolio) (<= 8000000000 net_assets)) $x58) true))))
(check-sat)
