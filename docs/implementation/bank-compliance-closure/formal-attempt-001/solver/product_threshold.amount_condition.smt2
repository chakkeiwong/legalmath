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
 (let (($x36 (and designated (not adding_funds))))
(let (($x21 (ite (> gross maximum) $x36 true)))
(let (($x62 (or (>= maximum gross) $x36)))
(or (not true) (and (distinct $x62 $x21) true))))))
(check-sat)
