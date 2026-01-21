from io import BytesIO
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib import colors


def generate_stock_sheet_pdf(shop, products):
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    elements = []

    # Header styles
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        alignment=TA_CENTER,
        fontSize=20,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        "SubtitleStyle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=11,
        spaceAfter=10
    )

    shop_style = ParagraphStyle(
        "ShopStyle",
        parent=styles["Heading2"],
        alignment=TA_CENTER,
        fontSize=14,
        spaceAfter=12
    )

    # ===== HEADER =====
    elements.append(Paragraph("StockWise", title_style))
    elements.append(Paragraph("Smart Inventory System", subtitle_style))
    elements.append(Paragraph(f"Shop: {shop.name}", shop_style))
    elements.append(
        Paragraph(f"Date: {date.today().strftime('%d %B %Y')}", subtitle_style)
    )

    Spacer(1, 12)

    # ===== TABLE =====
    table_data = [[
        "Product", "Count 1", "Count 2", "Count 3", "Count 4", "Final"
    ]]

    for product in products:
        table_data.append([
            product.name, "______", "______", "______", "______", "______"
        ])

    table = Table(
        table_data,
        colWidths=[150, 60, 60, 60, 60, 60],
        repeatRows=1
    )

    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
    ]))

    elements.append(table)

    doc.build(elements)
    buffer.seek(0)

    return buffer
