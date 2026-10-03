; benchmark generated from python API
(set-info :status unknown)
(declare-fun in_scope_product () Bool)
(declare-fun registered_institution () Bool)
(declare-fun faq9_exception () Bool)
(declare-fun discretionary_portfolio_management () Bool)
(assert
 (let (($x89 (ite faq9_exception false (ite registered_institution in_scope_product false))))
(let (($x13 (ite discretionary_portfolio_management $x89 false)))
(let (($x17 (not faq9_exception)))
(let (($x44 (and registered_institution in_scope_product $x17 discretionary_portfolio_management)))
(and (distinct $x44 $x13) true))))))
(check-sat)
