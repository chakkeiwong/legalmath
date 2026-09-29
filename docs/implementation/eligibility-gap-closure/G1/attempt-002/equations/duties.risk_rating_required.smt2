; benchmark generated from python API
(set-info :status unknown)
(declare-fun in_scope_product () Bool)
(declare-fun registered_institution () Bool)
(declare-fun faq9_exception () Bool)
(declare-fun bcd_exempt () Bool)
(assert
 (let (($x63 (ite faq9_exception false (ite registered_institution in_scope_product false))))
(let (($x67 (ite bcd_exempt false $x63)))
(let (($x6 (not bcd_exempt)))
(let (($x7 (not faq9_exception)))
(let (($x70 (and registered_institution in_scope_product $x7 $x6)))
(and (distinct $x70 $x67) true)))))))
(check-sat)
