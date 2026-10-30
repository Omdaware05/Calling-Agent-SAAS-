import html as html_lib
import logging
import random
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import verify_app_client
from app.models.invoice import Invoice
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invoices", tags=["invoices"], dependencies=[Depends(verify_app_client)])


class LineItemPayload(BaseModel):
    description: str = Field(default="AI Voice Call Hours")
    quantity: float = Field(default=1.0)
    unit_price: float = Field(default=15.0)


class CreateInvoicePayload(BaseModel):
    business_id: Optional[str] = None
    tax_rate: float = Field(default=18.0)
    notes: Optional[str] = Field(default="Payment terms: Net 30. Remit via Bank Transfer.")
    currency: str = Field(default="USD")
    line_items: List[LineItemPayload] = Field(default_factory=list)


def format_invoice(inv: Invoice) -> Dict[str, Any]:
    return {
        "invoice_id": inv.id,
        "invoice_number": inv.invoice_number,
        "business_id": inv.business_id,
        "status": (inv.status or "ISSUED").upper(),
        "subtotal": round(inv.subtotal or 0.0, 2),
        "tax": round(inv.tax or 0.0, 2),
        "total": round(inv.total or 0.0, 2),
        "currency": inv.currency or "USD",
        "issue_date": inv.issue_date.strftime("%Y-%m-%d") if inv.issue_date else datetime.now(UTC).strftime("%Y-%m-%d"),
        "due_date": inv.due_date.strftime("%Y-%m-%d") if inv.due_date else (datetime.now(UTC) + timedelta(days=30)).strftime("%Y-%m-%d"),
        "notes": inv.notes or "",
        "line_items": inv.line_items or [],
    }


@router.get("")
@router.get("/")
async def list_invoices(
    business_id: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    List invoices for a tenant/business.

    This GET used to FABRICATE two demo invoices (one marked PAID) when a
    business had none — merely opening the Billing page created fake
    financial records, and because the numbers were hard-coded
    (INV-<year>-0101/0102) against a UNIQUE column, opening Billing for a
    second business raised IntegrityError and 500'd that business forever.
    A read endpoint must never write; an empty list is the honest answer.
    """
    b_id = business_id or tenant_id
    query = select(Invoice).order_by(desc(Invoice.created_at))
    if b_id:
        query = query.where(Invoice.business_id == b_id)

    result = await db.execute(query)
    invoices = result.scalars().all()

    return [format_invoice(inv) for inv in invoices]


@router.post("")
@router.post("/")
async def create_invoice(
    payload: CreateInvoicePayload,
    business_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate and save a new invoice record.
    """
    b_id = payload.business_id or business_id
    if not b_id:
        # Fallback to first available tenant
        tenant_res = await db.execute(select(Tenant).limit(1))
        first_tenant = tenant_res.scalars().first()
        b_id = first_tenant.id if first_tenant else "default-tenant"

    processed_items = []
    subtotal = 0.0

    for item in payload.line_items:
        amt = round(float(item.quantity) * float(item.unit_price), 2)
        subtotal += amt
        processed_items.append({
            "description": item.description,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "amount": amt,
        })

    if not processed_items:
        processed_items.append({
            "description": "AI Agent Voice Runtime",
            "quantity": 1,
            "unit_price": 100.0,
            "amount": 100.0,
        })
        subtotal = 100.0

    tax_rate = max(0.0, payload.tax_rate)
    tax = round(subtotal * (tax_rate / 100.0), 2)
    total = round(subtotal + tax, 2)

    # Random numbers in a 9000-space collided with the UNIQUE
    # invoice_number column (birthday effect) -> intermittent 500s.
    # Generate + insert with a retry on conflict.
    from sqlalchemy.exc import IntegrityError

    invoice = None
    for _attempt in range(6):
        inv_num = f"INV-{datetime.now(UTC).year}-{random.randint(1000, 999999)}"
        candidate = Invoice(
        invoice_number=inv_num,
        business_id=b_id,
        status="ISSUED",
        subtotal=subtotal,
        tax=tax,
        total=total,
        currency=payload.currency or "USD",
        issue_date=datetime.now(UTC),
        due_date=datetime.now(UTC) + timedelta(days=30),
        notes=payload.notes or "Payment terms: Net 30.",
        line_items=processed_items,
    )

        try:
            db.add(candidate)
            await db.commit()
        except IntegrityError:
            await db.rollback()
            continue
        invoice = candidate
        break
    if invoice is None:
        raise HTTPException(status_code=500, detail="Could not allocate a unique invoice number")
    await db.refresh(invoice)

    return format_invoice(invoice)


@router.post("/{invoice_id}/mark-paid")
async def mark_invoice_paid(
    invoice_id: str,
    business_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark an invoice as PAID manually.
    """
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    inv = result.scalars().first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    inv.status = "PAID"
    await db.commit()
    await db.refresh(inv)

    return format_invoice(inv)


@router.get("/{invoice_id}/pdf")
async def get_invoice_pdf_html(
    invoice_id: str,
    business_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns an HTML printable invoice with professional styling and print button.
    """
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    inv = result.scalars().first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Fetch business / tenant name
    tenant_name = "Client Business"
    if inv.business_id:
        t_res = await db.execute(select(Tenant).where(Tenant.id == inv.business_id))
        tenant = t_res.scalars().first()
        if tenant:
            tenant_name = tenant.name

    status_color = "#10b981" if inv.status == "PAID" else "#f97316"
    status_label = "PAID IN FULL" if inv.status == "PAID" else "PAYMENT DUE (NET 30)"

    items_html = ""
    for item in (inv.line_items or []):
        desc = html_lib.escape(str(item.get("description", "Item")))
        qty = item.get("quantity", 1)
        rate = item.get("unit_price", 0.0)
        amt = item.get("amount", round(qty * rate, 2))
        items_html += f"""
        <tr style="border-bottom: 1px solid #e2e8f0;">
            <td style="padding: 12px 16px; font-size: 14px; color: #1e293b;">{desc}</td>
            <td style="padding: 12px 16px; font-size: 14px; color: #64748b; text-align: center;">{qty}</td>
            <td style="padding: 12px 16px; font-size: 14px; color: #64748b; text-align: right;">${rate:,.2f}</td>
            <td style="padding: 12px 16px; font-size: 14px; font-weight: 600; color: #0f172a; text-align: right;">${amt:,.2f}</td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Invoice {html_lib.escape(str(inv.invoice_number))}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #f8fafc;
            color: #0f172a;
            margin: 0;
            padding: 40px 20px;
        }}
        .invoice-card {{
            max-width: 800px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01);
            border: 1px solid #e2e8f0;
            padding: 48px;
        }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 2px solid #f1f5f9;
            padding-bottom: 32px;
            margin-bottom: 32px;
        }}
        .brand {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .logo {{
            width: 44px;
            height: 44px;
            background: linear-gradient(135deg, #f97316, #ea580c);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 20px;
        }}
        .brand-title {{
            font-size: 22px;
            font-weight: 800;
            letter-spacing: -0.5px;
            color: #0f172a;
        }}
        .badge {{
            display: inline-block;
            padding: 6px 14px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            background-color: {status_color}1a;
            color: {status_color};
            border: 1px solid {status_color}40;
        }}
        .grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 24px;
            margin-bottom: 36px;
        }}
        .label {{
            font-size: 11px;
            text-transform: uppercase;
            font-weight: 700;
            color: #94a3b8;
            margin-bottom: 4px;
        }}
        .val {{
            font-size: 15px;
            font-weight: 600;
            color: #1e293b;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 32px;
        }}
        th {{
            background: #f8fafc;
            padding: 12px 16px;
            text-align: left;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            color: #64748b;
            border-bottom: 1px solid #e2e8f0;
        }}
        .totals {{
            width: 280px;
            margin-left: auto;
            margin-bottom: 36px;
        }}
        .totals-row {{
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            font-size: 14px;
            color: #64748b;
        }}
        .totals-row.grand {{
            border-top: 2px solid #0f172a;
            margin-top: 8px;
            padding-top: 12px;
            font-size: 18px;
            font-weight: 800;
            color: #0f172a;
        }}
        .notes-box {{
            background: #f8fafc;
            border-radius: 12px;
            padding: 20px;
            font-size: 13px;
            color: #475569;
            border: 1px solid #f1f5f9;
        }}
        .actions {{
            display: flex;
            justify-content: flex-end;
            margin-bottom: 24px;
            max-width: 800px;
            margin: 0 auto 16px auto;
        }}
        .btn-print {{
            background: #0f172a;
            color: #ffffff;
            border: none;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}
        .btn-print:hover {{
            background: #1e293b;
        }}
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .actions {{
                display: none;
            }}
            .invoice-card {{
                box-shadow: none;
                border: none;
                padding: 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="actions">
        <button class="btn-print" onclick="window.print()">🖨️ Print or Save as PDF</button>
    </div>
    <div class="invoice-card">
        <div class="header">
            <div class="brand">
                <div class="logo">⚡</div>
                <div>
                    <div class="brand-title">ARB SoftTech AI</div>
                    <div style="font-size: 12px; color: #64748b;">Autonomous Voice Agent Telephony</div>
                </div>
            </div>
            <div style="text-align: right;">
                <div class="badge">{status_label}</div>
                <div style="font-size: 18px; font-weight: 800; margin-top: 8px; color: #0f172a;">{html_lib.escape(str(inv.invoice_number))}</div>
            </div>
        </div>

        <div class="grid">
            <div>
                <div class="label">Billed To</div>
                <div class="val">{html_lib.escape(str(tenant_name))}</div>
                <div style="font-size: 13px; color: #64748b; margin-top: 4px;">Account ID: {inv.business_id or 'N/A'}</div>
            </div>
            <div style="text-align: right;">
                <div class="label">Invoice Date</div>
                <div class="val">{inv.issue_date.strftime('%B %d, %Y') if inv.issue_date else 'N/A'}</div>
                <div class="label" style="margin-top: 10px;">Due Date</div>
                <div class="val">{inv.due_date.strftime('%B %d, %Y') if inv.due_date else 'N/A'}</div>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Description</th>
                    <th style="text-align: center;">Qty / Hrs</th>
                    <th style="text-align: right;">Unit Rate</th>
                    <th style="text-align: right;">Total Amount</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
        </table>

        <div class="totals">
            <div class="totals-row">
                <span>Subtotal</span>
                <span>${inv.subtotal:,.2f}</span>
            </div>
            <div class="totals-row">
                <span>Tax</span>
                <span>${inv.tax:,.2f}</span>
            </div>
            <div class="totals-row grand">
                <span>Total Due</span>
                <span>${inv.total:,.2f} {inv.currency}</span>
            </div>
        </div>

        <div class="notes-box">
            <strong>Notes & Remittance:</strong><br>
            {html_lib.escape(str(inv.notes or "Payment terms: Net 30. Remit via Bank Transfer directly to our designated billing account."))}
        </div>
    </div>
</body>
</html>
"""
    return HTMLResponse(content=html, status_code=200)
