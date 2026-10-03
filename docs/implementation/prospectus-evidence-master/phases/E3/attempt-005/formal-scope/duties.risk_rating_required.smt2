; benchmark generated from python API
(set-info :status unknown)
(declare-fun in_scope_product () Bool)
(declare-fun registered_institution () Bool)
(declare-fun faq9_exception () Bool)
(declare-fun bcd_exempt () Bool)
(assert
 (let (($x89 (ite faq9_exception false (ite registered_institution in_scope_product false))))
(let (($x67 (ite bcd_exempt false $x89)))
(let (($x81 (not bcd_exempt)))
(let (($x18 (not faq9_exception)))
(let (($x9 (and registered_institution in_scope_product $x18 $x81)))
(and (distinct $x9 $x67) true)))))))
(check-sat)
