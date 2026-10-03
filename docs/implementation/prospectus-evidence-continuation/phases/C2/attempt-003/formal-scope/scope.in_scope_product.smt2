; benchmark generated from python API
(set-info :status unknown)
(declare-fun qualifying_contingent_loss_absorption () Bool)
(declare-fun plain_debt_or_deposit () Bool)
(declare-fun debt_legal_form () Bool)
(declare-fun qualifying_wrapper () Bool)
(assert
 (let (($x30 (ite debt_legal_form (ite plain_debt_or_deposit false qualifying_contingent_loss_absorption) false)))
(let (($x24 (ite qualifying_wrapper true $x30)))
(let (($x16 (not plain_debt_or_deposit)))
(let (($x50 (or qualifying_wrapper (and debt_legal_form qualifying_contingent_loss_absorption $x16))))
(and (distinct $x50 $x24) true))))))
(check-sat)
