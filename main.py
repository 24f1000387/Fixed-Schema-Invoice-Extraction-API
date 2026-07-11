from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dateutil.parser import parse
import re

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InvoiceInput(BaseModel):
    invoice_text: str


# ----------------------------
# Utility Functions
# ----------------------------

def extract_first(patterns, text):
    """
    Try multiple regex patterns and return first match.
    """
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match:
            return match.group(1).strip()
    return None


def parse_amount(value):
    if value is None:
        return None

    value = value.replace(",", "")
    value = re.sub(r"(Rs\.?|INR|₹)", "", value, flags=re.IGNORECASE).strip()

    try:
        return float(value)
    except:
        return None


def parse_date(value):
    if value is None:
        return None

    try:
        return parse(value, dayfirst=True).strftime("%Y-%m-%d")
    except:
        return None


# ----------------------------
# Extraction Functions
# ----------------------------

def extract_invoice_no(text):
    patterns = [
        r"Invoice\s*No\.?\s*[:#-]?\s*([A-Za-z0-9\-\/]+)",
        r"Invoice\s*Number\s*[:#-]?\s*([A-Za-z0-9\-\/]+)",
        r"Invoice\s*#\s*([A-Za-z0-9\-\/]+)",
        r"Invoice\s*ID\s*[:#-]?\s*([A-Za-z0-9\-\/]+)",
        r"Invoice\s*Ref(?:erence)?\s*[:#-]?\s*([A-Za-z0-9\-\/]+)",
        r"Reference\s*(?:No)?\s*[:#-]?\s*([A-Za-z0-9\-\/]+)",
        r"Ref\s*[:#-]?\s*([A-Za-z0-9\-\/]+)",
        r"Bill\s*No\.?\s*[:#-]?\s*([A-Za-z0-9\-\/]+)",
        r"Document\s*No\.?\s*[:#-]?\s*([A-Za-z0-9\-\/]+)",
        r"Doc\s*No\.?\s*[:#-]?\s*([A-Za-z0-9\-\/]+)"
    ]

    return extract_first(patterns, text)


def extract_vendor(text):
    patterns = [
        r"Vendor\s*[:\-]\s*(.+)",
        r"Supplier\s*[:\-]\s*(.+)",
        r"Sold\s*By\s*[:\-]\s*(.+)",
        r"Company\s*[:\-]\s*(.+)"
    ]

    vendor = extract_first(patterns, text)

    if vendor:
        vendor = vendor.split("\n")[0].strip()

    return vendor


def extract_date(text):
    patterns = [
        r"Date\s*[:\-]\s*(.+)",
        r"Invoice\s*Date\s*[:\-]\s*(.+)",
        r"Dated\s*[:\-]\s*(.+)"
    ]

    date = extract_first(patterns, text)

    if date:
        date = date.split("\n")[0]

    return parse_date(date)


def extract_subtotal(text):
    patterns = [
        r"Subtotal\s*[:\-]?\s*(?:Rs\.?|₹|INR)?\s*([\d,]+\.\d{2})",
        r"Sub\s*Total\s*[:\-]?\s*(?:Rs\.?|₹|INR)?\s*([\d,]+\.\d{2})",
        r"Amount\s*Before\s*Tax\s*[:\-]?\s*(?:Rs\.?|₹|INR)?\s*([\d,]+\.\d{2})",
        r"Net\s*Amount\s*[:\-]?\s*(?:Rs\.?|₹|INR)?\s*([\d,]+\.\d{2})"
    ]

    return parse_amount(extract_first(patterns, text))


def extract_tax(text):
    patterns = [
        r"GST.*?[:\-]?\s*(?:Rs\.?|₹|INR)?\s*([\d,]+\.\d{2})",
        r"CGST.*?[:\-]?\s*(?:Rs\.?|₹|INR)?\s*([\d,]+\.\d{2})",
        r"SGST.*?[:\-]?\s*(?:Rs\.?|₹|INR)?\s*([\d,]+\.\d{2})",
        r"IGST.*?[:\-]?\s*(?:Rs\.?|₹|INR)?\s*([\d,]+\.\d{2})",
        r"Tax.*?[:\-]?\s*(?:Rs\.?|₹|INR)?\s*([\d,]+\.\d{2})",
        r"VAT.*?[:\-]?\s*(?:Rs\.?|₹|INR)?\s*([\d,]+\.\d{2})"
    ]

    return parse_amount(extract_first(patterns, text))


def extract_currency(text):
    if "USD" in text.upper():
        return "USD"

    if "EUR" in text.upper():
        return "EUR"

    if "GBP" in text.upper():
        return "GBP"

    if "INR" in text.upper() or "RS." in text.upper() or "₹" in text:
        return "INR"

    return "INR"


# ----------------------------
# API Endpoint
# ----------------------------

@app.post("/extract")
def extract_invoice(data: InvoiceInput):

    text = data.invoice_text

    result = {
        "invoice_no": extract_invoice_no(text),
        "date": extract_date(text),
        "vendor": extract_vendor(text),
        "amount": extract_subtotal(text),
        "tax": extract_tax(text),
        "currency": extract_currency(text),
    }

    return result
