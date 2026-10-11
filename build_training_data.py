"""Build data/training_data.csv, the seed dataset for the ML classifier.

The seed set is synthetic but realistic: it uses the narration shapes Indian
banks actually print (UPI strings, NEFT blocks, POS lines, ACH mandates) around
a list of real merchant and keyword tokens. Each template is expanded with
several merchants, which gives the model enough variety to generalise beyond
the exact strings the rule pack already covers.

Replace this file with your own labelled history as soon as you have one. Real
data always beats synthetic data. The CSV format is simply:

    description,category

Run it with:  python tools/build_training_data.py
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "training_data.csv"

rng = random.Random(20261011)


def ref() -> str:
    return str(rng.randint(100000000000, 999999999999))


def vpa(name: str) -> str:
    handle = name.lower().replace(" ", "")[:12]
    return f"{handle}@{rng.choice(['okaxis', 'oksbi', 'ybl', 'paytm', 'ibl', 'axl'])}"


TEMPLATES: dict[str, list[tuple[str, list[str]]]] = {
    "Salary": [
        ("NEFT CR-{bank}-{m}-SALARY FOR {mon} {y}-{ref}", ["ACME TECHNOLOGIES PVT LTD", "INFOSYS LTD", "TCS LIMITED", "WIPRO ENTERPRISES", "ZENITH SOLUTIONS"]),
        ("SALARY CREDIT {m} {ref}", ["ACME TECH", "BLUESTONE LABS", "NOVA CONSULTING"]),
        ("ACH CR-{m} PAYROLL-{ref}", ["HDFC BANK PAYROLL", "CITI PAYROLL SERVICES"]),
        ("MONTHLY SALARY {mon} {y} {m}", ["KRISHNA ENTERPRISES", "ORION MEDIA"]),
    ],
    "Interest Income": [
        ("INTEREST CREDIT FOR QTR ENDED {mon} {y}", [""]),
        ("INT.PD:{ref} SAVINGS INTEREST", [""]),
        ("FD INTEREST CREDIT A/C {ref}", [""]),
        ("CREDIT INTEREST CAPITALISED {mon}", [""]),
    ],
    "Investment Income": [
        ("DIVIDEND {m} {ref}", ["RELIANCE INDUSTRIES", "HDFC BANK LTD", "ITC LIMITED", "TCS LTD"]),
        ("ACH CR-{m}-DIVIDEND PAYOUT", ["CAMS MF", "KFINTECH"]),
        ("FD MATURITY PROCEEDS {ref}", [""]),
        ("MF REDEMPTION {m} {ref}", ["AXIS MUTUAL FUND", "SBI MUTUAL FUND"]),
    ],
    "Business Receipts": [
        ("NEFT CR-{m}-INVOICE {ref}", ["SUNRISE TRADERS", "PATEL AND SONS", "VERTEX SUPPLIES"]),
        ("RAZORPAY SETTLEMENT {ref}", [""]),
        ("PAYTM MERCHANT SETTLEMENT {ref}", [""]),
        ("IMPS IN {ref} {m} PAYMENT AGAINST BILL", ["GLOBAL EXPORTS", "SRI BALAJI AGENCY"]),
    ],
    "Refund / Reversal": [
        ("UPI/{ref}/REFUND/{m}/{vpa}", ["AMAZON", "FLIPKART", "MAKEMYTRIP", "SWIGGY"]),
        ("REVERSAL OF FAILED TXN {ref}", [""]),
        ("IMPS RETURN {ref} CHARGEBACK", [""]),
        ("REFUND CPC INCOME TAX {ref}", [""]),
    ],
    "Cash Deposit": [
        ("CASH DEPOSIT AT BRANCH {ref}", [""]),
        ("BY CASH CDM {m}", ["ANDHERI BR", "KORAMANGALA BR", "SECTOR 18 BR"]),
        ("SELF CASH DEP {ref}", [""]),
    ],
    "Transfer In": [
        ("UPI/{ref}/PAYMENT FROM/{m}/{vpa}", ["RAHUL SHARMA", "PRIYA NAIR", "AMIT VERMA", "SNEHA RAO", "VIKRAM SINGH"]),
        ("IMPS IN/{ref}/{m}", ["ANIL KUMAR", "MEENA JOSHI", "SURESH BABU"]),
        ("NEFT CR-{bank}-{m}-{ref}", ["DEEPAK MEHTA", "KAVITA IYER"]),
        ("CHQ DEPOSIT CLG {ref}", [""]),
    ],
    "Loan Disbursal": [
        ("LOAN DISBURSEMENT {ref} {m}", ["HDFC LTD HOME LOAN", "BAJAJ FINANCE"]),
        ("PERSONAL LOAN CREDIT {ref}", [""]),
    ],
    "Rent": [
        ("UPI/{ref}/HOUSE RENT {mon}/{m}/{vpa}", ["LANDLORD RAMESH", "MRS KULKARNI", "PROPERTY OWNER"]),
        ("NEFT DR-{m}-MONTHLY RENT {mon}", ["SHANTI APARTMENTS", "GREEN MEADOWS CHS"]),
        ("SOCIETY MAINTENANCE {mon} {m}", ["LAKE VIEW CHS", "PALM GROVE SOCIETY"]),
        ("NOBROKER RENT PAYMENT {ref}", [""]),
    ],
    "Utilities": [
        ("BILLPAY {m} ELECTRICITY BILL {ref}", ["MSEDCL", "BESCOM", "TATA POWER", "ADANI ELECTRICITY", "BSES RAJDHANI", "TORRENT POWER"]),
        ("ACH DR-{m}-ELECTRICITY", ["JVVNL", "KSEB", "TNEB"]),
        ("UPI/{ref}/GAS BILL/{m}/{vpa}", ["MAHANAGAR GAS", "INDANE GAS", "BHARAT GAS", "GUJARAT GAS"]),
        ("WATER BILL PAYMENT {m} {ref}", ["MUNICIPAL CORP", "JAL BOARD"]),
    ],
    "Telecom & Internet": [
        ("UPI/{ref}/MOBILE RECHARGE/{m}/{vpa}", ["AIRTEL", "JIO", "VI INDIA", "BSNL"]),
        ("BILLPAY POSTPAID BILL {m} {ref}", ["AIRTEL", "VODAFONE IDEA", "JIO POSTPAID"]),
        ("ACH DR-{m}-BROADBAND", ["ACT FIBERNET", "HATHWAY", "EXCITEL", "JIO FIBER"]),
        ("POS {ref} {m} DTH RECHARGE", ["TATA PLAY", "DISH TV"]),
    ],
    "Groceries": [
        ("UPI/{ref}/PAYMENT/{m}/{vpa}", ["BIGBASKET", "BLINKIT", "ZEPTO", "JIOMART", "DMART"]),
        ("POS {ref} {m} PURCHASE", ["D MART AVENUE", "RELIANCE FRESH", "MORE RETAIL", "SPENCERS RETAIL"]),
        ("UPI/{ref}/KIRANA STORE/{m}/{vpa}", ["SHREE PROVISION", "ANNAPURNA STORES"]),
        ("INSTAMART ORDER {ref}", [""]),
    ],
    "Food & Dining": [
        ("UPI/{ref}/ORDER/{m}/{vpa}", ["SWIGGY", "ZOMATO", "DOMINOS", "EATCLUB"]),
        ("POS {ref} {m}", ["MCDONALDS", "KFC INDIA", "BURGER KING", "STARBUCKS", "BARBEQUE NATION", "CHAAYOS"]),
        ("UPI/{ref}/RESTAURANT BILL/{m}/{vpa}", ["PARADISE BIRYANI", "SARAVANA BHAVAN", "CAFE MOCHA"]),
        ("CARD PURCHASE {m} BAKERY {ref}", ["MONGINIS", "THEOBROMA"]),
    ],
    "Shopping": [
        ("UPI/{ref}/ORDER PAYMENT/{m}/{vpa}", ["AMAZON PAY", "FLIPKART", "MYNTRA", "AJIO", "MEESHO", "NYKAA"]),
        ("POS {ref} {m} ECOM PURCHASE", ["AMAZON SELLER", "TATACLIQ", "CROMA RETAIL", "RELIANCE DIGITAL"]),
        ("CARD PURCHASE {m} {ref}", ["SHOPPERS STOP", "LIFESTYLE STORE", "WESTSIDE", "PANTALOONS", "DECATHLON", "IKEA INDIA"]),
    ],
    "Travel & Transport": [
        ("UPI/{ref}/RIDE PAYMENT/{m}/{vpa}", ["UBER INDIA", "OLA CABS", "RAPIDO"]),
        ("POS {ref} {m} TICKET BOOKING", ["IRCTC", "INDIGO AIRLINES", "AIR INDIA", "SPICEJET", "VISTARA"]),
        ("ECOM {m} HOTEL BOOKING {ref}", ["MAKEMYTRIP", "GOIBIBO", "OYO ROOMS", "CLEARTRIP", "YATRA"]),
        ("FASTAG RECHARGE {m} {ref}", ["NHAI FASTAG", "PAYTM FASTAG"]),
        ("UPI/{ref}/METRO RECHARGE/{m}/{vpa}", ["DMRC", "BMRCL"]),
    ],
    "Fuel": [
        ("POS {ref} {m} FUEL", ["INDIAN OIL", "BHARAT PETROLEUM", "HP PETROL PUMP", "SHELL INDIA", "NAYARA ENERGY"]),
        ("UPI/{ref}/PETROL/{m}/{vpa}", ["IOCL FILLING STN", "HPCL PUMP"]),
    ],
    "Healthcare": [
        ("UPI/{ref}/PHARMACY/{m}/{vpa}", ["PHARMEASY", "NETMEDS", "1MG", "MEDPLUS"]),
        ("POS {ref} {m} HOSPITAL", ["APOLLO HOSPITALS", "FORTIS HEALTHCARE", "MAX HOSPITAL"]),
        ("CARD PURCHASE {m} DIAGNOSTIC {ref}", ["DR LAL PATHLABS", "METROPOLIS LABS", "THYROCARE"]),
        ("UPI/{ref}/CLINIC FEE/{m}/{vpa}", ["CITY CLINIC", "PRACTO HEALTH"]),
    ],
    "Education": [
        ("NEFT DR-{m}-SCHOOL FEE {mon}", ["DELHI PUBLIC SCHOOL", "ST XAVIERS", "RYAN INTERNATIONAL"]),
        ("UPI/{ref}/TUITION FEE/{m}/{vpa}", ["BYJUS", "UNACADEMY", "VEDANTU"]),
        ("POS {ref} {m} COURSE FEE", ["COURSERA", "UDEMY", "UPGRAD"]),
        ("COLLEGE FEE PAYMENT {m} {ref}", ["MUMBAI UNIVERSITY", "VIT ACADEMY"]),
    ],
    "Entertainment & Subscriptions": [
        ("POS {ref} {m} SUBSCRIPTION", ["NETFLIX COM", "SPOTIFY INDIA", "DISNEY HOTSTAR", "SONY LIV", "ZEE5"]),
        ("UPI/{ref}/TICKETS/{m}/{vpa}", ["BOOKMYSHOW", "PVR CINEMAS", "INOX LEISURE"]),
        ("ECOM {m} {ref}", ["GOOGLE PLAY", "APPLE COM BILL", "YOUTUBE PREMIUM", "AMAZON PRIME VIDEO"]),
    ],
    "Insurance": [
        ("ACH DR-{m}-PREMIUM {ref}", ["LIC OF INDIA", "HDFC LIFE", "ICICI PRU LIFE", "SBI LIFE", "MAX LIFE"]),
        ("POS {ref} {m} HEALTH INSURANCE", ["STAR HEALTH", "NIVA BUPA", "TATA AIG"]),
        ("UPI/{ref}/INSURANCE PREMIUM/{m}/{vpa}", ["POLICYBAZAAR", "BAJAJ ALLIANZ"]),
        ("MOTOR INSURANCE RENEWAL {m} {ref}", ["ICICI LOMBARD"]),
    ],
    "Investments": [
        ("ACH DR-{m}-SIP INSTALMENT {ref}", ["BSE STAR MF", "NSE MF PLATFORM", "AXIS MUTUAL FUND", "SBI MUTUAL FUND"]),
        ("UPI/{ref}/INVESTMENT/{m}/{vpa}", ["GROWW", "ZERODHA COIN", "KUVERA", "INDMONEY", "ETMONEY"]),
        ("NEFT DR-{m}-TRADING ACCOUNT {ref}", ["ZERODHA BROKING", "UPSTOX", "ANGEL ONE", "ICICI DIRECT"]),
        ("FIXED DEPOSIT CREATION {ref}", [""]),
        ("RD INSTALMENT {mon} {ref}", [""]),
        ("PPF CONTRIBUTION {ref}", [""]),
        ("NPS CONTRIBUTION {m} {ref}", ["NSDL NPS"]),
    ],
    "Loan Repayment": [
        ("ACH DR-{m}-EMI {mon} {ref}", ["HDFC HOME LOAN", "BAJAJ FINANCE", "TATA CAPITAL", "HDB FINANCIAL", "AXIS CAR LOAN"]),
        ("LOAN INSTALMENT DEBIT {ref} {m}", ["ICICI PERSONAL LOAN", "SBI HOME LOAN"]),
        ("EMI DEBIT {mon} {y} {ref}", [""]),
    ],
    "Credit Card Payment": [
        ("CREDIT CARD PAYMENT {m} {ref}", ["HDFC CC", "ICICI CC", "SBI CARD", "AXIS CC", "AMEX"]),
        ("BILLPAY CREDIT CARD BILL {ref}", [""]),
        ("AUTOPAY CC XX{tail} {ref}", [""]),
    ],
    "Taxes": [
        ("GST PAYMENT CHALLAN {ref}", [""]),
        ("TDS REMITTANCE {mon} {y} {ref}", [""]),
        ("ADVANCE TAX PAYMENT CBDT {ref}", [""]),
        ("PROPERTY TAX {m} {ref}", ["MUNICIPAL CORPORATION"]),
        ("PROFESSION TAX {mon} {ref}", [""]),
    ],
    "Bank Charges & Fees": [
        ("AMB CHARGES {mon} {y} INCL GST", [""]),
        ("SMS ALERT CHARGES {mon}", [""]),
        ("DEBIT CARD ANNUAL FEE {ref}", [""]),
        ("CHEQUE RETURN CHARGES {ref}", [""]),
        ("ATM DECLINE CHARGE {ref}", [""]),
        ("LOCKER RENT {y} {ref}", [""]),
        ("PROCESSING FEE {ref}", [""]),
        ("ECS RETURN CHARGE {ref}", [""]),
    ],
    "Cash Withdrawal": [
        ("ATM WDL {ref} {m}", ["ANDHERI ATM", "MG ROAD ATM", "SECTOR 22 ATM"]),
        ("CASH WITHDRAWAL NFS {ref}", [""]),
        ("ATM CASH {m} {ref}", ["HDFC ATM", "SBI ATM", "AXIS ATM"]),
        ("SELF WITHDRAWAL CHQ {ref}", [""]),
    ],
    "Transfer Out": [
        ("UPI/{ref}/PAYMENT TO/{m}/{vpa}", ["ROHIT GUPTA", "NEHA SHARMA", "ARJUN PATEL", "DIVYA MENON"]),
        ("IMPS OUT/{ref}/{m}", ["SANDEEP RAO", "FARHAN KHAN"]),
        ("NEFT DR-{bank}-{m}-{ref}", ["MANOJ TIWARI", "LAKSHMI NARAYAN"]),
        ("CHQ PAID {ref} CLEARING", [""]),
    ],
    "Donation": [
        ("UPI/{ref}/DONATION/{m}/{vpa}", ["AKSHAYA PATRA", "GOONJ NGO", "CRY INDIA", "TEMPLE TRUST"]),
        ("NEFT DR-{m}-CHARITY {ref}", ["PM CARES FUND", "HELPAGE INDIA"]),
    ],
    "Business Expense": [
        ("NEFT DR-{m}-VENDOR PAYMENT {ref}", ["SHREE SUPPLIERS", "PRIME CONTRACTORS", "MAHALAXMI TRADERS"]),
        ("POS {ref} {m} CLOUD SERVICES", ["AWS AMAZON WEB", "GOOGLE CLOUD", "MICROSOFT AZURE"]),
        ("COURIER CHARGES {m} {ref}", ["BLUEDART", "DELHIVERY", "DTDC"]),
        ("PROFESSIONAL FEE {m} {ref}", ["CA SHARMA ASSOCIATES", "LEGAL CONSULTANCY"]),
        ("UPI/{ref}/OFFICE SUPPLIES/{m}/{vpa}", ["STATIONERY MART"]),
    ],
    "Self Transfer": [
        ("TRANSFER TO SELF AC {ref}", [""]),
        ("SELF TRANSFER OWN ACCOUNT {ref}", [""]),
        ("IMPS SELF {ref} OWN AC", [""]),
    ],
}

MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]
BANKS = ["HDFC", "SBIN", "ICIC", "UTIB", "KKBK", "PUNB"]


def expand(template: str, merchant: str) -> str:
    return (
        template.replace("{ref}", ref())
        .replace("{m}", merchant)
        .replace("{vpa}", vpa(merchant or "user"))
        .replace("{mon}", rng.choice(MONTHS))
        .replace("{y}", str(rng.choice([2024, 2025, 2026])))
        .replace("{bank}", rng.choice(BANKS))
        .replace("{tail}", str(rng.randint(1000, 9999)))
        .replace("  ", " ")
        .strip()
    )


def main() -> None:
    rows: list[tuple[str, str]] = []
    for category, templates in TEMPLATES.items():
        for template, merchants in templates:
            for merchant in merchants:
                # Several samples per merchant so references vary.
                for _ in range(3):
                    rows.append((expand(template, merchant), category))

    # Deduplicate while keeping order.
    seen: set[str] = set()
    unique: list[tuple[str, str]] = []
    for description, category in rows:
        key = description.lower()
        if key not in seen:
            seen.add(key)
            unique.append((description, category))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["description", "category"])
        writer.writerows(unique)

    counts: dict[str, int] = {}
    for _d, c in unique:
        counts[c] = counts.get(c, 0) + 1
    print(f"wrote {len(unique)} rows to {OUT}")
    for category in sorted(counts):
        print(f"  {category:<32} {counts[category]}")


if __name__ == "__main__":
    main()
