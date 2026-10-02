; benchmark generated from python API
(set-info :status unknown)
(declare-fun in_scope_product () Bool)
(declare-fun registered_institution () Bool)
(declare-fun faq9_exception () Bool)
(declare-fun bcd_exempt () Bool)
(assert
 (let (($x25 (ite faq9_exception false (ite registered_institution in_scope_product false))))
(let (($x68 (ite bcd_exempt false $x25)))
(let (($x15 (not bcd_exempt)))
(let (($x83 (not faq9_exception)))
(let (($x89 (and registered_institution in_scope_product $x83 $x15)))
(and (distinct $x89 $x68) true)))))))
(check-sat)
