; benchmark generated from python API
(set-info :status unknown)
(declare-fun gross () Int)
(declare-fun maximum () Int)
(declare-fun adding_funds () Bool)
(declare-fun designated () Bool)
(assert
 (>= gross 0))
(assert
 (>= maximum 0))
(assert
 (let (($x22 (and designated (not adding_funds))))
(let (($x42 (ite (> gross maximum) $x22 true)))
(or (not true) (and (distinct (or (>= maximum gross) $x22) $x42) true)))))
(check-sat)
