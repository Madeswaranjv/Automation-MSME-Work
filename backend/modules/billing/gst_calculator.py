"""GST calculation helpers for billing workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class LineItem:
    """Represent one billable invoice line item."""

    description: str
    hsn_code: str
    quantity: float
    unit_price: float
    gst_rate: float


@dataclass
class GSTBreakdown:
    """Represent the GST split and totals for an invoice."""

    subtotal: float
    cgst_rate: float
    sgst_rate: float
    igst_rate: float
    cgst_amount: float
    sgst_amount: float
    igst_amount: float
    total: float
    supply_type: str


def compute_gst(
    line_items: List[LineItem],
    seller_state_code: str,
    buyer_state_code: str,
) -> GSTBreakdown:
    """Compute GST for a list of line items as intrastate or interstate supply."""
    subtotal = sum(item.quantity * item.unit_price for item in line_items)
    if seller_state_code.strip() == buyer_state_code.strip():
        supply_type = "intrastate"
    else:
        supply_type = "interstate"

    total_gst_amount = sum(
        item.quantity * item.unit_price * item.gst_rate / 100 for item in line_items
    )

    if supply_type == "intrastate":
        cgst = total_gst_amount / 2
        sgst = total_gst_amount / 2
        igst = 0.0
        cgst_rate = line_items[0].gst_rate / 2 if line_items else 0.0
        sgst_rate = cgst_rate
        igst_rate = 0.0
    else:
        cgst = 0.0
        sgst = 0.0
        igst = total_gst_amount
        cgst_rate = 0.0
        sgst_rate = 0.0
        igst_rate = line_items[0].gst_rate if line_items else 0.0

    total = subtotal + total_gst_amount
    return GSTBreakdown(
        subtotal=round(subtotal, 2),
        cgst_rate=round(cgst_rate, 2),
        sgst_rate=round(sgst_rate, 2),
        igst_rate=round(igst_rate, 2),
        cgst_amount=round(cgst, 2),
        sgst_amount=round(sgst, 2),
        igst_amount=round(igst, 2),
        total=round(total, 2),
        supply_type=supply_type,
    )


def validate_hsn(hsn_code: str) -> bool:
    """Return True when an HSN code has 4, 6, or 8 digits."""
    return hsn_code.isdigit() and len(hsn_code) in [4, 6, 8]


INDIA_STATE_CODES: dict[str, str] = {
    "01": "Jammu & Kashmir",
    "02": "Himachal Pradesh",
    "03": "Punjab",
    "04": "Chandigarh",
    "05": "Uttarakhand",
    "06": "Haryana",
    "07": "Delhi",
    "08": "Rajasthan",
    "09": "Uttar Pradesh",
    "10": "Bihar",
    "11": "Sikkim",
    "12": "Arunachal Pradesh",
    "13": "Nagaland",
    "14": "Manipur",
    "15": "Mizoram",
    "16": "Tripura",
    "17": "Meghalaya",
    "18": "Assam",
    "19": "West Bengal",
    "20": "Jharkhand",
    "21": "Odisha",
    "22": "Chhattisgarh",
    "23": "Madhya Pradesh",
    "24": "Gujarat",
    "25": "Daman & Diu",
    "26": "Dadra & Nagar Haveli and Daman & Diu",
    "27": "Maharashtra",
    "28": "Andhra Pradesh (Old)",
    "29": "Karnataka",
    "30": "Goa",
    "31": "Lakshadweep",
    "32": "Kerala",
    "33": "Tamil Nadu",
    "34": "Puducherry",
    "35": "Andaman & Nicobar Islands",
    "36": "Telangana",
    "37": "Andhra Pradesh",
    "38": "Ladakh",
    "97": "Other Territory",
    "99": "Centre Jurisdiction",
}
