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


def get_amount(line):
    nums = re.findall(r"[\d,]+(?:\.\d+)?", line)
    if not nums:
        return None
    try:
        return float(nums[-1].replace(",", ""))
    except:
        return None


def get_date(line):
    try:
        return parse(line, dayfirst=True).strftime("%Y-%m-%d")
    except:
        return None


@app.post("/extract")
def extract(data: InvoiceInput):

    text = data.invoice_text

    result = {
        "invoice_no": None,
        "date": None,
        "vendor": None,
        "amount": None,
        "tax": None,
        "currency": "INR"
    }

    lines = [x.strip() for x in text.splitlines() if x.strip()]

    total = None
    cgst = None
    sgst = None

    for i, line in enumerate(lines):

        low = line.lower()

        # ---------------- Invoice Number ----------------

        if result["invoice_no"] is None:

            m = re.search(
                r"(invoice\s*(?:no|number|#|id)?|ref(?:erence)?|bill\s*no|doc(?:ument)?\s*no)\s*[:#-]?\s*([A-Za-z0-9\-\/]+)",
                line,
                re.I,
            )

            if m:
                result["invoice_no"] = m.group(2)

        # ---------------- Date ----------------

        if result["date"] is None:

            m = re.search(
                r"(date|issued|invoice date)\s*[:\-]\s*(.+)",
                line,
                re.I,
            )

            if m:
                result["date"] = get_date(m.group(2))

        # ---------------- Vendor ----------------

        if result["vendor"] is None:

            m = re.search(
                r"(vendor|supplier|company|seller|from|bill from|billed by|issued by)\s*[:\-]\s*(.+)",
                line,
                re.I,
            )

            if m:
                result["vendor"] = m.group(2).strip()

        # ---------------- Currency ----------------

        if "currency" in low:

            if "usd" in low:
                result["currency"] = "USD"

            elif "eur" in low:
                result["currency"] = "EUR"

            elif "gbp" in low:
                result["currency"] = "GBP"

            elif "inr" in low:
                result["currency"] = "INR"

        # ---------------- Amount ----------------

        if result["amount"] is None:

            if any(x in low for x in [
                "subtotal",
                "sub total",
                "taxable value",
                "net amount",
                "basic amount",
                "amount before tax",
                "amount excluding tax",
            ]):
                result["amount"] = get_amount(line)

        # ---------------- Tax ----------------

        if "taxable value" in low:
            pass

        elif "igst" in low:
            result["tax"] = get_amount(line)

        elif "gst" in low and "cgst" not in low and "sgst" not in low:
            result["tax"] = get_amount(line)

        elif "cgst" in low:
            cgst = get_amount(line)

        elif "sgst" in low:
            sgst = get_amount(line)

        elif re.match(r"tax\s*[:\-]", low):
            result["tax"] = get_amount(line)

        # ---------------- Total ----------------

        if any(x in low for x in [
            "grand total",
            "total due",
            "amount payable",
            "invoice total",
            "total"
        ]):

            if "subtotal" not in low:
                total = get_amount(line)

    # CGST + SGST

    if result["tax"] is None:

        if cgst is not None and sgst is not None:
            result["tax"] = cgst + sgst

        elif cgst is not None:
            result["tax"] = cgst

        elif sgst is not None:
            result["tax"] = sgst

    # Amount fallback

    if result["amount"] is None:

        if total is not None and result["tax"] is not None:
            result["amount"] = round(total - result["tax"], 2)

    # Vendor fallback

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
            "client",
            "bill to",
            "ship to",
        ]

        for line in lines:

            low = line.lower()

            if any(x in low for x in ignore):
                continue

            if re.search(r"\d", line):
                continue

            result["vendor"] = line.split("—")[0].strip()
            break

    return result
