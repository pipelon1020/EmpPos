# src/routers/report.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from src.dependencies import get_db, get_current_user
from src.models.order import Order, OrderItem
from src.models.user import User

router = APIRouter(prefix="/reports", tags=["reports"])

def get_date_range(period: str):
    now = datetime.now(timezone.utc)
    if period == "daily":
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "weekly":
        start = now - timedelta(days=now.weekday())
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "monthly":
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start, now

# --- Resumen de ganancias por período ---

@router.get("/summary")
def get_summary(
    period: str = Query(default="daily", pattern="^(daily|weekly|monthly)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    start, end = get_date_range(period)

    orders = db.query(Order).filter(Order.closed_at >= start, Order.closed_at <= end).all()

    total_revenue = sum(o.total for o in orders)
    total_orders = len(orders)

    by_payment = {}
    for order in orders:
        key = order.payment_type.value
        by_payment[key] = by_payment.get(key, 0) + order.total

    return {
        "period": period,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "by_payment_type": by_payment
    }

# --- Productos más vendidos ---

@router.get("/top-products")
def get_top_products(
    period: str = Query(default="monthly", pattern="^(daily|weekly|monthly)$"),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    start, end = get_date_range(period)

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
        .limit(limit)
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

# --- Ventas por día dentro de un período ---

@router.get("/daily-breakdown")
def get_daily_breakdown(
    period: str = Query(default="monthly", pattern="^(weekly|monthly)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    start, end = get_date_range(period)

    orders = db.query(Order).filter(Order.closed_at >= start, Order.closed_at <= end).all()

    breakdown = {}
    for order in orders:
        day = order.closed_at.strftime("%Y-%m-%d")
        if day not in breakdown:
            breakdown[day] = {"total_revenue": 0, "total_orders": 0}
        breakdown[day]["total_revenue"] += order.total
        breakdown[day]["total_orders"] += 1

    return {"period": period, "breakdown": breakdown}
