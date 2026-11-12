# src/routers/report.py
from datetime import datetime, timedelta, timezone, date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from src.dependencies import get_db, get_current_user
from src.models.order import Order, OrderItem
from src.models.user import User

from src.schemas.report import (
    PeriodRequest,
    TopProductsRequest,
    DailyBreakdownRequest,
    DateRangeRequest,
    SummaryResponse,
    TopProduct,
    DailyBreakdownResponse,
    DailySales,
    SalesReport,
)

router = APIRouter(prefix="/reports", tags=["reports"])


# ---------- Helpers ----------

def require_admin(current_user: User):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se necesita permiso de administrador"
        )

def get_date_range(period: str):
    now = datetime.now(timezone.utc)
    if period == "daily":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "weekly":
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    else:  # monthly
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, now


def to_datetime_range(date_from: date, date_to: date):
    start = datetime.combine(date_from, datetime.min.time()).replace(tzinfo=timezone.utc)
    end = datetime.combine(date_to, datetime.max.time()).replace(tzinfo=timezone.utc)
    return start, end


# ---------- Resumen de ganancias por período ----------

@router.post("/summary", response_model=SummaryResponse, response_model_by_alias=True)
def get_summary(
    body: PeriodRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    require_admin(current_user)

    start, end = get_date_range(body.period)

    orders = db.query(Order).filter(Order.closed_at >= start, Order.closed_at <= end).all()

    total_revenue = sum(o.total for o in orders)

    by_payment = {}
    for order in orders:
        key = order.payment_type.value
        by_payment[key] = by_payment.get(key, 0) + order.total

    return {
        "period": body.period,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "total_revenue": total_revenue,
        "total_orders": len(orders),
        "by_payment_type": by_payment
    }


# ---------- Productos más vendidos ----------

@router.post("/top-products", response_model=list[TopProduct])
def get_top_products(
    body: TopProductsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    require_admin(current_user)

    start, end = get_date_range(body.period)

    results = (
        db.query(
            OrderItem.product_id,
            OrderItem.product_name,
            func.sum(OrderItem.quantity).label("total_quantity"),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("total_revenue")
        )
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.closed_at >= start, Order.closed_at <= end)
        .group_by(OrderItem.product_id, OrderItem.product_name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(body.limit)
        .all()
    )

    return [
        {
            "product_id": r.product_id,
            "product_name": r.product_name,
            "total_quantity": r.total_quantity,
            "total_revenue": r.total_revenue
        }
        for r in results
    ]


# ---------- Ventas por día dentro de un período ----------

@router.post("/daily-breakdown", response_model=DailyBreakdownResponse)
def get_daily_breakdown(
    body: DailyBreakdownRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    require_admin(current_user)

    start, end = get_date_range(body.period)

    orders = db.query(Order).filter(Order.closed_at >= start, Order.closed_at <= end).all()

    breakdown = {}
    for order in orders:
        day = order.closed_at.strftime("%Y-%m-%d")
        if day not in breakdown:
            breakdown[day] = {"total_revenue": 0, "total_orders": 0}
        breakdown[day]["total_revenue"] += order.total
        breakdown[day]["total_orders"] += 1

    return {"period": body.period, "breakdown": breakdown}


# ---------- Reporte por rango de fechas (día por día) ----------

@router.post("/by-date", response_model=SalesReport)
def get_report_by_date(
    body: DateRangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    require_admin(current_user)

    start, end = to_datetime_range(body.date_from, body.date_to)

    orders = (
        db.query(Order)
        .filter(Order.closed_at >= start, Order.closed_at <= end)
        .order_by(Order.closed_at)
        .all()
    )

    days = {}
    by_payment_total = {}
    total_revenue = 0.0

    for order in orders:
        day = order.closed_at.strftime("%Y-%m-%d")
        payment = order.payment_type.value

        if day not in days:
            days[day] = {
                "date": day,
                "total_revenue": 0.0,
                "total_orders": 0,
                "by_payment_type": {}
            }

        days[day]["total_revenue"] += order.total
        days[day]["total_orders"] += 1
        days[day]["by_payment_type"][payment] = (
            days[day]["by_payment_type"].get(payment, 0) + order.total
        )

        by_payment_total[payment] = by_payment_total.get(payment, 0) + order.total
        total_revenue += order.total

    total_orders = len(orders)

    # Incluir días sin ventas con valor 0
    sales = []
    current = body.date_from
    while current <= body.date_to:
        key = current.strftime("%Y-%m-%d")
        sales.append(
            DailySales(**days[key]) if key in days
            else DailySales(date=key, total_revenue=0.0, total_orders=0, by_payment_type={})
        )
        current += timedelta(days=1)

    return SalesReport(
        date_from=body.date_from.isoformat(),
        date_to=body.date_to.isoformat(),
        total_revenue=total_revenue,
        total_orders=total_orders,
        average_ticket=round(total_revenue / total_orders, 2) if total_orders else 0.0,
        by_payment_type=by_payment_total,
        sales=sales
    )

#Consulta por filtro de dias 
@router.post("/invoices-by-date", response_model=list)
def get_invoices_by_date(
    body: DateRangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    require_admin(current_user)

    # Convertimos las fechas de inicio y fin a objetos datetime con zona horaria UTC
    start, end = to_datetime_range(body.date_from, body.date_to)

    # Consultamos las órdenes filtradas por el rango de fechas
    orders = (
        db.query(Order)
        .filter(Order.closed_at >= start, Order.closed_at <= end)
        .order_by(Order.closed_at.desc())
        .all()
    )

    invoices_detail = []
    for order in orders:
        items = []
        for item in order.items:  # Asumiendo que la relación en tu modelo Order se llama 'items'
            items.append({
                "product_id": item.product_id,
                "product_name": item.product_name,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "subtotal": item.quantity * item.unit_price
            })
        
        invoices_detail.append({
            "order_id": order.id,
            "order_name": order.name,
            "payment_type": order.payment_type.value,
            "total": order.total,
            "closed_at": order.closed_at.isoformat() if order.closed_at else None,
            "items": items
        })

    return invoices_detail