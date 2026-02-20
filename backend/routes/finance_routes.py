"""
Finance routes for Servex Holdings backend.
Handles finance hub operations: client statements, trip worksheets, overdue tracking.
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from io import BytesIO
import uuid

from database import db
from dependencies import get_current_user, get_tenant_id
from models.enums import InvoiceStatus

router = APIRouter()

# ============ SETTINGS - CURRENCIES ============

@router.get("/settings/currencies")
async def get_currencies(tenant_id: str = Depends(get_tenant_id)):
    """Get currency settings including exchange rates"""
    # Try to get from tenant settings, fallback to defaults
    settings = await db.settings.find_one({"tenant_id": tenant_id}, {"_id": 0})
    
    if settings and settings.get("currencies"):
        return {"currencies": settings["currencies"]}
    
    # Return default currencies
    return {
        "currencies": [
            {"code": "ZAR", "name": "South African Rand", "symbol": "R", "exchange_rate": 1.0},
            {"code": "KES", "name": "Kenyan Shilling", "symbol": "KES", "exchange_rate": 6.67}
        ]
    }

@router.put("/settings/currencies")
async def update_currencies(
    data: dict,
    tenant_id: str = Depends(get_tenant_id),
    user: dict = Depends(get_current_user)
):
    """Update currency exchange rates"""
    currencies = data.get("currencies", [])
    
    await db.settings.update_one(
        {"tenant_id": tenant_id},
        {"$set": {"currencies": currencies, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    
    return {"message": "Currencies updated", "currencies": currencies}

@router.get("/finance/client-statements")
async def get_client_statements(tenant_id: str = Depends(get_tenant_id)):
    """
    Get all clients with their outstanding amounts grouped by trip.
    Returns data matching the Excel statement summary format.
    """
    # Get all clients for this tenant (limit to 1000)
    clients = await db.clients.find({"tenant_id": tenant_id}).to_list(1000)
    
    # Get all trips to determine which trips to show as columns
    trips = await db.trips.find(
        {"tenant_id": tenant_id}
    ).sort("created_at", -1).limit(10).to_list(10)
    
    trip_numbers = [t.get("trip_number", f"T{i}") for i, t in enumerate(trips)]
    trip_ids = {t.get("id"): t.get("trip_number") for t in trips}
    
    # Get all invoices that are not fully paid (limit to 5000)
    invoices = await db.invoices.find({
        "tenant_id": tenant_id,
        "status": {"$in": ["draft", "sent", "overdue"]}
    }).to_list(5000)
    
    # Build client statements
    client_statements = []
    total_outstanding = 0
    total_overdue = 0
    
    for client in clients:
        client_id = client.get("id")
        client_invoices = [inv for inv in invoices if inv.get("client_id") == client_id]
        
        if not client_invoices:
            continue
        
        # Calculate total outstanding for this client
        client_total = sum(
            (inv.get("total", 0) - inv.get("paid_amount", 0))
            for inv in client_invoices
        )
        
        if client_total <= 0:
            continue
        
        # Group by trip
        trip_amounts = {}
        for inv in client_invoices:
            trip_id = inv.get("trip_id")
            trip_num = trip_ids.get(trip_id, "Other")
            outstanding = inv.get("total", 0) - inv.get("paid_amount", 0)
            if outstanding > 0:
                trip_amounts[trip_num] = trip_amounts.get(trip_num, 0) + outstanding
        
        # Count overdue
        client_overdue = sum(
            (inv.get("total", 0) - inv.get("paid_amount", 0))
            for inv in client_invoices
            if inv.get("status") == "overdue"
        )
        
        total_outstanding += client_total
        total_overdue += client_overdue
        
        client_statements.append({
            "client_id": client_id,
            "client_name": client.get("name", "Unknown"),
            "client_email": client.get("email"),
            "client_phone": client.get("phone"),
            "total_outstanding": round(client_total, 2),
            "trip_amounts": trip_amounts,
            "invoice_count": len(client_invoices),
            "has_overdue": client_overdue > 0
        })
    
    # Sort by total outstanding (highest first)
    client_statements.sort(key=lambda x: x["total_outstanding"], reverse=True)
    
    return {
        "statements": client_statements,
        "trip_columns": trip_numbers[:8],  # Show last 8 trips
        "summary": {
            "total_outstanding": round(total_outstanding, 2),
            "clients_with_debt": len(client_statements),
            "overdue_amount": round(total_overdue, 2)
        }
    }

@router.get("/finance/client-statements/{client_id}/invoices")
async def get_client_statement_invoices(client_id: str, tenant_id: str = Depends(get_tenant_id)):
    """Get all unpaid/partial invoices for a specific client"""
    invoices = await db.invoices.find({
        "tenant_id": tenant_id,
        "client_id": client_id,
        "status": {"$in": ["draft", "sent", "overdue"]}
    }).sort("created_at", -1).to_list(1000)
    
    # Get trip info for each invoice
    trip_ids = list(set(inv.get("trip_id") for inv in invoices if inv.get("trip_id")))
    trips = await db.trips.find({"id": {"$in": trip_ids}}).to_list(1000)
    trip_map = {t.get("id"): t for t in trips}
    
    result = []
    for inv in invoices:
        trip = trip_map.get(inv.get("trip_id"), {})
        outstanding = inv.get("total", 0) - inv.get("paid_amount", 0)
        result.append({
            "id": inv.get("id"),
            "invoice_number": inv.get("invoice_number"),
            "trip_number": trip.get("trip_number", "-"),
            "total": inv.get("total", 0),
            "paid_amount": inv.get("paid_amount", 0),
            "outstanding": outstanding,
            "due_date": inv.get("due_date"),
            "status": inv.get("status"),
            "created_at": inv.get("created_at")
        })
    
    return result


# ============ FINANCE - TRIP WORKSHEETS ============

@router.get("/finance/trip-worksheet/{trip_id}")
async def get_trip_worksheet(trip_id: str, tenant_id: str = Depends(get_tenant_id)):
    """
    Get invoice breakdown for a specific trip (like the S25 Worksheet PDF).
    """
    # Get trip - use id field instead of _id
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Get all invoices for this trip
    invoices = await db.invoices.find({
        "tenant_id": tenant_id,
        "trip_id": trip_id
    }).to_list(1000)
    
    # Get clients - use id field instead of _id
    client_ids = list(set(inv.get("client_id") for inv in invoices if inv.get("client_id")))
    clients = await db.clients.find({"id": {"$in": client_ids}}).to_list(1000)
    client_map = {c.get("id"): c for c in clients}
    
    # Get shipments for weight info
    shipments = await db.shipments.find({"trip_id": trip_id}).to_list(1000)
    # Map client_id to total weight
    client_weights = {}
    for s in shipments:
        cid = s.get("client_id")
        if cid:
            client_weights[cid] = client_weights.get(cid, 0) + (s.get("total_weight", 0) or 0)
    
    # Build invoice list
    invoice_list = []
    total_revenue = 0
    total_collected = 0
    total_outstanding = 0
    invoices_paid = 0
    
    for inv in invoices:
        client = client_map.get(inv.get("client_id"), {})
        total = inv.get("total", 0)
        paid = inv.get("paid_amount", 0)
        outstanding = total - paid
        weight = client_weights.get(inv.get("client_id"), 0)
        
        total_revenue += total
        total_collected += paid
        total_outstanding += outstanding
        
        if inv.get("status") == "paid":
            invoices_paid += 1
        
        # Determine status for display
        status = inv.get("status", "draft")
        if status == "sent" and inv.get("due_date"):
            try:
                due_str = inv["due_date"]
                if isinstance(due_str, str):
                    if 'T' in due_str:
                        due = datetime.fromisoformat(due_str.replace("Z", "+00:00"))
                    else:
                        due = datetime.fromisoformat(due_str).replace(tzinfo=timezone.utc)
                else:
                    due = due_str
                if due and due.tzinfo is None:
                    due = due.replace(tzinfo=timezone.utc)
                if due < datetime.now(timezone.utc):
                    status = "overdue"
            except (ValueError, TypeError, AttributeError):
                pass
        
        invoice_list.append({
            "id": inv.get("id"),
            "invoice_number": inv.get("invoice_number"),
            "client_id": inv.get("client_id"),
            "client_name": client.get("name", "Unknown"),
            "client_email": client.get("email"),
            "recipient": inv.get("recipient") or client.get("name", "-"),
            "weight_kg": round(weight, 2),
            "total_amount": round(total, 2),
            "paid_amount": round(paid, 2),
            "outstanding": round(outstanding, 2),
            "status": status,
            "due_date": inv.get("due_date"),
            "created_at": inv.get("created_at")
        })
    
    # Sort by client name
    invoice_list.sort(key=lambda x: x["client_name"].lower())
    
    return {
        "trip": {
            "id": trip.get("id"),
            "trip_number": trip.get("trip_number"),
            "status": trip.get("status"),
            "route": trip.get("route", []),
            "departure_date": trip.get("departure_date")
        },
        "summary": {
            "total_revenue": round(total_revenue, 2),
            "total_collected": round(total_collected, 2),
            "total_outstanding": round(total_outstanding, 2),
            "collection_percent": round((total_collected / total_revenue * 100) if total_revenue > 0 else 0, 1),
            "invoices_paid": invoices_paid,
            "invoices_total": len(invoices)
        },
        "invoices": invoice_list
    }


@router.get("/finance/trip-worksheet/{trip_id}/pdf")
async def get_trip_worksheet_pdf(trip_id: str, tenant_id: str = Depends(get_tenant_id)):
    """
    Generate PDF worksheet for a trip with invoice breakdown.
    """
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
    
    # Get trip
    trip = await db.trips.find_one({"id": trip_id, "tenant_id": tenant_id})
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Get all invoices for this trip
    invoices = await db.invoices.find({
        "tenant_id": tenant_id,
        "trip_id": trip_id
    }, {"_id": 0}).to_list(1000)
    
    # Get clients
    client_ids = list(set(inv.get("client_id") for inv in invoices if inv.get("client_id")))
    clients = await db.clients.find({"id": {"$in": client_ids}}, {"_id": 0}).to_list(1000)
    client_map = {c.get("id"): c for c in clients}
    
    # Get shipments for weight info
    shipments = await db.shipments.find({"trip_id": trip_id}, {"_id": 0}).to_list(1000)
    client_weights = {}
    for s in shipments:
        cid = s.get("client_id")
        if cid:
            client_weights[cid] = client_weights.get(cid, 0) + (s.get("total_weight", 0) or 0)
    
    # Calculate totals
    total_revenue = sum(inv.get("total", 0) for inv in invoices)
    total_paid = sum(inv.get("paid_amount", 0) for inv in invoices)
    total_outstanding = total_revenue - total_paid
    
    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=15*mm, rightMargin=15*mm, topMargin=15*mm, bottomMargin=15*mm)
    
    # Define colors
    olive = colors.HexColor('#6B633C')
    dark_gray = colors.HexColor('#3C3F42')
    light_gray = colors.HexColor('#F5F5F5')
    
    # Styles - use unique names to avoid conflicts with getSampleStyleSheet()
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='WorksheetTitle', fontSize=18, fontName='Helvetica-Bold', textColor=olive, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='WorksheetSubtitle', fontSize=12, fontName='Helvetica', textColor=dark_gray, alignment=TA_CENTER))
    styles.add(ParagraphStyle(name='WorksheetSectionTitle', fontSize=11, fontName='Helvetica-Bold', textColor=dark_gray))
    
    elements = []
    
    # Title
    trip_number = trip.get("trip_number", "Unknown")
    elements.append(Paragraph(f"Trip Worksheet: {trip_number}", styles['WorksheetTitle']))
    elements.append(Spacer(1, 3*mm))
    
    # Trip info
    route = " → ".join(trip.get("route", []))
    departure = trip.get("departure_date", "")
    elements.append(Paragraph(f"Route: {route}", styles['WorksheetSubtitle']))
    elements.append(Paragraph(f"Departure: {departure} | Status: {trip.get('status', 'unknown').title()}", styles['WorksheetSubtitle']))
    elements.append(Spacer(1, 8*mm))
    
    # Summary section
    elements.append(Paragraph("Summary", styles['WorksheetSectionTitle']))
    elements.append(Spacer(1, 3*mm))
    
    summary_data = [
        ['Total Revenue', 'Total Collected', 'Outstanding', 'Invoices'],
        [f"R {total_revenue:,.2f}", f"R {total_paid:,.2f}", f"R {total_outstanding:,.2f}", f"{len(invoices)}"]
    ]
    summary_table = Table(summary_data, colWidths=[45*mm, 45*mm, 45*mm, 35*mm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), olive),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 8*mm))
    
    # Invoice details
    elements.append(Paragraph("Invoice Details", styles['WorksheetSectionTitle']))
    elements.append(Spacer(1, 3*mm))
    
    # Invoice table header
    table_data = [['Invoice #', 'Client', 'Weight (kg)', 'Total', 'Paid', 'Outstanding', 'Status']]
    
    # Sort invoices by client name
    sorted_invoices = sorted(invoices, key=lambda x: client_map.get(x.get("client_id"), {}).get("name", "").lower())
    
    for inv in sorted_invoices:
        client = client_map.get(inv.get("client_id"), {})
        weight = client_weights.get(inv.get("client_id"), 0)
        total = inv.get("total", 0)
        paid = inv.get("paid_amount", 0)
        outstanding = total - paid
        status = inv.get("status", "draft").title()
        
        table_data.append([
            inv.get("invoice_number", "-"),
            client.get("name", "Unknown")[:25],
            f"{weight:.1f}",
            f"R {total:,.2f}",
            f"R {paid:,.2f}",
            f"R {outstanding:,.2f}",
            status
        ])
    
    if len(table_data) == 1:
        table_data.append(['-', 'No invoices found', '-', '-', '-', '-', '-'])
    
    invoice_table = Table(table_data, colWidths=[25*mm, 45*mm, 20*mm, 28*mm, 28*mm, 28*mm, 18*mm])
    invoice_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), olive),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    
    # Alternating row colors
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            invoice_table.setStyle(TableStyle([('BACKGROUND', (0, i), (-1, i), light_gray)]))
    
    elements.append(invoice_table)
    elements.append(Spacer(1, 10*mm))
    
    # Footer
    elements.append(Paragraph(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')} | Servex Holdings", 
                              ParagraphStyle(name='Footer', fontSize=8, textColor=colors.gray, alignment=TA_CENTER)))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    filename = f"Worksheet-{trip_number}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============ FINANCE - OVERDUE INVOICES ============

@router.get("/finance/overdue")
async def get_overdue_invoices(tenant_id: str = Depends(get_tenant_id)):
    """Get all overdue invoices sorted by days overdue"""
    now = datetime.now(timezone.utc)
    
    # Get invoices where due_date < now and status is not paid
    invoices = await db.invoices.find({
        "tenant_id": tenant_id,
        "status": {"$in": ["draft", "sent", "overdue"]},
        "due_date": {"$lt": now.isoformat()}
    }).to_list(1000)
    
    # Get clients - use id field instead of _id
    client_ids = list(set(inv.get("client_id") for inv in invoices if inv.get("client_id")))
    clients = await db.clients.find({"id": {"$in": client_ids}}).to_list(1000)
    client_map = {c.get("id"): c for c in clients}
    
    # Get trips - use id field instead of _id
    trip_ids = list(set(inv.get("trip_id") for inv in invoices if inv.get("trip_id")))
    trips = await db.trips.find({"id": {"$in": trip_ids}}).to_list(1000)
    trip_map = {t.get("id"): t for t in trips}
    
    result = []
    for inv in invoices:
        client = client_map.get(inv.get("client_id"), {})
        trip = trip_map.get(inv.get("trip_id"), {})
        
        outstanding = inv.get("total", 0) - inv.get("paid_amount", 0)
        if outstanding <= 0:
            continue
        
        # Calculate days overdue
        due_date = inv.get("due_date")
        if isinstance(due_date, str):
            # Handle ISO format with or without timezone
            try:
                if 'T' in due_date:
                    due = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
                else:
                    # Date-only format like "2025-12-31"
                    due = datetime.fromisoformat(due_date).replace(tzinfo=timezone.utc)
            except (ValueError, TypeError, AttributeError):
                due = None
            if due and due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
        elif due_date:
            due = due_date
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
        else:
            due = None
        
        days_overdue = (now - due).days if due else 0
        
        result.append({
            "id": inv.get("id"),
            "invoice_number": inv.get("invoice_number"),
            "client_id": inv.get("client_id"),
            "client_name": client.get("name", "Unknown"),
            "client_email": client.get("email"),
            "client_whatsapp": client.get("whatsapp") or client.get("phone"),
            "trip_number": trip.get("trip_number", "-"),
            "due_date": due_date,
            "days_overdue": days_overdue,
            "total": inv.get("total", 0),
            "paid_amount": inv.get("paid_amount", 0),
            "outstanding": outstanding
        })
    
    # Sort by days overdue (most overdue first)
    result.sort(key=lambda x: x["days_overdue"], reverse=True)
    
    return {
        "invoices": result,
        "total_overdue": sum(i["outstanding"] for i in result),
        "count": len(result)
    }


# ============ FINANCE - EMAIL INVOICE ============

class EmailInvoiceRequest(BaseModel):
    to: str
    subject: str
    body: str
    attach_pdf: bool = True

@router.post("/invoices/{invoice_id}/send-email")
async def send_invoice_email(
    invoice_id: str,
    request: EmailInvoiceRequest,
    tenant_id: str = Depends(get_tenant_id),
    current_user: dict = Depends(get_current_user)
):
    """
    Send invoice via email with PDF attachment.
    NOTE: This is a placeholder - actual email sending requires SMTP configuration.
    """
    # Get invoice - use id field instead of _id
    invoice = await db.invoices.find_one({"id": invoice_id, "tenant_id": tenant_id})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    # Log the email attempt (even if we can't actually send)
    email_log = {
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "invoice_id": invoice_id,
        "to_email": request.to,
        "subject": request.subject,
        "body": request.body,
        "sent_by": current_user.get("id"),
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "status": "logged"  # Would be "sent" with actual SMTP
    }
    
    # In production, this would use SendGrid or SMTP
    # For now, we just log it
    await db.email_logs.insert_one(email_log)
    
    # Update invoice with email sent info
    await db.invoices.update_one(
        {"id": invoice_id},
        {"$set": {
            "email_sent_at": datetime.now(timezone.utc).isoformat(),
            "email_sent_to": request.to
        }}
    )
    
    # Create audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "tenant_id": tenant_id,
        "user_id": current_user.get("id"),
        "action": "email_sent",
        "table_name": "invoices",
        "record_id": invoice_id,
        "old_value": None,
        "new_value": {"to": request.to, "subject": request.subject},
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Email sent successfully (MOCKED)", "to": request.to}
