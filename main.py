from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dateutil.parser import parse
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InvoiceInput(BaseModel):
    invoice_text: str


# ---------------- Utilities ---------------- #

def parse_amount(text):
    if text is None:
        return None

    m = re.search(r"([\d,]+(?:\.\d+)?)", text)
    if not m:
        return None

    try:
        return float(m.group(1).replace(",", ""))
    except:
        return None


def parse_date(text):
    if not text:
        return None

    try:
        return parse(text, dayfirst=True).strftime("%Y-%m-%d")
    except:
        return None


# ---------------- Extraction ---------------- #

def extract_invoice(text):

    result = {
        "invoice_no": None,
        "date": None,
        "vendor": None,
        "amount": None,
        "tax": None,
        "currency": None,
    }

    lines = [l.strip() for l in text.splitlines() if l.strip()]

    total = None

    # ---------- Pass 1 ----------
    for i, line in enumerate(lines):

        low = line.lower()

        # Currency
        if "currency" in low:
            if "INR" in line.upper():
                result["currency"] = "INR"
            elif "USD" in line.upper():
                result["currency"] = "USD"
            elif "EUR" in line.upper():
                result["currency"] = "EUR"

        if result["currency"] is None:
            if "₹" in line or "RS." in line.upper():
                result["currency"] = "INR"

        # Invoice Number
        patterns = [
            r"invoice\s*no\.?\s*[:#-]?\s*(.+)",
            r"invoice\s*number\s*[:#-]?\s*(.+)",
            r"invoice\s*id\s*[:#-]?\s*(.+)",
            r"ref(?:erence)?\s*[:#-]?\s*(.+)",
            r"bill\s*no\.?\s*[:#-]?\s*(.+)",
            r"document\s*no\.?\s*[:#-]?\s*(.+)",
        ]

        if result["invoice_no"] is None:
            for p in patterns:
                m = re.match(p, line, re.I)
                if m:
                    result["invoice_no"] = m.group(1).strip()
                    break

        # Vendor labels
        vendor_patterns = [
            r"vendor\s*[:\-]\s*(.+)",
            r"supplier\s*[:\-]\s*(.+)",
            r"company\s*[:\-]\s*(.+)",
            r"from\s*[:\-]\s*(.+)",
            r"issued by\s*[:\-]\s*(.+)",
            r"seller\s*[:\-]\s*(.+)",
            r"bill from\s*[:\-]\s*(.+)",
            r"billed by\s*[:\-]\s*(.+)",
        ]

        if result["vendor"] is None:
            for p in vendor_patterns:
                m = re.match(p, line, re.I)
                if m:
                    result["vendor"] = m.group(1).strip()
                    break

        # Date
        if result["date"] is None:
            m = re.match(r"(date|issued|invoice date)\s*[:\-]\s*(.+)", line, re.I)
            if m:
                result["date"] = parse_date(m.group(2))

        # Amount
        if result["amount"] is None:

            if any(x in low for x in [
                "subtotal",
                "sub total",
                "taxable value",
                "net amount",
                "basic amount",
                "amount before tax",
                "amount excluding tax"
            ]):
                result["amount"] = parse_amount(line)

        # Tax
        if result["tax"] is None:

            if any(x in low for x in [
                "gst",
                "cgst",
                "sgst",
                "igst",
                "vat",
                "tax"
            ]):
                result["tax"] = parse_amount(line)

        # Total
        if any(x in low for x in [
            "grand total",
            "total due",
            "amount payable",
            "total"
        ]):
            total = parse_amount(line)

    # ---------- Vendor Fallback ----------

    if result["vendor"] is None:

        ignore = [
            "invoice",
            "ref",
            "reference",
            "date",
            "issued",
            "subtotal",
            "total",
            "gst",
            "cgst",
            "sgst",
            "igst",
            "tax",
            "currency",
            "bill to",
            "client",
        ]

        for line in lines:

            low = line.lower()

            if any(word in low for word in ignore):
                continue

            if re.search(r"\d", line):
                continue

            result["vendor"] = line.split("—")[0].strip()
            break

    # ---------- Amount Fallback ----------

    if result["amount"] is None:

        if total is not None and result["tax"] is not None:
            result["amount"] = round(total - result["tax"], 2)

    if result["currency"] is None:
        result["currency"] = "INR"

    return result


@app.post("/extract")
def extract(data: InvoiceInput):
    return extract_invoice(data.invoice_text)
