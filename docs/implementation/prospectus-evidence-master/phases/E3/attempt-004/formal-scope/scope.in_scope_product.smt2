; benchmark generated from python API
(set-info :status unknown)
(declare-fun qualifying_contingent_loss_absorption () Bool)
(declare-fun plain_debt_or_deposit () Bool)
(declare-fun debt_legal_form () Bool)
(declare-fun qualifying_wrapper () Bool)
(assert
 (let (($x71 (ite debt_legal_form (ite plain_debt_or_deposit false qualifying_contingent_loss_absorption) false)))
(let (($x54 (ite qualifying_wrapper true $x71)))
(let (($x7 (not plain_debt_or_deposit)))
(let (($x69 (or qualifying_wrapper (and debt_legal_form qualifying_contingent_loss_absorption $x7))))
(and (distinct $x69 $x54) true))))))
(check-sat)
