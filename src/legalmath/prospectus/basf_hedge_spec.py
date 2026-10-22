"""Exposed, original-image-supplied Note26.5 structure; not table discovery."""

def seq(a,b):
    return list(range(a,b+1))


PROSE = {
    'note_title': (279,[3,4],'Note26.5 derivative financial instruments and hedging relationships'),
    'use_heading': (279,[5],'The use of derivative financial instruments'),
    'use': (279,seq(6,20),'Currency,interest and commodity risks,underlying/planned transactions,positive-value counterparty credit risk and credit limits'),
    'central_controls': (279,seq(21,25),'Centralized risk positions at BASF SE and certain group companies;internal guidelines and controls'),
    'valuation': (279,[26,27,29,30],'Valuation models use observable inputs if available;some commodity derivatives use market prices directly'),
    'hedge_heading': (279,[66],'Hedge accounting'),
    'naphtha': (279,seq(67,77),'Naphtha options;exercise prices in dollars per metric ton and following-year cash-flow/profit recognition'),
    'gas': (279,seq(78,88),'Gas options;exercise prices in euros per MWh or dollars per mmBtu and2023/2024 recognition'),
    'commodity_time_value': (279,seq(89,96)+[98,99,100],'Option time value recognized separately in equity,initial asset-cost derecognition and later profit recognition on consumption;49/24million asset-cost derecognition'),
    'sales_currency': (280,seq(2,19),'Future-dollar sales options;exchange rates,below-total sales volume,subsequent recognition and option-time-value equity/earnings movements'),
    'private_placement': (280,seq(20,26),'2013 fixed-rate1.25billion-dollar private placement converted to euros using swaps;4.13percent interest and1.3589dollars per euro'),
    'commercial_paper': (280,seq(27,38),'Dollar commercial-paper forwards;1.0683dollars per euro and separate equity/earnings hedge-cost movements;reported no ineffectiveness'),
    'table_introduction': (280,seq(39,41),'The following yearly tables separate balance sheet,cash-flow reserve,nominal value and ineffectiveness effects'),
    'closing_rule': (282,seq(3,9),'Forecast transactions considered highly probable in2022/2021;commodity reserves derecognized against acquired assets,with no immediate reclassification to profit or loss'),
}

METADATA={279:[0,1,2],280:[0,1,42],281:[0,1,2],282:[0,1,2]}
TYPOGRAPHIC={279:[28,97]}

FAIR_ROWS=[
    ('fx_forwards',[35],[[36],[37]],None),
    ('fx_options',[38],[[39],[40]],None),
    ('fx_total',[41],[[42],[43]],None),
    ('fx_designated',[44],[[47],[48]],'fx_total'),
    ('combined_swaps',[45],[[49],[50]],None),
    ('combined_designated',[46],[[51],[52]],'combined_swaps'),
    ('interest_total',[53],[[54],[55]],None),
    ('commodity_total',[56],[[57],[58]],None),
    ('commodity_designated',[63],[[59],[60]],'commodity_total'),
    ('total',[64],[[61],[62]],None),
]
FAIR_VALUES=[['165','21'],['19','1'],['184','22'],['16','0'],['265','102'],['256','179'],
             ['265','102'],['511','324'],['45','107 a'],['960','447']]
COLUMNS=['assets','liabilities','balance_item','nominal','reserve','oci_change','reclassified',
         'reclassification_item','instrument_change','hedged_change','ineffectiveness','income_item']
TEXT_COLUMNS={'balance_item','reclassification_item','income_item'}
HEADERS={
    '2022':[[32,33],[34,35],[110],[9,10],seq(11,15),seq(16,20),seq(21,25),seq(26,31),[111,112],[114],[115],[117,118]],
    '2021':[[149,150],[151,152],[212],[126,127],seq(128,132),seq(133,137),seq(138,142),seq(143,148),[214,215],[217],[218],[220,221]],
}
SHARED={'2022':116,'2021':219}
GROUP_HEADERS={'2022':[[5],[8],[6,7],[113]],'2021':[[122],[125],[123,124],[216]]}
HEADER_MEMBERS=[['assets','liabilities','balance_item'],['reserve','oci_change','reclassified'],
                ['instrument_change','hedged_change'],['ineffectiveness','income_item']]
EFFECT_ROWS={
    '2022':[
        ('currency',[36],[[37],[38],[39,40,41],[42],[43],[44],[45],[46,47,48],[49],[50],[51],[52]]),
        ('interest',[53],[[54],[55],[56],[57],[58],[59],[60],[61,62,63],[64],[65],[66],[67]]),
        ('combined',[68,69],[[70],[71],[72,73],[74],[75],[76],[77],[78,79],[80],[81],[82],[83]]),
        ('commodity',[84],[[85],[86],[87,88],[89],[90],[91],[92],[93,94,95],[96],[97],[98],[99]]),
        ('total',[100],[[101],[102],[],[103],[104],[105],[106],[],[107],[108],[109],[]]),
    ],
    '2021':[
        ('currency',[211],[[153],[154],[155,156,157],[158],[159],[160],[161],[162,163,164],[165],[166],[167],[168]]),
        ('combined',[169,170],[[171],[172],[173,174],[175],[176],[177],[178],[179,180],[181],[182],[183],[184]]),
        ('commodity',[185],[[186],[187],[188,189,190,191],[192],[193],[194],[195],[196],[197],[198],[199],[200]]),
        ('total',[201],[[202],[203],[],[204],[205],[206],[207],[],[208],[209],[210],[]]),
    ],
}
# Empty string marks an inspected unprinted grid position, not a source quote.
EFFECT_VALUES={
    '2022':[
        ['17','1','Other receivables and miscellaneous assets / other liabilities','1,215','11','304','–294','Other operating income','10','10','–','n/a'],
        ['–','–','n/a','–','–','–15','15','Other operating income','–','–','–','n/a'],
        ['256','–','Other receivables and miscellaneous assets','920','2','76','–68','Other financial income','256','259','–','n/a'],
        ['45','–','Other receivables and miscellaneous assets','296','4','181','–111 a','Other operating income','4','4','–','n/a'],
        ['318','1','','2,431','17','546','–458','','270','273','–',''],
    ],
    '2021':[
        ['1','1','Other receivables and miscellaneous assets / other liabilities','508','0','83','–125','Other operating income','0','0','–','n/a'],
        ['179','–','Other receivables and miscellaneous assets','920','–5','89','–85','Other financial income','179','187','–','n/a'],
        ['107','0','Other receivables and miscellaneous assets / assets of disposal groups / other liabilities','488','100','154','– a','n/a','100','100','–','n/a'],
        ['287','1','','1,916','95','326','–210','','279','287','–',''],
    ],
}
FOOTNOTES={
    'fair':'a Of which €71 million reported in the balance sheet under assets of disposal groups',
    '2022':'a €166 million was derecognized from the cash flow hedge reserve, reducing the cost of inventories, and recognized in profit or loss upon consumption.',
    '2021':'a €59 million was derecognized from the cash flow hedge reserve, reducing the cost of inventories, and recognized in profit or loss upon consumption.',
}
