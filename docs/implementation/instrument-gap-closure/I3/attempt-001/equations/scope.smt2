; benchmark generated from python API
(set-info :status unknown)
(declare-fun qualifying_contingent_loss_absorption () Bool)
(declare-fun plain_debt_or_deposit () Bool)
(declare-fun debt_legal_form () Bool)
(declare-fun qualifying_wrapper () Bool)
(assert
 (let (($x23 (ite debt_legal_form (ite plain_debt_or_deposit false qualifying_contingent_loss_absorption) false)))
(let (($x52 (ite qualifying_wrapper true $x23)))
(let (($x42 (not plain_debt_or_deposit)))
(let (($x71 (or qualifying_wrapper (and debt_legal_form qualifying_contingent_loss_absorption $x42))))
(and (distinct $x71 $x52) true))))))
(check-sat)
