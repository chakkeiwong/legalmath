; benchmark generated from python API
(set-info :status unknown)
(declare-fun in_scope_product () Bool)
(declare-fun registered_institution () Bool)
(declare-fun faq9_exception () Bool)
(declare-fun discretionary_portfolio_management () Bool)
(assert
 (let (($x25 (ite faq9_exception false (ite registered_institution in_scope_product false))))
(let (($x76 (ite discretionary_portfolio_management $x25 false)))
(let (($x83 (not faq9_exception)))
(let (($x46 (and registered_institution in_scope_product $x83 discretionary_portfolio_management)))
(and (distinct $x46 $x76) true))))))
(check-sat)
