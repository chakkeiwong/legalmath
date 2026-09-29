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
 (let (($x21 (and designated (not adding_funds))))
(let (($x64 (ite (> gross maximum) $x21 true)))
(let (($x55 (or (>= maximum gross) $x21)))
(or (not true) (and (distinct $x55 $x64) true))))))
(check-sat)
