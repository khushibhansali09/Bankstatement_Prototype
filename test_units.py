"""Unit tests for the pieces most likely to break on a new bank format.

Run with:  python -m pytest -q      (or: python run_tests.py)
"""

from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bsp.classify import taxonomy
from bsp.classify.naive_bayes import NaiveBayesClassifier, featurise
from bsp.classify.rules import RuleEngine, load_rules
from bsp.extract import layout
from bsp.extract.patterns import (
    find_amounts, infer_day_first, parse_amount, parse_date, detect_channel,
    looks_like_money,
)
from bsp.models import Transaction
from bsp.normalize import extract_counterparty, normalise_text
from bsp.validate import check_balances, find_duplicates


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------

def test_date_formats():
    assert parse_date("01/09/2025") == date(2025, 9, 1)
    assert parse_date("01-09-25") == date(2025, 9, 1)
    assert parse_date("01.09.2025") == date(2025, 9, 1)
    assert parse_date("01-Sep-2025") == date(2025, 9, 1)
    assert parse_date("1 September 2025") == date(2025, 9, 1)
    assert parse_date("2025-09-01") == date(2025, 9, 1)
    assert parse_date("Sep 01, 2025") == date(2025, 9, 1)


def test_date_day_first_vs_month_first():
    assert parse_date("03/04/2025", day_first=True) == date(2025, 4, 3)
    assert parse_date("03/04/2025", day_first=False) == date(2025, 3, 4)
    # A day above 12 settles it regardless of the flag.
    assert parse_date("25/04/2025", day_first=False) == date(2025, 4, 25)


def test_infer_day_first_from_whole_file():
    assert infer_day_first(["25/04/2025 payment", "03/04/2025 payment"]) is True
    assert infer_day_first(["04/25/2025 payment", "04/03/2025 payment"]) is False


def test_rubbish_dates_return_none():
    assert parse_date("") is None
    assert parse_date("no date here") is None
    assert parse_date("32/13/2025") is None


# ---------------------------------------------------------------------------
# Amounts
# ---------------------------------------------------------------------------

def test_amount_formats():
    assert parse_amount("1,234.56") == Decimal("1234.56")
    assert parse_amount("1,23,456.78") == Decimal("123456.78")       # Indian grouping
    assert parse_amount("1234567.89") == Decimal("1234567.89")
    assert parse_amount("Rs. 5,000.00") == Decimal("5000.00")
    assert parse_amount("\u20b9 5,000.00") == Decimal("5000.00")


def test_amount_signs_and_markers():
    assert parse_amount("(5,000.00)") == Decimal("-5000.00")
    assert parse_amount("-5,000.00") == Decimal("-5000.00")
    assert parse_amount("5,000.00 Dr") == Decimal("-5000.00")
    assert parse_amount("5,000.00 Cr") == Decimal("5000.00")


def test_long_integers_are_not_money():
    assert looks_like_money("182736451") is False
    assert looks_like_money("1,234.56") is True
    found = find_amounts("UPI/428715903214/PAYMENT 1,234.56")
    assert Decimal("1234.56") in [value for value, _m, _s, _e in found]


def test_reference_numbers_are_skipped():
    found = find_amounts("REF NO 90812 AMOUNT 1,500.00")
    values = [value for value, _m, _s, _e in found]
    assert Decimal("1500.00") in values


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

def test_normalise_strips_the_noise():
    raw = "UPI/528412345678/SWIGGY LIMITED/HDFC0000123/Pay to Swiggy"
    out = normalise_text(raw)
    assert "528412345678" not in out
    assert "hdfc0000123" not in out
    assert "swiggy" in out


def test_normalise_expands_abbreviations():
    assert "cash withdrawal" in normalise_text("CWDR ANDHERI ATM")
    assert "tax" in normalise_text("GST PAYMENT CHALLAN")


def test_counterparty():
    assert extract_counterparty("UPI/123/PAYMENT/SWIGGY LIMITED/swiggy@okaxis")
    assert extract_counterparty("NEFT CR-HDFC0000123-ACME TECHNOLOGIES-SALARY")


def test_channel_detection():
    assert detect_channel("UPI/123/PAY/x@okaxis") == "UPI"
    assert detect_channel("ATM WDL 00291") == "ATM"
    assert detect_channel("NEFT CR-HDFC") == "NEFT"


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------

def _txn(description: str, direction: str = "DR", amount: str = "100") -> Transaction:
    txn = Transaction(description=description, direction=direction, amount=Decimal(amount))
    from bsp.normalize import apply

    apply(txn)
    return txn


def test_rule_pack_loads_and_is_valid():
    rules = load_rules()
    assert len(rules) > 20
    for rule in rules:
        assert rule.category in taxonomy.CATEGORIES


def test_rules_catch_the_obvious_cases():
    engine = RuleEngine()
    cases = [
        ("NEFT CR-ACME-SALARY SEP 2025", "CR", "Salary"),
        ("UPI/1/ORDER/SWIGGY/swiggy@ok", "DR", "Food & Dining"),
        ("ATM WDL 00291 ANDHERI", "DR", "Cash Withdrawal"),
        ("ACH DR-HDFC HOME LOAN-EMI OCT", "DR", "Loan Repayment"),
        ("BILLPAY MSEDCL ELECTRICITY BILL", "DR", "Utilities"),
        ("AMB CHARGES SEP 2025 INCL GST", "DR", "Bank Charges & Fees"),
    ]
    for description, direction, expected in cases:
        match = engine.classify(_txn(description, direction))
        assert match is not None, description
        assert match.category == expected, f"{description} -> {match.category}"


def test_direction_guard_catches_a_wrong_sided_label():
    assert taxonomy.direction_conflict("Salary", "DR") is True
    assert taxonomy.direction_conflict("Salary", "CR") is False
    assert taxonomy.direction_conflict("Self Transfer", "DR") is False


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

def test_features_include_words_and_characters():
    bag = featurise("swiggy order")
    assert "w:swiggy" in bag
    assert "b:swiggy_order" in bag
    assert any(key.startswith("c:") for key in bag)


def test_naive_bayes_learns_and_survives_a_typo():
    texts = ["swiggy order food"] * 5 + ["atm cash withdrawal"] * 5
    labels = ["Food & Dining"] * 5 + ["Cash Withdrawal"] * 5
    model = NaiveBayesClassifier().fit(texts, labels)
    assert model.predict("swiggy order food")[0] == "Food & Dining"
    assert model.predict("swigy ordr food")[0] == "Food & Dining"   # character n-grams
    assert model.predict("atm cash withdrawal")[0] == "Cash Withdrawal"


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

def _word(text: str, x0: float, top: float) -> dict:
    return {"text": text, "x0": x0, "x1": x0 + len(text) * 5, "top": top,
            "bottom": top + 9, "size": 9}


def test_lines_group_by_vertical_band():
    words = [_word("A", 10, 100), _word("B", 60, 101), _word("C", 10, 130)]
    lines = layout.build_lines(words, tolerance=3)
    assert len(lines) == 2
    assert lines[0]["text"] == "A B"


def test_header_detection_and_banding():
    words = [
        _word("Date", 10, 100), _word("Narration", 60, 100),
        _word("Debit", 300, 100), _word("Credit", 400, 100), _word("Balance", 500, 100),
    ]
    for row in range(5):
        top = 120 + row * 12
        words += [
            _word("01/09/2025", 10, top),
            _word("SOME LONG NARRATION TEXT", 60, top),
            _word("100.00", 300, top),
            _word("200.00", 400, top),
            _word("900.00", 500, top),
        ]
    lines = layout.build_lines(words, tolerance=3)
    header = layout.detect_header(lines)
    assert header is not None
    cells = layout.assign_cells(lines[1], header["bands"])
    assert cells[layout.COL_DATE] == "01/09/2025"
    assert cells[layout.COL_DEBIT] == "100.00"
    assert cells[layout.COL_CREDIT] == "200.00"
    assert cells[layout.COL_BALANCE] == "900.00"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _row(index: int, debit=None, credit=None, balance=None) -> Transaction:
    txn = Transaction(row_index=index)
    txn.debit = Decimal(debit) if debit else None
    txn.credit = Decimal(credit) if credit else None
    txn.balance = Decimal(balance) if balance else None
    return txn


def test_balance_continuity_passes_on_clean_data():
    rows = [
        _row(1, debit="100", balance="900"),
        _row(2, credit="50", balance="950"),
        _row(3, debit="200", balance="750"),
    ]
    checked, breaks, closing = check_balances(rows, Decimal("0.05"), Decimal("1000"))
    assert checked == 3
    assert breaks == []
    assert closing == Decimal("750")


def test_balance_continuity_names_the_broken_row():
    rows = [
        _row(1, debit="100", balance="900"),
        _row(2, credit="50", balance="999"),      # wrong on purpose
        _row(3, debit="200", balance="799"),
    ]
    _checked, breaks, _closing = check_balances(rows, Decimal("0.05"), Decimal("1000"))
    assert breaks == [2]


def test_duplicate_detection():
    a = _row(1, debit="100", balance="900")
    b = _row(2, debit="100", balance="800")
    for row in (a, b):
        row.txn_date = date(2025, 9, 1)
        row.amount = Decimal("100")
        row.direction = "DR"
        row.normalised_text = "same payment"
    groups = find_duplicates([a, b])
    assert groups == [[1, 2]]
