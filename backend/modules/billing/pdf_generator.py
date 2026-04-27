"""PDF invoice generation helpers for billing workflows."""

from __future__ import annotations

import io
import os
from datetime import datetime
from urllib.parse import quote

import qrcode
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from xml.sax.saxutils import escape

from modules.billing.gst_calculator import GSTBreakdown, LineItem

OUTPUT_DIR = os.getenv("PDF_OUTPUT_DIR", "./generated_pdfs")
os.makedirs(OUTPUT_DIR, exist_ok=True)
_ = LineItem


def _safe_filename(value: str) -> str:
    """Return a filesystem-safe filename fragment."""
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)


def _to_float(value: object, default: float = 0.0) -> float:
    """Convert an input value to float with a default fallback."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def generate_upi_qr(upi_id: str, amount: float, payee_name: str, invoice_number: str) -> str:
    """Generate a UPI QR PNG file and return its absolute path."""
    upi_link = (
        f"upi://pay?pa={upi_id}&pn={quote(payee_name)}&am={amount:.2f}"
        f"&tn=Invoice {invoice_number}&cu=INR"
    )
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=6,
        border=2,
    )
    qr.add_data(upi_link)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    file_path = os.path.abspath(
        os.path.join(OUTPUT_DIR, f"qr_{_safe_filename(invoice_number)}.png")
    )
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    with open(file_path, "wb") as file_obj:
        file_obj.write(buffer.getvalue())
    buffer.close()
    return file_path


def _words_under_100(number: int) -> str:
    """Convert a number below 100 into words."""
    ones = [
        "Zero",
        "One",
        "Two",
        "Three",
        "Four",
        "Five",
        "Six",
        "Seven",
        "Eight",
        "Nine",
        "Ten",
        "Eleven",
        "Twelve",
        "Thirteen",
        "Fourteen",
        "Fifteen",
        "Sixteen",
        "Seventeen",
        "Eighteen",
        "Nineteen",
    ]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    if number < 20:
        return ones[number]
    tens_value = tens[number // 10]
    remainder = number % 10
    return tens_value if remainder == 0 else f"{tens_value} {ones[remainder]}"


def _words_under_1000(number: int) -> str:
    """Convert a number below 1000 into words."""
    if number < 100:
        return _words_under_100(number)
    hundreds = number // 100
    remainder = number % 100
    prefix = f"{_words_under_100(hundreds)} Hundred"
    return prefix if remainder == 0 else f"{prefix} {_words_under_100(remainder)}"


def _int_to_indian_words(number: int) -> str:
    """Convert an integer amount into Indian numbering words."""
    if number == 0:
        return "Zero"
    if number > 9999999:
        raise ValueError("Amount exceeds supported limit of 99,99,999.")

    parts: list[str] = []
    lakhs = number // 100000
    if lakhs:
        parts.append(f"{_words_under_100(lakhs)} Lakh")
    number %= 100000

    thousands = number // 1000
    if thousands:
        parts.append(f"{_words_under_100(thousands)} Thousand")
    number %= 1000

    if number:
        parts.append(_words_under_1000(number))

    return " ".join(parts)


def rupees_in_words(amount: float) -> str:
    """Convert a rupee amount into Indian words ending with Only."""
    total_paise = int(round(amount * 100))
    rupees = total_paise // 100
    paise = total_paise % 100
    if rupees > 9999999:
        raise ValueError("Amount exceeds supported limit of 99,99,999.")

    words = f"Rupees {_int_to_indian_words(rupees)}"
    if paise:
        words = f"{words} and {_words_under_100(paise)} Paise"
    return f"{words} Only"


def generate_invoice_pdf(
    invoice_number: str,
    invoice_date: str,
    seller: dict,
    buyer: dict,
    line_items: list[dict],
    gst_breakdown: GSTBreakdown,
    due_date: str | None = None,
) -> str:
    """Generate a complete GST invoice PDF and return its absolute path."""
    _ = datetime
    file_path = os.path.abspath(
        os.path.join(OUTPUT_DIR, f"invoice_{_safe_filename(invoice_number)}.pdf")
    )
    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    heading_style = ParagraphStyle(
        "HeadingStyle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=colors.HexColor("#1a1a2e"),
        alignment=TA_CENTER,
        spaceAfter=0,
    )
    subheading_style = ParagraphStyle(
        "SubheadingStyle",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=colors.HexColor("#16213e"),
        alignment=TA_LEFT,
    )
    normal_style = ParagraphStyle(
        "NormalStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        textColor=colors.HexColor("#333333"),
        leading=12,
        alignment=TA_LEFT,
    )
    small_style = ParagraphStyle(
        "SmallStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        textColor=colors.HexColor("#666666"),
        leading=10,
        alignment=TA_CENTER,
    )
    right_style = ParagraphStyle(
        "RightStyle",
        parent=normal_style,
        alignment=TA_RIGHT,
    )
    bold_right = ParagraphStyle(
        "BoldRightStyle",
        parent=normal_style,
        fontName="Helvetica-Bold",
        fontSize=10,
        alignment=TA_RIGHT,
    )

    story: list[object] = []
    story.append(Paragraph("TAX INVOICE", heading_style))
    story.append(Spacer(1, 4 * mm))

    seller_lines = [
        "<b>From:</b>",
        escape(str(seller.get("name", ""))),
        escape(str(seller.get("address", ""))).replace("\n", "<br/>"),
        f"GSTIN: {escape(str(seller.get('gstin', '')))}",
        f"Ph: {escape(str(seller.get('phone', '')))}",
    ]
    buyer_lines = [
        f"Invoice No: {escape(invoice_number)}",
        f"Date: {escape(invoice_date)}",
        f"Due Date: {escape(due_date or 'On Receipt')}",
        "<b>To:</b>",
        escape(str(buyer.get("name", ""))),
        escape(str(buyer.get("address", ""))).replace("\n", "<br/>"),
        f"GSTIN: {escape(str(buyer.get('gstin') or 'Unregistered'))}",
    ]
    party_table = Table(
        [
            [
                Paragraph("<br/>".join(seller_lines), normal_style),
                Paragraph("<br/>".join(buyer_lines), normal_style),
            ]
        ],
        colWidths=[90 * mm, 90 * mm],
    )
    party_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0, colors.white),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(party_table)
    story.append(Spacer(1, 5 * mm))

    item_rows: list[list[str]] = [["#", "Description", "HSN", "Qty", "Unit", "Rate", "Amount"]]
    for index, item in enumerate(line_items, start=1):
        quantity = _to_float(item.get("quantity"))
        unit_price = _to_float(item.get("unit_price"))
        amount = quantity * unit_price
        item_rows.append(
            [
                str(index),
                str(item.get("description", "")),
                str(item.get("hsn_code", "")),
                f"{quantity:g}",
                str(item.get("unit", "pcs")),
                f"Rs. {unit_price:,.2f}",
                f"Rs. {amount:,.2f}",
            ]
        )

    items_table = Table(
        item_rows,
        colWidths=[8 * mm, 60 * mm, 18 * mm, 14 * mm, 14 * mm, 22 * mm, 22 * mm],
        repeatRows=1,
    )
    items_style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d9dce1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (3, 1), (6, -1), "RIGHT"),
        ("ALIGN", (0, 0), (0, -1), "CENTER"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for row_index in range(1, len(item_rows)):
        background = colors.white if row_index % 2 else colors.HexColor("#f8f9fa")
        items_style_commands.append(("BACKGROUND", (0, row_index), (-1, row_index), background))
    items_table.setStyle(TableStyle(items_style_commands))
    story.append(items_table)
    story.append(Spacer(1, 4 * mm))

    totals_rows = [["Subtotal", f"Rs. {gst_breakdown.subtotal:,.2f}"]]
    if gst_breakdown.supply_type == "intrastate":
        totals_rows.append(
            [f"CGST @ {gst_breakdown.cgst_rate:g}%", f"Rs. {gst_breakdown.cgst_amount:,.2f}"]
        )
        totals_rows.append(
            [f"SGST @ {gst_breakdown.sgst_rate:g}%", f"Rs. {gst_breakdown.sgst_amount:,.2f}"]
        )
    else:
        totals_rows.append(
            [f"IGST @ {gst_breakdown.igst_rate:g}%", f"Rs. {gst_breakdown.igst_amount:,.2f}"]
        )
    totals_rows.append(["", ""])
    totals_rows.append(["TOTAL", f"Rs. {gst_breakdown.total:,.2f}"])

    totals_table = Table(totals_rows, colWidths=[130 * mm, 28 * mm], hAlign="RIGHT")
    totals_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
                ("FONTNAME", (0, 0), (-1, -2), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LINEABOVE", (0, -2), (-1, -2), 0.8, colors.HexColor("#1a1a2e")),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#1a1a2e")),
                ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, -1), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(totals_table)
    story.append(Spacer(1, 4 * mm))

    story.append(
        Paragraph(
            f"<b>Amount in Words:</b> {escape(rupees_in_words(gst_breakdown.total))}",
            normal_style,
        )
    )
    story.append(Spacer(1, 5 * mm))

    if seller.get("upi_id"):
        qr_path = generate_upi_qr(
            upi_id=str(seller.get("upi_id")),
            amount=gst_breakdown.total,
            payee_name=str(seller.get("name", "Merchant")),
            invoice_number=invoice_number,
        )
        qr_section = Table(
            [
                [
                    [
                        Paragraph("Scan to Pay", subheading_style),
                        Spacer(1, 2 * mm),
                        RLImage(qr_path, width=30 * mm, height=30 * mm),
                    ],
                    [
                        Paragraph("Bank Details", subheading_style),
                        Spacer(1, 2 * mm),
                        Paragraph(
                            escape(
                                f"UPI ID: {seller.get('upi_id', '')}\n"
                                "Use the QR code to pay this invoice."
                            ).replace("\n", "<br/>"),
                            normal_style,
                        ),
                    ],
                ]
            ],
            colWidths=[55 * mm, 103 * mm],
        )
        qr_section.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#d9dce1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(qr_section)
        story.append(Spacer(1, 5 * mm))

    story.append(Paragraph("This is a computer-generated invoice.", small_style))
    story.append(Spacer(1, 1.5 * mm))
    story.append(Paragraph("Thank you for your business.", small_style))

    doc.build(story)
    return file_path
