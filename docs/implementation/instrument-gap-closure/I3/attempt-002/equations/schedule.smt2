; benchmark generated from python API
(set-info :status unknown)
(declare-fun notice_date () Int)
(declare-fun conversion_date () Int)
(declare-fun deadline () Int)
(assert
 (>= notice_date 0))
(assert
 (>= conversion_date 0))
(assert
 (>= deadline 0))
(assert
 (let (($x51 (<= conversion_date notice_date)))
(let (($x20 (not (or $x51 (> conversion_date deadline)))))
(let (($x25 (and (> conversion_date notice_date) (>= deadline conversion_date))))
(and (distinct $x25 $x20) true)))))
(check-sat)
