"""Finite original-image reading of BES H1 sector and rating tables, pages162–163."""
DOCUMENT = "bes-interim-h1-2010"
SOURCE = "b86022629850867b5bedbdaf701a451a816f46766d102fc487fc51da658b0ea7"
DATES = ("2010-06-30", "2009-12-31")
SECTORS = [
    "Agriculture", "Mining", "Food, beverage na tobacco", "Textiles", "Shoes", "Wood and cork",
    "Priting and publishing", "Refining and oil", "Chemicals and rubber", "Non-metalic minerals",
    "Metalic products", "Production of machinery, equipment and electric", "Production of transport material",
    "Other transforming industries", "Electricity, gas and water", "Construction", "Wholesale and retail",
    "Tourism", "Transports and communications", "Financial activities", "Real estate activities",
    "Services provided to companies", "Public services", "Non-profit organisations", "Mortgage loans",
    "Consumers loans", "Other", "TOTAL",
]
COLUMNS = ("loans-gross", "loans-impairment", "trading-assets", "fair-value-assets", "risk-derivatives",
    "available-for-sale-gross", "available-for-sale-impairment", "held-to-maturity-gross",
    "held-to-maturity-impairment", "guarantees-issued")
GROUPS = [
    ("Loans and advances to customers", ["loans-gross", "loans-impairment"]),
    ("Financial assets held for trading", ["trading-assets"]),
    ("Other financial assets as at fair value through profit or loss", ["fair-value-assets"]),
    ("Derivatives for risk management purposes", ["risk-derivatives"]),
    ("Available-for-sale financial assets", ["available-for-sale-gross", "available-for-sale-impairment"]),
    ("Held-to-maturity investments", ["held-to-maturity-gross", "held-to-maturity-impairment"]),
    ("Financial guarantees issued", ["guarantees-issued"]),
]

# A comma separates columns. Spaces and parentheses retain the image reading.
SECTOR2010 = """553 182,(24 779),10 003,-,-,25 304,(2 887),-,-,35 961
708 395,(10 814),7 689,-,-,14 653,-,-,-,21 814
892 412,(15 934),16 496,2 416,-,44 397,(52),4 304,-,94 977
389 294,(60 658),4 546,-,-,31 731,(2 238),-,-,18 143
76 636,(3 878),1 142,-,-,1 070,(499),-,-,2 726
181 289,(22 607),2 002,-,-,-,-,-,-,5 169
329 222,(7 706),46 401,-,-,140 263,-,-,-,72 018
22 980,(344),373,211,-,-,-,-,-,58 192
644 587,(17 976),18 671,-,-,70 695,(11 052),13 062,-,81 481
507 181,(17 078),1 583,-,-,9 572,-,-,-,42 292
662 130,(28 510),2 734,-,-,8 059,-,-,-,91 906
313 917,(13 615),2 600,-,-,30 091,(596),14 687,-,237 822
135 216,(11 726),755,-,-,1 786,(31),-,-,89 886
490 661,(19 735),956,-,-,15 304,(14 250),-,-,33 063
1 607 740,(16 630),58 014,5 993,-,395 260,-,17 477,-,557 900
5 428 586,(214 096),195 856,-,-,50 720,(1 687),-,-,2 090 327
3 287 381,(182 844),23 620,430,-,300 028,(13 215),5 352,-,601 722
1 416 390,(34 081),13 598,-,-,8 889,(376),-,-,65 211
2 638 138,(75 938),276 167,197,-,700 683,(3),212 308,-,864 667
2 398 070,(93 664),1 479 860,1 508 313,532 552,2 533 341,(45 784),1 196 388,(40 615),283 868
6 036 982,(184 886),35 947,-,-,91 220,(1 815),-,-,564 321
4 687 363,(105 605),66 903,5,-,1 599 790,(29 576),-,-,1 437 907
1 050 647,(15 790),3 493 992,-,-,3 043 703,-,925 150,-,205 913
3 819 116,(114 448),196 183,93 701,-,1 125 190,(15 523),409 321,(21 033),505 377
11 738 626,(221 133),-,-,-,-,-,-,-,39
2 793 815,(164 394),-,-,-,-,-,-,-,114 685
545 162,(2 670),10 131,-,-,12 633,(4),21 050,-,1 869
53 355 118,(1 681 539),5 966 222,1 611 266,532 552,10 254 382,(139 588),2 819 099,(61 648),8 179 256"""
SECTOR2009 = """582 861,(20 320),3 182,-,-,16 638,(3 562),-,-,30 277
515 579,(6 068),7 311,-,-,6 006,-,-,-,24 469
890 181,(19 120),17 371,-,-,40 142,(64),4 302,-,106 435
382 478,(57 980),3 994,-,-,21 450,(2 453),-,-,23 872
100 154,(4 247),738,-,-,500,(616),-,-,3 312
178 899,(20 771),1 586,-,-,-,-,-,-,5 354
286 052,(6 469),6 428,-,-,125 731,-,-,-,39 842
40 677,(267),1 090,-,-,218,-,-,-,5 749
584 284,(19 597),14 948,-,-,56 555,(10 366),13 118,-,67 091
519 879,(17 103),1 247,-,-,5 014,-,-,-,51 438
623 148,(23 313),5 451,-,-,10 345,-,-,-,94 650
359 306,(33 996),2 454,1 994,-,7 844,(783),17 936,-,209 995
140 082,(4 410),1 627,-,-,2 373,(38),24 180,-,80 658
524 781,(20 836),973,-,-,15 057,(12 087),-,-,18 241
1 428 411,(11 469),30 861,3 714,-,395 640,-,17 443,-,429 729
5 142 994,(175 183),119 430,-,-,102 618,(2 253),-,-,1 804 897
3 251 094,(167 646),20 300,-,-,148 337,(13 474),5 333,-,573 865
1 315 727,(27 546),13 516,-,-,8 312,(463),-,-,72 520
2 355 878,(61 438),200 742,-,-,1 217 662,(4),143 083,-,632 175
2 223 376,(89 152),1 360 458,875 292,455 115,2 546 467,(48 291),1 296 763,(20 584),214 248
5 201 380,(176 493),36 698,-,-,309 760,(1 672),-,-,589 303
4 376 173,(90 197),52 482,9,-,1 052 914,(31 771),-,-,1 154 893
960 993,(11 041),2 402 121,-,-,2 105 458,-,583 578,-,97 342
4 035 966,(113 932),150 413,111 358,-,458 810,(9 986),448 725,(13 981),522 702
11 352 578,(212 533),-,-,-,-,-,-,-,39
2 817 309,(155 918),-,-,-,-,-,-,-,127 619
340 914,(5 262),4 063,9 934,-,15 639,(7),21 933,-,2 451
50 531 154,(1 552 307),4 459 484,1 002 301,455 115,8 669 490,(137 890),2 576 394,(34 565),6 983 166"""


def sector_rows(year):
    if year not in {"2010", "2009"}:
        raise ValueError("Original risk stock date required")
    literals = (SECTOR2010 if year == "2010" else SECTOR2009).splitlines()
    result = []
    for i, (name, text) in enumerate(zip(SECTORS, literals)):
        start = 43 + 11*i + (1 if i > 18 else 0) if year == "2010" else 388 + 11*i
        cell_ids = [[start + j + 1] for j in range(10)]
        if year == "2010" and i == 18:
            cell_ids = [[242],[243],[244],[245],[246],[247],[248,249],[250],[251],[252]]
        result.append({"id": "sector-" + str(i), "label": [start], "printed_label": name,
            "cells": cell_ids, "printed": text.split(","), "role": "total" if i == 27 else "sector"})
    return result


RATING_GROUPS = [
    ("large", "Large companies", [25], 0,5),
    ("medium", "Medium enterprises", [61], 5,14),
    ("small", "Small enterprises", [97], 14,20),
    ("mortgage", "Mortgage loans", [138], 20,28),
    ("private", "Private individuals", [186], 28,38),
]
RATING_COLUMNS = ("2010:amount", "2010:percent", "2009:amount", "2009:percent")
# Internal-scale source selector, printed scale, then four printed cells.
RATINGS = [
    (15,"[aaa;a-]","748,1.40%,1 424,2.82%"),
    (20,"[bbb+;-bbb-]","2 245,4.21%,1 710,3.38%"),
    (26,"[bb+;bb-]","5 974,11.20%,5 705,11.29%"),
    (31,"[b+;b-]","8 932,16.74%,8 573,16.97%"),
    (36,"ccc+","875,1.64%,859,1.70%"),
    (41,"8-9","307,0.58%,233,0.46%"),
    (46,"10-11","485,0.91%,410,0.81%"),
    (51,"12-13","758,1.42%,751,1.49%"),
    (56,"14-15","854,1.60%,823,1.63%"),
    (62,"16-17","850,1.59%,938,1.86%"),
    (67,"18-19","672,1.26%,628,1.24%"),
    (72,"20-21","743,1.39%,730,1.44%"),
    (77,"22-23","323,0.61%,351,0.69%"),
    (82,"24-25","684,1.28%,765,1.51%"),
    (87,"A","74,0.14%,180,0.36%"),
    (92,"B","591,1.11%,503,1.00%"),
    (98,"C","943,1.77%,930,1.84%"),
    (103,"D","457,0.86%,499,0.99%"),
    (108,"E","315,0.59%,318,0.63%"),
    (113,"F","398,0.75%,427,0.84%"),
    (118,"01","1 234,2.31%,1 161,2.30%"),
    (123,"02","2 924,5.48%,2 762,5.47%"),
    (128,"03","2 292,4.30%,2 110,4.18%"),
    (133,"04","1 329,2.49%,1 271,2.52%"),
    (139,"05","820,1.54%,807,1.60%"),
    (144,"06","609,1.14%,626,1.24%"),
    (149,"07","1 369,2.57%,1 452,2.87%"),
    (154,"08","146,0.27%,180,0.35%"),
    (159,"01","103,0.19%,95,0.19%"),
    (164,"02","127,0.24%,114,0.23%"),
    (169,"03","188,0.35%,184,0.36%"),
    (174,"04","389,0.73%,332,0.66%"),
    (181,"05","283,0.53%,310,0.61%"),
    (187,"06","187,0.34%,199,0.39%"),
    (192,"07","183,0.34%,158,0.31%"),
    (197,"08","133,0.24%,196,0.39%"),
    (202,"09","219,0.41%,310,0.61%"),
    (207,"10","15,0.03%,18,0.04%"),
    (212,"No internal rating/scoring loans","13 577,25.43%,11 489,22.73%"),
    (217,"TOTAL","53 355,100.00%,50 531,100.00%"),
]


def rating_rows():
    return [{"id": "rating-" + str(i), "group": next((key for key, _, _, start, end in RATING_GROUPS if start <= i < end), None),
        "label": [start], "printed_label": label, "cells": [[start+j+1] for j in range(4)],
        "printed": text.split(","), "role": "total" if i == 39 else "unrated" if i == 38 else "rated"}
        for i, (start, label, text) in enumerate(RATINGS)]


def ocr(first, last):
    return ["ocr" + str(i) for i in range(first, last + 1)]


CONTEXT = {
    "162-native-title": (162, ["l0"]),
    "162-native-scope": (162, ["l1", "l2"]),
    "162-native-footer": (162, ["l3", "l4"]),
    "162-decoration": (162, ocr(0, 2)),
    "162-duplicate-title": (162, ["ocr3"]),
    "162-duplicate-scope": (162, ocr(4, 5)),
    "162-footer": (162, ocr(696, 698)),
    "163-native-title": (163, ["l0"]),
    "163-native-scope": (163, ["l1"]),
    "163-native-footer": (163, ["l2", "l3"]),
    "163-decoration": (163, ocr(0, 1) + ocr(179, 180)),
    "163-duplicate-title": (163, ["ocr2"]),
    "163-duplicate-scope": (163, ["ocr3"]),
    "163-footer": (163, ocr(222, 224)),
}


def tables():
    result = []
    for year, date, first, last in (("2010", DATES[0], 6, 42), ("2009", DATES[1], 352, 387)):
        columns = [{"id": key, "date": date, "unit": "thousand EUR",
            "asset_category": next(label for label, keys in GROUPS if key in keys),
            "measure": "impairment" if key.endswith("impairment") else "gross amount" if key.endswith("gross") else "amount"}
            for key in COLUMNS]
        result.append({"id": "sectors-" + year, "page": 162, "kind": "sector-exposure", "dates": [date],
            "monetary_unit": "thousand EUR", "header": ocr(first, last), "columns": columns,
            "groups": [], "rows": [{**r, "group": None} for r in sector_rows(year)]})
    result.append({"id": "ratings", "page": 163, "kind": "rating-portfolio", "dates": list(DATES),
        "monetary_unit": "million EUR", "header": ocr(4, 14),
        "columns": [{"id": key, "date": DATES[0 if key.startswith("2010") else 1],
            "unit": "percent" if key.endswith("percent") else "million EUR",
            "asset_category": "Loan portfolio", "measure": "portfolio percentage" if key.endswith("percent") else "credit amount"}
            for key in RATING_COLUMNS],
        "groups": [{"id": key, "label": ids, "printed_label": label,
            "row_ids": ["rating-" + str(i) for i in range(first, last)]}
            for key, label, ids, first, last in RATING_GROUPS], "rows": rating_rows()})
    return result
