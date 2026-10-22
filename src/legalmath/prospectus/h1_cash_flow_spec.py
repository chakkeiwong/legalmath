"""Supplied image reading of the complete BES H1 2010 cash-flow page60.

Selectors refer to retained original OCR occurrences. Printed literals come
from the retained original page image; they do not replace its raw OCR.
"""
DOCUMENT = "bes-interim-h1-2010"
SOURCE = "b86022629850867b5bedbdaf701a451a816f46766d102fc487fc51da658b0ea7"
PAGE = 60
YEARS = ("2010", "2009")
CONTEXT = {
    "native-header": ["l0"], "native-footer": ["l1"],
    "decoration": ["ocr0", "ocr1", "ocr98", "ocr162"],
    "ocr-header": ["ocr2"], "ocr-footer": ["ocr163"],
    "entity": ["ocr3"], "title": ["ocr4"], "period": ["ocr5"],
    "unit": ["ocr6"], "notes-header": ["ocr7"],
    "year2010": ["ocr8"], "year2009": ["ocr9"],
    "operating-section": ["ocr10"], "operating-change-section": ["ocr34"],
    "investing-section": ["ocr69"], "financing-section": ["ocr100"],
    "cash-components-section": ["ocr142"], "notes-integral": ["ocr161"],
}


def row(key, section, label, cells, printed, notes=(), role="flow"):
    return {"id": key, "section": section, "role": role,
        "label": ["ocr" + str(n) for n in label], "notes": ["ocr" + str(n) for n in notes],
        "cells": [["ocr" + str(n)] for n in cells], "printed": list(printed)}


ROWS = [
    row("interest-received", "operating", [11], [12,13], ["1 786 242", "2 195 802"]),
    row("interest-paid", "operating", [14], [15,16], ["(1 316 102)", "(1 625 059)"]),
    row("fees-received", "operating", [17], [18,19], ["433 389", "381 651"]),
    row("fees-paid", "operating", [20], [21,22], ["(64 493)", "(54 209)"]),
    row("recoveries", "operating", [23], [24,25], ["9 817", "9 067"]),
    row("pension-contributions", "operating", [26], [27,28], ["(3 698)", "(420)"]),
    row("employees-suppliers", "operating", [29], [30,31], ["(391 277)", "(432 266)"]),
    row("operating-receipts-subtotal", "operating", [], [32,33], ["453 878", "474 566"], role="unlabelled-subtotal"),
    row("central-bank-deposits-change", "operating-changes", [35], [36,37], ["5 210 044", "(1 808 823)"]),
    row("fair-value-assets", "operating-changes", [38], [39,40], ["(1 351 083)", "(254 278)"]),
    row("loans-banks", "operating-changes", [41], [42,43], ["4 429 578", "(6 655 969)"]),
    row("deposits-banks-change", "operating-changes", [44], [45,46], ["196 182", "2 700 662"]),
    row("loans-customers", "operating-changes", [47], [48,49], ["(2 806 979)", "(503 594)"]),
    row("due-customers", "operating-changes", [50], [51,52], ["584 513", "(1 184 490)"]),
    row("risk-derivatives", "operating-changes", [53], [54,55], ["(77 424)", "(153 043)"]),
    row("other-operating", "operating-changes", [56], [57,58], ["(207 855)", "108 417"]),
    row("operating-before-tax", "operating", [59,60], [61,62], ["6 430 854", "(7 276 552)"], role="subtotal"),
    row("income-tax", "operating", [63], [64,65], ["(82 135)", "(107 058)"]),
    row("operating-net", "operating", [66], [67,68], ["6 348 719", "(7 383 610)"], role="subtotal"),
    row("subsidiaries-acquired", "investing", [70], [72,73], ["(105 353)", "(23 659)"], notes=[71]),
    row("subsidiaries-disposed", "investing", [74], [76,77], ["-", "4 981"], notes=[75]),
    row("dividends-received", "investing", [78], [79,80], ["70 685", "63 410"]),
    row("available-for-sale-acquired", "investing", [81], [82,83], ["(19 775 432)", "(15 672 240)"]),
    row("available-for-sale-disposed", "investing", [84], [85,86], ["17 984 688", "15 570 984"]),
    row("held-to-maturity", "investing", [87], [88,89], ["(188 667)", "(510 975)"]),
    row("tangible-intangible-acquired", "investing", [90], [91,92], ["(109 814)", "(56 935)"]),
    row("tangible-intangible-disposed", "investing", [93], [94,95], ["580", "8"]),
    row("investing-net", "investing", [96], [97,99], ["(2 123 313)", "(624 426)"], role="subtotal"),
    row("capital-increase", "financing", [101], [102,103], ["-", "1 189 072"]),
    row("bonds-issued", "financing", [104], [105,106], ["5 853 994", "10 832 867"]),
    row("bonds-repaid", "financing", [107], [108,109], ["(10 008 884)", "(5 044 201)"]),
    row("subordinated-issued", "financing", [110], [111,112], ["4 279", "20 000"]),
    row("subordinated-repaid", "financing", [113], [114,115], ["(340 449)", "-"]),
    row("treasury-stock", "financing", [116], [117,118], ["112", "4 023"]),
    row("ordinary-dividends", "financing", [119], [120,121], ["(163 178)", "(79 656)"]),
    row("preference-dividends", "financing", [122], [123,124], ["(33 480)", "(33 480)"]),
    row("financing-net", "financing", [125], ["126:left","126:right"], ["(4 687 606)", "6 888 625"], role="subtotal"),
    row("net-change", "cash-rollforward", [127], [128,129], ["(462 200)", "(1 119 411)"], role="subtotal"),
    row("opening-cash", "cash-rollforward", [130], [131,132], ["2 161 089", "1 923 762"], role="opening-balance"),
    row("exchange-effect", "cash-rollforward", [133], [134,135], ["148 154", "(9 745)"]),
    row("net-change-repeat", "cash-rollforward", [136], [137,138], ["(462 200)", "(1 119 411)"], role="repeated-flow"),
    row("closing-cash", "cash-rollforward", [139], [140,141], ["1 847 043", "794 606"], role="closing-balance"),
    row("cash", "cash-components", [143], [145,146], ["202 099", "156 943"], notes=[144], role="balance-component"),
    row("central-bank-deposits", "cash-components", [147], [149,150], ["1 740 902", "1 076 138"], notes=[148], role="balance-component"),
    row("mandatory-central-bank", "cash-components", [151], [152,153], ["(596 816)", "(1 012 416)"], role="balance-component"),
    row("bank-deposits", "cash-components", [154], [156,157], ["500 858", "573 941"], notes=[155], role="balance-component"),
    row("total-cash-components", "cash-components", [158], [159,160], ["1 847 043", "794 606"], role="subtotal"),
]

# These checks compare printed amounts. They are not accounting opinions.
CHECKS = [
    ("operating-receipts", "operating-receipts-subtotal", [r["id"] for r in ROWS[:7]]),
    ("operating-before-tax", "operating-before-tax", ["operating-receipts-subtotal"] + [r["id"] for r in ROWS[8:16]]),
    ("operating-after-tax", "operating-net", ["operating-before-tax", "income-tax"]),
    ("investing-components", "investing-net", [r["id"] for r in ROWS if r["section"] == "investing" and r["role"] == "flow"]),
    ("financing-components", "financing-net", [r["id"] for r in ROWS if r["section"] == "financing" and r["role"] == "flow"]),
    ("net-cash-change", "net-change", ["operating-net", "investing-net", "financing-net"]),
    ("repeated-net-change", "net-change-repeat", ["net-change"]),
    ("cash-rollforward", "closing-cash", ["opening-cash", "exchange-effect", "net-change-repeat"]),
    ("cash-components", "total-cash-components", ["cash", "central-bank-deposits", "mandatory-central-bank", "bank-deposits"]),
    ("closing-cash-versus-components", "closing-cash", ["total-cash-components"]),
]
