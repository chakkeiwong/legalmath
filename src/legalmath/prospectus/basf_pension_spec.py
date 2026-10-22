"""Exposed supplied associations for original BASF2022 Note22; not discovery."""

COUNTS = {261: 97, 262: 143, 263: 98, 264: 165, 265: 150, 266: 100}
EXCLUDED = [4, 5, 7, *range(54, 100)]
TYPOGRAPHIC = {261: [30, 76], 262: [131, 135, 140]}
SHARED = {51: "The strategy", 56: "In some countries", 57: "employer has", 61: "minimum guarantee"}


def seq(first, last):
    return list(range(first, last + 1))


# page, exact original unit IDs/character associations, column, supplied meaning.
PROSE = {
    "heading": (261, [3, 4], "left", "Note22: provisions for pensions and similar obligations; accounting policies."),
    "benefit_policy": (261, seq(5, 13), "left", "Benefits depend on service, contributions or pay and local labor, tax and social-security law; new service has predominantly defined contribution arrangements."),
    "governance": (261, seq(14, 18), "left", "The Group Pension Committee monitors funding and plan-asset risks under documented responsibilities."),
    "policy_scope": (261, [19, 20], "left", "The following accounting policies concern defined benefit pension obligations."),
    "valuation": (261, [*seq(46, 50), "51:left", 52], "left", "Projected unit credit valuation uses compensation, pension, inflation, turnover and longevity assumptions, discounted using high-quality corporate fixed-rate bond yields."),
    "similar_obligations": (261, [55, "56:left", "57:left", 58], "left", "Similar obligations include North American retired-staff healthcare and life-insurance commitments."),
    "actuarial_reports": (261, ["61:left", 62], "left", "Actuarial reports determine the pension provisions."),
    "oci_rule": (261, seq(21, 25), "middle", "Actuarial assumption changes, actual-versus-standardized asset returns and asset-ceiling effects are recognized directly in equity as other comprehensive income."),
    "regulatory_environment": (261, [26, 27, 28, 29, *seq(31, 38)], "middle", "Government supervision includes minimum funding calculated with assumptions different from IAS19 and asset-allocation restrictions; compliance may change contributions, financing and employer obligations."),
    "risks": (261, seq(39, 45), "middle", "Demographic, legal and economic risks include inflation adjustments in Germany and the United Kingdom and discount-rate changes in defined benefit obligations."),
    "funding_strategy": (261, ["51:right", 53, 54], "middle", "Funding strategy takes country-specific supervisory and tax rules into account."),
    "subsidiary_liability": (261, ["56:right", "57:right", 59, 60, "61:right", 63, 64, 65, 66], "middle-to-right", "Employers may owe subsidiary support for minimum guarantees. Defined contribution treatment is conditional on recourse being unlikely given plan structure, execution and fund assets."),
    "country_scope": (261, seq(67, 72), "right", "Descriptions are typical country plans; acquisition-related variations exist and are described as immaterial to those descriptions."),
    "germany": (261, [73, 74, 75, *seq(77, 96)], "right", "BASF SE ensures financing of Pensionskasse promises; member companies bear adjustments the fund cannot bear under supervisory rules. The source distinguishes new-hire dates, contribution plans, trusts, provisions and cash-balance/securities-based benefits."),
    "us": (262, [3, 4, 5, *seq(9, 12), *seq(18, 29)], "left", "U.S. defined benefit accrual was frozen in2010 without cost-of-living entitlement; ERISA minimum funding depends on actuarial valuations, while some unfunded plans are outside ERISA. Healthcare/life plans closed to entrants in2007 and benefits were frozen."),
    "switzerland": (262, seq(30, 42), "left", "Swiss plans are accounted for as defined benefit because statutory BVG minimum pensions are included; benefits vest immediately and employers must contribute to fund statutory minima under joint board governance."),
    "uk": (262, [6, 7, 8, *seq(13, 17), *seq(43, 50)], "middle", "U.K. legacy defined benefit accrual is closed but pre-retirement cost-of-living adjustments are legally required. Trustee governance and local social/labor/funding rules apply, with technical valuations every three years."),
    "other_countries": (262, seq(51, 54), "middle", "Other-country defined benefits use provisions in some cases and mainly external insurers or pension funds."),
    "assumptions_intro": (262, seq(55, 57), "right", "Key actuarial assumptions for defined benefit obligations follow."),
    "assumption_timing": (262, seq(126, 128), "right", "December31 obligation assumptions determine the following year's pension expenses."),
    "discount_method": (262, [129, 130, 132, 133, 134, *seq(136, 139), 141, 142], "right", "The former uniform approach used qualifying corporate-bond yields; material Germany/U.S./Switzerland/U.K. obligations moved to WTW RATE:Link at December31,2022, with effects continued on263."),
    "discount_change": (263, [4, 3, *seq(5, 8)], "left", "The2022 model change increased group obligations by664million euros, mainly Germany; the previous approach would have raised Germany's discount rate by30basis points. The separated initial letter remains in original source order metadata."),
    "inflation": (263, seq(22, 25), "left", "Most domestic obligations require regular inflation-related adjustments; the report applies10percent in2022 and raises the long-term assumption from1.60to2.20percent."),
    "mortality_updates": (263, seq(27, 32), "left", "Valuation generally uses the latest mortality tables, with the stated2019German,2021Swiss and2022U.S. updates."),
    "sensitivity_intro": (263, [9, 12, 13], "middle", "The table gives alternative defined-benefit valuations after changing material assumptions."),
    "sensitivity_limit": (263, seq(64, 69), "middle", "Linear extrapolation of the sensitivity amounts to other changes and addition of combined changes in individual assumptions are not possible."),
    "expense_heading": (263, [10, 11], "right", "Explanation of income-statement and balance-sheet amounts."),
    "net_interest": (263, seq(88, 94), "right", "Net interest uses beginning-of-year liability, obligation interest, standardized asset return and asset-ceiling interest, accounting for expected contributions and benefits."),
    "interest_timing": (263, seq(95, 97), "right", "The respective year's net interest is based on the discount rate and obligation at the beginning of that year."),
    "plan_adjustments": (264, seq(123, 127), "left", "The2022 Netherlands final-salary conversion concerns future service;2021Canada benefits and corresponding assets transferred to an insurer."),
    "duration": (264, seq(128, 130), "left", "Weighted average obligation duration was13.2years at December31,2022 versus16.6previously."),
    "standardized_return": (264, seq(149, 153), "middle", "Standardized return uses beginning-year assets and the beginning-year obligation discount rate, adjusted for benefit and contribution payments."),
    "pigments": (264, seq(154, 157), "middle", "The previous-year acquisition/divestiture effects include remaining pigments-business obligations, assets and an associated deposit."),
    "contribution_forecast": (264, seq(158, 161), "middle", "Funding requirements are monitored;2023company contributions were expected to be around140million euros, not recorded as an actual payment."),
    "allocation_policy": (265, [75, *seq(113, 121)], "left", "Asset-liability studies, obligation development, asset risks, investment rules and market assessments guide a globally diversified allocation."),
    "ldi": (265, seq(98, 100), "left", "Some plans, especially U.K./U.S., use liability-driven interest-rate and inflation hedges."),
    "asset_classes": (265, [*seq(124, 136), 122, 123], "middle-to-right", "The source distinguishes government and corporate debt, limited emerging/high-yield exposure, monitored credit risks and private/infrastructure/absolute-return/senior-secured alternatives."),
    "illiquidity": (265, seq(101, 110), "right", "Most equities have active prices;138/188million euros of privately placed debt lack an active market, and3731million especially in alternatives/real estate lacks a fungible price. Yield premiums do not establish liquidity."),
    "related_assets": (265, seq(137, 141), "right", "BASF-issued plan securities are printed zero in both years; pension-fund properties rented to BASF have115/112million euro values."),
    "fund_loan": (265, seq(142, 149), "right", "To support regulatory solvency/risk capacity, the initial fund loan was220million nominal in2021,80million used to repay participation capital, and320million nominal in2022."),
    "funding_intro": (266, [3], "left", "The following table reports current funding at December31."),
    "asset_ceiling": (266, seq(41, 47), "left", "A431million euro Swiss asset ceiling arose in2022 under the report's IAS19.64 explanation. A surplus is tested for impairment; absent economic benefit such as refunds or reduced contributions, a ceiling is reported."),
    "dc_contributions": (266, seq(48, 51), "left", "Defined-contribution expenses in operations are344million euros in2022 and308million in2021."),
    "government_contributions": (266, [52, 53], "left", "Government-plan contributions are601million euros in2022 and578million in2021, a separate scope from company defined-contribution expenses."),
}


def table(page, title, unit, kind, columns, rows, groups=(), scope=""):
    return dict(page=page, title=title, unit=unit, kind=kind, columns=columns,
                rows=rows, groups=list(groups), scope=scope)


def row(name, label, cells, values, parent=None):
    return dict(id=name, label=label, cells=cells, values=values, parent=parent)


def cols(ids, keys=None):
    return [(k, [n]) for k, n in zip(keys or ["2022", "2021"], ids)]


COUNTRY_COLUMNS = [c + ":" + y for c in ("germany", "us", "switzerland", "uk") for y in ("2022", "2021")]
TABLES = {
    "obligation_assumptions": table(262, [58, 59], [], "supplied_rate_percent",
        cols(seq(65, 72), COUNTRY_COLUMNS), [
            row("discount", [73], [[n] for n in seq(74, 81)], ["3.70", "1.10", "5.30", "2.70", "2.20", "0.40", "4.80", "2.00"]),
            row("pension_increase", [82, 83], [[n] for n in seq(84, 91)], ["2.20", "1.60", "–", "–", "–", "–", "3.40", "3.50"])],
        groups=[([60], COUNTRY_COLUMNS[:2]), ([61], COUNTRY_COLUMNS[2:4]), ([62], COUNTRY_COLUMNS[4:6]), ([63,64], COUNTRY_COLUMNS[6:])],
        scope="December31 obligation valuation; conventional percent units supplied, not printed"),
    "expense_assumptions": table(262, [92, 93], [], "supplied_rate_percent",
        cols(seq(99, 106), COUNTRY_COLUMNS), [
            row("discount", [107], [[n] for n in seq(108, 115)], ["1.10", "0.70", "2.70", "2.30", "0.40", "0.10", "2.00", "1.50"]),
            row("pension_increase", [116,117], [[n] for n in seq(118,125)], ["1.60", "1.50", "–", "–", "–", "–", "3.50", "3.10"])],
        groups=[([94], COUNTRY_COLUMNS[:2]), ([95], COUNTRY_COLUMNS[2:4]), ([96], COUNTRY_COLUMNS[4:6]), ([97,98], COUNTRY_COLUMNS[6:])],
        scope="Expenses in the respective business year; conventional percent units supplied, not printed"),
    "mortality": table(263, [35], [], "text", [("reference", [])], [
        row("germany", [36], [[37]], ["Heubeck Richttafeln 2018G (modified)"]),
        row("us", [38], [[39,40]], ["Pri-2012 base mortality tables with Scale MP-2021 projection"]),
        row("switzerland", [41], [[42,43]], ["BVG 2020 generational with CMI 2018 mortality improvement"]),
        row("uk", [44], [[45,46]], ["S2PxA (standard actuarial mortality tables for self-administered plans (SAPS))"])],
        scope="Named actuarial mortality references at December31,2022"),
    "sensitivity": table(263, [21], [26], "million_eur",
        cols([52,53,54,55], ["increase:2022","increase:2021","decrease:2022","decrease:2021"]), [
            row("discount", [49], [[n] for n in seq(56,59)], ["–1,305","–2,115","1,477","2,420"]),
            row("pension_increase", [33,34], [[n] for n in seq(60,63)], ["985","1,533","–846","–1,267"])],
        groups=[([47,48],["increase:2022","increase:2021"]),([50,51],["decrease:2022","decrease:2021"])],
        scope="Alternative valuations for exactly plus/minus0.5percentage points; not additive or linearly scalable"),
    "expenses": table(263, [14], [15], "million_eur", cols([16,17]), [
        row("defined_benefit", [18], [[19],[20]], ["357","423"]),
        row("defined_contribution", [70], [[71],[72]], ["344","308"]),
        row("operating", [73,74], [[75],[76]], ["701","731"]),
        row("underfunded_interest", [77,78], [[79],[80]], ["102","85"]),
        row("overfunded_interest", [81], [[82],[83]], ["–21","–3"]),
        row("financial", [84,85], [[86],[87]], ["81","82"])], scope="Operating pension expenses and financial result shown separately"),
    "dbo": table(264, [3], [5], "million_eur", cols([7,8]), [
        row("opening",[17],[[9],[10]],["28,629","29,840"]),
        row("service",[11],[[12],[13]],["373","419"]),
        row("past_service",[14],[[15],[16]],["2","1"]),
        row("adjustments",[37],[[38],[39]],["–12","–21"]),
        row("interest",[63],[[44],[45]],["379","276"]),
        row("benefits",[50],[[51],[52]],["–1,126","–1,084"]),
        row("employee",[64],[[53],[54]],["37","37"]),
        row("actuarial",[57],[[55],[56]],["–6,800","–1,496"]),
        row("financial_assumptions",[58],[[88],[89]],["–7,712","–1,505"],"actuarial"),
        row("demographic_assumptions",[96],[[97],[98]],["–12","–117"],"actuarial"),
        row("experience",[105],[[106],[107]],["924","126"],"actuarial"),
        row("acquisitions",[113],[[111],[112]],["0","171"]),
        row("other",[114],[[115],[116]],["–4","–19"]),
        row("currency",[117],[[118],[119]],["192","505"]),
        row("closing",[122],[[120],[121]],["21,670","28,629"])], scope="Positive defined benefit obligation and its changes"),
    "assets": table(264, [4], [6], "million_eur", cols([23,24]), [
        row("opening",[18],[[25],[26]],["23,130","21,400"]),
        row("standard_return",[19],[[28],[29]],["300","194"]),
        row("return_deviation",[20],[[62],[33]],["–2,641","1,935"]),
        row("employer",[40],[[41],[42]],["144","151"]),
        row("employee",[46],[[47],[48]],["37","37"]),
        row("benefits",[59],[[71],[72]],["–1,009","–952"]),
        row("acquisitions",[76],[[77],[78]],["–","216"]),
        row("adjustments",[82],[[83],[84]],["–","–21"]),
        row("other",[90],[[91],[92]],["–21","–264"]),
        row("currency",[99],[[100],[101]],["143","434"]),
        row("closing",[108],[[109],[110]],["20,083","23,130"])], scope="Gross plan-asset balances and movements before the separate asset ceiling"),
    "net": table(264, [21], [22], "million_eur", cols([65,60]), [
        row("opening",[27],[[66],[61]],["–5,499","–8,440"]),
        row("service",[30],[[31],[32]],["–373","–419"]),
        row("past_service",[34],[[35],[36]],["–2","–1"]),
        row("adjustments",[43],[[67],[68]],["12","0"]),
        row("interest",[49],[[69],[70]],["–379","–276"]),
        row("standard_return",[73],[[74],[75]],["300","194"]),
        row("return_deviation",[79],[[80],[81]],["–2,641","1,935"]),
        row("actuarial",[85],[[86],[87]],["6,800","1,496"]),
        row("unfunded_benefits",[93],[[94],[95]],["117","132"]),
        row("employer",[102],[[103],[104]],["144","151"]),
        row("acquisitions",[131],[[132],[133]],["0","45"]),
        row("other",[148],[[134],[135]],["–17","–245"]),
        row("currency",[136],[[137],[138]],["–49","–71"]),
        row("ceiling",[139],[[140],[141]],["–431","–"]),
        row("closing",[162],[[142],[143]],["–2,018","–5,499"]),
        row("benefit_assets",[163],[[144],[145]],["792","661"],"closing"),
        row("provisions",[164],[[146],[147]],["2,810","6,160"],"closing")], scope="Source's signed net liability; positive asset and provision subrows require assets minus provisions"),
}

REGIONAL_COLUMNS = [c+":"+y for c in ("dbo","assets","ceiling","net") for y in ("2022","2021")]
REGIONAL_VALUES = [
    ["15,219","20,400","14,108","15,498","–","–","–1,111","–4,902"],
    ["2,876","3,563","1,977","2,610","–","–","–899","–953"],
    ["1,561","1,812","2,007","2,212","–431","–","15","400"],
    ["1,260","1,967","1,368","2,178","–","–","108","211"],
    ["754","887","623","632","–","–","–131","–255"],
    ["21,670","28,629","20,083","23,130","–431","–","–2,018","–5,499"]]
TABLES["regional"] = table(265,[3],[4],"million_eur",cols(seq(9,16),REGIONAL_COLUMNS),
    [row(name,[start],[[n] for n in seq(start+1,start+8)],values)
     for name,start,values in zip(("germany","us","switzerland","uk","other","total"),
                                 (17,26,35,44,53,62),REGIONAL_VALUES)],
    groups=[([n],REGIONAL_COLUMNS[i*2:i*2+2]) for i,n in enumerate(seq(5,8))],
    scope="Country-specific December31 balances; dashes are not zero-valued ceiling facts")
TABLES["asset_structure"] = table(265,[111],[112],"percent",cols([71,72]),[
    row("equity",[76],[[73],[74]],["21","26"]),
    row("debt",[77],[[78],[79]],["42","45"]),
    row("government",[80],[[81],[82]],["16","18"],"debt"),
    row("other_debt",[83],[[84],[85]],["26","27"],"debt"),
    row("real_estate",[86],[[87],[88]],["7","6"]),
    row("alternative",[89],[[90],[91]],["29","21"]),
    row("cash",[92],[[93],[94]],["1","2"]),
    row("total",[97],[[95],[96]],["100","100"])],scope="Percentage allocation, not million-euro balances; debt subrows are included")
TABLES["funding"] = table(266,[6],[8],"million_eur",
    [("2022:dbo",[10,11,12]),("2022:assets",[18,19]),("2021:dbo",[20,21,22]),("2021:assets",[23,24])],[
    row("unfunded",[13],[[n] for n in seq(25,28)],["1,963","–","2,121","–"]),
    row("funded",[14],[[n] for n in seq(29,32)],["19,707","20,083","26,508","23,130"]),
    row("ceiling",[15],[[n] for n in seq(33,36)],["–","–431","–","–"]),
    row("total",[16],[[n] for n in seq(37,40)],["21,670","19,652","28,629","23,130"])],
    groups=[([9],["2022:dbo","2022:assets"]),([17],["2021:dbo","2021:assets"])],
    scope="Funding table: total assets include the asset-ceiling adjustment, unlike gross plan assets")
