import os
import json
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dateutil.parser import parse

from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InvoiceRequest(BaseModel):
    invoice_text: str


SYSTEM_PROMPT = """
You are an invoice extraction engine.

Extract ONLY these fields.

Return ONLY valid JSON.

{
  "invoice_no": string|null,
  "date": string|null,
  "vendor": string|null,
  "amount": number|null,
  "tax": number|null,
  "currency": string|null
}

Rules:

1. amount = subtotal BEFORE tax.
2. tax = ONLY tax amount.
3. date MUST be YYYY-MM-DD.
4. vendor is seller/company issuing invoice.
5. invoice_no can appear as:
   Invoice No
   Invoice Number
   Ref
   Reference
   Bill No
   Doc No
   Document Number
6. Currency should be INR, USD, EUR, GBP etc.
7. If missing use null.
8. Return ONLY JSON.
"""


def normalize(data):

    required = [
        "invoice_no",
        "date",
        "vendor",
        "amount",
        "tax",
        "currency",
    ]

    for k in required:
        if k not in data:
            data[k] = None

    if data["date"]:
        try:
            data["date"] = parse(data["date"]).strftime("%Y-%m-%d")
        except:
            data["date"] = None

    if data["amount"] is not None:
        try:
            data["amount"] = float(data["amount"])
        except:
            data["amount"] = None

    if data["tax"] is not None:
        try:
            data["tax"] = float(data["tax"])
        except:
            data["tax"] = None

    return data


@app.post("/extract")
def extract(req: InvoiceRequest):

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": req.invoice_text,
            },
        ],
    )

    text = completion.choices[0].message.content

    try:
        result = json.loads(text)
    except:
        result = {
            "invoice_no": None,
            "date": None,
            "vendor": None,
            "amount": None,
            "tax": None,
            "currency": None,
        }

    return normalize(result)
