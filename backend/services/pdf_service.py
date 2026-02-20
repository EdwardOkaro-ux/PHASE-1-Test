"""
PDF generation service for Servex Holdings backend.
Handles invoice PDF generation using ReportLab.
"""
from io import BytesIO
from datetime import datetime
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from database import db


def format_weight(weight, decimals=4):
    """Format weight with specified decimal places"""
    if weight is None:
        return "-"
    return f"{float(weight):.{decimals}f}"


def format_dimension(dim, decimals=3):
    """Format dimension with specified decimal places"""
    if dim is None:
        return "-"
    return f"{float(dim):.{decimals}f}"


def format_dimensions(length, width, height, decimals=3):
    """Format L×W×H dimensions"""
    if not length and not width and not height:
        return "-"
    len_str = format_dimension(length, decimals) if length else "0"
    wid_str = format_dimension(width, decimals) if width else "0"
    hei_str = format_dimension(height, decimals) if height else "0"
    return f"{len_str} × {wid_str} × {hei_str}"


def format_currency(amount, currency="ZAR"):
    """Format currency amount"""
    if amount is None:
        return "-"
    symbols = {"ZAR": "R", "KES": "KES", "USD": "$", "EUR": "€", "GBP": "£"}
    symbol = symbols.get(currency, currency)
    return f"{symbol} {float(amount):,.2f}"


def get_payment_terms_display(payment_terms, payment_terms_custom, total):
    """Get payment terms display text with calculated amounts"""
    if not payment_terms:
        return None
    
    terms_map = {
        "full_on_receipt": "Full payment due on receipt",
        "net_30": "Net 30 days",
        "custom": payment_terms_custom or "Custom terms"
    }
    
    if payment_terms == "50_50":
        half = total / 2
        return f"50% upfront, 50% on delivery\n• Due on receipt: {format_currency(half)}\n• Due on delivery: {format_currency(half)}"
    elif payment_terms == "30_70":
        upfront = total * 0.3
        delivery = total * 0.7
        return f"30% upfront, 70% on delivery\n• Due on receipt: {format_currency(upfront)}\n• Due on delivery: {format_currency(delivery)}"
    
    return terms_map.get(payment_terms, payment_terms)


async def generate_invoice_pdf(
    invoice_id: str,
    tenant_id: str
):
    """Generate a professional PDF invoice with full client and recipient details"""
    
    # Fetch invoice with all related data
    invoice = await db.invoices.find_one({"id": invoice_id, "tenant_id": tenant_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Get client (use snapshot if available, fallback to current)
    client = await db.clients.find_one({"id": invoice.get("client_id")}, {"_id": 0})
    
    # Prefer snapshot data for historical accuracy
    client_name = invoice.get("client_name_snapshot") or (client.get("name") if client else "Unknown")
    client_address = invoice.get("client_address_snapshot") or (client.get("billing_address") or client.get("physical_address") if client else "")
    client_vat = invoice.get("client_vat_snapshot") or (client.get("vat_number") if client else "")
    client_phone = invoice.get("client_phone_snapshot") or (client.get("phone") if client else "")
    client_email = invoice.get("client_email_snapshot") or (client.get("email") if client else "")
    
    # Get line items with enriched data
    line_items = await db.invoice_line_items.find({"invoice_id": invoice_id}, {"_id": 0}).to_list(100)
    
    # Get shipments for recipient details
    shipment_ids = [li.get("shipment_id") for li in line_items if li.get("shipment_id")]
    shipments = {}
    if shipment_ids:
        shipment_docs = await db.shipments.find(
            {"id": {"$in": shipment_ids}},
            {"_id": 0}
        ).to_list(100)
        shipments = {s["id"]: s for s in shipment_docs}
    
    # Get adjustments
    adjustments = await db.invoice_adjustments.find({"invoice_id": invoice_id}, {"_id": 0}).to_list(100)
    
    # Get payments
    payments = await db.payments.find({"invoice_id": invoice_id}, {"_id": 0}).to_list(100)
    paid_amount = sum(p.get("amount", 0) for p in payments)
    
    # Define colors
    olive = colors.HexColor('#6B633C')
    dark_gray = colors.HexColor('#3C3F42')
    light_gray = colors.HexColor('#F5F5F5')
    
    # Currency
    currency = invoice.get("currency", "ZAR")
    
    # Create PDF buffer
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=15*mm, bottomMargin=15*mm)
    
    # Styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='CompanyName', fontSize=14, fontName='Helvetica-Bold', textColor=dark_gray))
    styles.add(ParagraphStyle(name='CompanyInfo', fontSize=9, fontName='Helvetica', textColor=dark_gray, leading=12))
    styles.add(ParagraphStyle(name='InvoiceTitle', fontSize=22, fontName='Helvetica-Bold', textColor=olive, alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name='InvoiceInfo', fontSize=10, fontName='Helvetica', textColor=dark_gray, alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name='SectionTitle', fontSize=11, fontName='Helvetica-Bold', textColor=dark_gray))
    styles.add(ParagraphStyle(name='ClientInfo', fontSize=10, fontName='Helvetica', textColor=dark_gray, leading=14))
    styles.add(ParagraphStyle(name='TotalLabel', fontSize=12, fontName='Helvetica-Bold', textColor=dark_gray, alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name='TotalAmount', fontSize=16, fontName='Helvetica-Bold', textColor=olive, alignment=TA_RIGHT))
    styles.add(ParagraphStyle(name='FooterStyle', fontSize=8, fontName='Helvetica', textColor=colors.gray, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='PaymentTerms', fontSize=10, fontName='Helvetica', textColor=dark_gray, leading=14))
    styles.add(ParagraphStyle(name='SmallText', fontSize=8, fontName='Helvetica', textColor=dark_gray))
    
    elements = []
    
    # Header section
    logo_path = Path(__file__).parent.parent / 'frontend' / 'public' / 'servex-logo.png'
    
    left_content = []
    if logo_path.exists():
        try:
            from PIL import Image as PILImage
            img = PILImage.open(logo_path)
            aspect = img.height / img.width
            logo = Image(str(logo_path), width=100, height=100*aspect)
            left_content.append(logo)
        except Exception:
            left_content.append(Paragraph("SERVEX HOLDINGS", styles['CompanyName']))
    else:
        left_content.append(Paragraph("SERVEX HOLDINGS", styles['CompanyName']))
    
    left_content.append(Spacer(1, 3*mm))
    left_content.append(Paragraph("<b>SERVEX HOLDINGS (PTY) LTD</b>", styles['CompanyInfo']))
    left_content.append(Paragraph("Unit 19 Eastborough Business Park", styles['CompanyInfo']))
    left_content.append(Paragraph("15 Olympia Street, Eastgate", styles['CompanyInfo']))
    left_content.append(Paragraph("Johannesburg 2090", styles['CompanyInfo']))
    left_content.append(Paragraph("info@servexholdings.com | +27 79 645 6281", styles['CompanyInfo']))
    
    # Invoice info (right side)
    issue_date = invoice.get('issue_date') or invoice.get('created_at', '')[:10]
    due_date = invoice.get('due_date', '')
    
    right_content = []
    right_content.append(Paragraph("INVOICE", styles['InvoiceTitle']))
    right_content.append(Spacer(1, 2*mm))
    right_content.append(Paragraph(f"<b>Invoice #:</b> {invoice.get('invoice_number', 'N/A')}", styles['InvoiceInfo']))
    right_content.append(Paragraph(f"<b>Date:</b> {issue_date}", styles['InvoiceInfo']))
    right_content.append(Paragraph(f"<b>Due:</b> {due_date}", styles['InvoiceInfo']))
    right_content.append(Paragraph(f"<b>Status:</b> {invoice.get('status', 'draft').upper()}", styles['InvoiceInfo']))
    
    header_table = Table([[left_content, right_content]], colWidths=[100*mm, 80*mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 8*mm))
    
    # Bill To section with full client details
    elements.append(Paragraph("Bill To:", styles['SectionTitle']))
    elements.append(Spacer(1, 2*mm))
    
    bill_to_text = f"<b>{client_name}</b><br/>"
    if client_address:
        bill_to_text += f"{client_address}<br/>"
    if client_vat:
        bill_to_text += f"VAT: {client_vat}<br/>"
    if client_phone:
        bill_to_text += f"Tel: {client_phone}<br/>"
    if client_email:
        bill_to_text += f"Email: {client_email}"
    
    elements.append(Paragraph(bill_to_text, styles['ClientInfo']))
    elements.append(Spacer(1, 6*mm))
    
    # Collect unique recipients from line items
    recipients = {}
    for li in line_items:
        shipment_id = li.get("shipment_id")
        if shipment_id and shipment_id in shipments:
            s = shipments[shipment_id]
            recipient_name = li.get("recipient_name") or s.get("recipient")
            if recipient_name and recipient_name not in recipients:
                recipients[recipient_name] = {
                    "name": recipient_name,
                    "phone": s.get("recipient_phone"),
                    "vat": s.get("recipient_vat"),
                    "address": s.get("shipping_address")
                }
    
    # Ship To section (if recipient differs from client)
    if recipients:
        elements.append(Paragraph("Ship To:", styles['SectionTitle']))
        elements.append(Spacer(1, 2*mm))
        
        for r_name, r_info in recipients.items():
            ship_to_text = f"<b>{r_info['name']}</b><br/>"
            if r_info.get("address"):
                ship_to_text += f"{r_info['address']}<br/>"
            if r_info.get("vat"):
                ship_to_text += f"VAT: {r_info['vat']}<br/>"
            if r_info.get("phone"):
                ship_to_text += f"Tel: {r_info['phone']}"
            elements.append(Paragraph(ship_to_text, styles['ClientInfo']))
            elements.append(Spacer(1, 2*mm))
        
        elements.append(Spacer(1, 4*mm))
    
    # Line Items Table with enhanced columns
    table_data = [['#', 'Description', 'Dimensions', 'Qty', 'Weight', 'Rate', 'Amount']]
    
    total_qty = 0
    for idx, item in enumerate(line_items, 1):
        shipment = shipments.get(item.get("shipment_id"), {})
        
        # Get parcel label
        parcel_label = item.get("parcel_label", "")
        if not parcel_label and shipment:
            seq = shipment.get("parcel_sequence")
            total = shipment.get("total_in_sequence")
            if seq and total:
                parcel_label = f"{seq}/{total}"
        
        # Get dimensions from line item or shipment
        length = item.get("length_cm") or shipment.get("length_cm")
        width = item.get("width_cm") or shipment.get("width_cm")
        height = item.get("height_cm") or shipment.get("height_cm")
        dimensions = format_dimensions(length, width, height)
        
        qty = item.get('quantity', 1)
        total_qty += qty
        weight = item.get('weight') or item.get('quantity', 0)
        rate = item.get('rate', 0)
        amount = item.get('amount') or (weight * rate)
        
        # Build description with recipient if different
        desc = item.get('description', '')[:40]
        recipient = item.get('recipient_name') or shipment.get('recipient')
        if recipient:
            desc = f"{desc}\n({recipient})"
        
        table_data.append([
            f"{idx}. {parcel_label}" if parcel_label else str(idx),
            Paragraph(desc, styles['SmallText']),
            dimensions,
            str(int(qty)),
            format_weight(weight),
            format_currency(rate, currency),
            format_currency(amount, currency)
        ])
    
    if not line_items:
        table_data.append(['', 'No line items', '', '', '', '', ''])
    
    # Create table with proper column widths
    col_widths = [18*mm, 50*mm, 32*mm, 12*mm, 22*mm, 22*mm, 26*mm]
    items_table = Table(table_data, colWidths=col_widths)
    
    # Table styling
    table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), olive),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]
    
    # Alternating row colors
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            table_style.append(('BACKGROUND', (0, i), (-1, i), light_gray))
    
    items_table.setStyle(TableStyle(table_style))
    elements.append(items_table)
    elements.append(Spacer(1, 2*mm))
    
    # Item count
    elements.append(Paragraph(f"<i>{len(line_items)} line items | Total Qty: {int(total_qty)} pieces</i>", styles['SmallText']))
    elements.append(Spacer(1, 6*mm))
    
    # Adjustments section
    if adjustments:
        elements.append(Paragraph("Adjustments:", styles['SectionTitle']))
        elements.append(Spacer(1, 2*mm))
        
        adj_data = [['Description', 'Amount']]
        for adj in adjustments:
            sign = "+" if adj.get("is_addition", True) else "-"
            amt = adj.get("amount", 0)
            adj_data.append([
                adj.get("description", "Adjustment"),
                f"{sign} {format_currency(amt, currency)}"
            ])
        
        adj_table = Table(adj_data, colWidths=[130*mm, 30*mm])
        adj_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(adj_table)
        elements.append(Spacer(1, 4*mm))
    
    # Totals section
    subtotal = invoice.get('subtotal', 0)
    adj_total = invoice.get('adjustments', 0)
    total = invoice.get('total', 0)
    outstanding = total - paid_amount
    
    totals_data = [
        ['Subtotal:', format_currency(subtotal, currency)],
    ]
    
    if adj_total != 0:
        sign = "+" if adj_total >= 0 else ""
        totals_data.append(['Adjustments:', f"{sign}{format_currency(adj_total, currency)}"])
    
    totals_data.append(['TOTAL:', format_currency(total, currency)])
    
    if paid_amount > 0:
        totals_data.append(['Paid:', format_currency(paid_amount, currency)])
        totals_data.append(['Outstanding:', format_currency(outstanding, currency)])
    
    totals_table = Table(totals_data, colWidths=[130*mm, 40*mm])
    totals_style = [
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]
    
    # Bold the total row
    total_row_idx = 2 if adj_total != 0 else 1
    totals_style.append(('FONTNAME', (0, total_row_idx), (-1, total_row_idx), 'Helvetica-Bold'))
    totals_style.append(('FONTSIZE', (0, total_row_idx), (-1, total_row_idx), 12))
    totals_style.append(('TEXTCOLOR', (1, total_row_idx), (1, total_row_idx), olive))
    
    totals_table.setStyle(TableStyle(totals_style))
    elements.append(totals_table)
    elements.append(Spacer(1, 6*mm))
    
    # Payment terms
    payment_terms = invoice.get("payment_terms")
    if payment_terms:
        terms_display = get_payment_terms_display(
            payment_terms,
            invoice.get("payment_terms_custom"),
            total
        )
        if terms_display:
            elements.append(Paragraph("<b>Payment Terms:</b>", styles['SectionTitle']))
            elements.append(Spacer(1, 2*mm))
            elements.append(Paragraph(terms_display.replace("\n", "<br/>"), styles['PaymentTerms']))
            elements.append(Spacer(1, 4*mm))
    
    # Banking details
    elements.append(Paragraph("<b>Banking Details:</b>", styles['SectionTitle']))
    elements.append(Spacer(1, 2*mm))
    banking = """
    Bank: First National Bank (FNB)<br/>
    Account Name: Servex Holdings (Pty) Ltd<br/>
    Account Number: 62842877857<br/>
    Branch Code: 250655<br/>
    Reference: {invoice_number}
    """.format(invoice_number=invoice.get('invoice_number', ''))
    elements.append(Paragraph(banking, styles['ClientInfo']))
    elements.append(Spacer(1, 8*mm))
    
    # Footer
    elements.append(Paragraph(
        f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} | Servex Holdings (Pty) Ltd | Thank you for your business",
        styles['FooterStyle']
    ))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    filename = f"Invoice-{invoice.get('invoice_number', invoice_id)}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
