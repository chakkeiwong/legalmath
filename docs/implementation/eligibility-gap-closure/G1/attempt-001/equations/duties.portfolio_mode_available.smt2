; benchmark generated from python API
(set-info :status unknown)
(declare-fun in_scope_product () Bool)
(declare-fun registered_institution () Bool)
(declare-fun faq9_exception () Bool)
(declare-fun discretionary_portfolio_management () Bool)
(assert
 (let (($x63 (ite faq9_exception false (ite registered_institution in_scope_product false))))
(let (($x80 (ite discretionary_portfolio_management $x63 false)))
(let (($x7 (not faq9_exception)))
(let (($x20 (and registered_institution in_scope_product $x7 discretionary_portfolio_management)))
(and (distinct $x20 $x80) true))))))
(check-sat)
