; benchmark generated from python API
(set-info :status unknown)
(declare-fun days_elapsed () Int)
(assert
 (>= days_elapsed 0))
(assert
 (let (($x13 (not (or (< days_elapsed 30) (> days_elapsed 60)))))
(let (($x15 (<= 30 days_elapsed)))
(let (($x16 (and $x15 (>= 60 days_elapsed))))
(and (distinct $x16 $x13) true)))))
(check-sat)
