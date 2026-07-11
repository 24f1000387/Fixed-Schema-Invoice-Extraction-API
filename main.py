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


def extract(pattern, text):
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def clean_amount(value):
    if value is None:
        return None
    value = value.replace(",", "")
    value = re.sub(r"Rs\.?|INR", "", value, flags=re.I).strip()
    try:
        return float(value)
    except:
        return None


@app.post("/extract")
def extract_invoice(data: InvoiceInput):

    text = data.invoice_text

    invoice_no = extract(
        r"Invoice\s*(?:No|Number)?\s*[:#]?\s*([A-Za-z0-9\-\/]+)", text
    )

    vendor = extract(
        r"Vendor\s*[:\-]\s*(.+)", text
    )

    date_text = extract(
        r"Date\s*[:\-]\s*(.+)", text
    )

    date = None
    if date_text:
        try:
            date = parse(date_text, dayfirst=True).strftime("%Y-%m-%d")
        except:
            pass

    subtotal = extract(
        r"(?:Subtotal|Sub Total)\s*[:\-]?\s*(?:Rs\.?|INR)?\s*([\d,]+\.\d{2})",
        text,
    )

    tax = extract(
        r"(?:GST|CGST|SGST|IGST|Tax).*?[:\-]?\s*(?:Rs\.?|INR)?\s*([\d,]+\.\d{2})",
        text,
    )

    return {
        "invoice_no": invoice_no,
        "date": date,
        "vendor": vendor,
        "amount": clean_amount(subtotal),
        "tax": clean_amount(tax),
        "currency": "INR",
    }
