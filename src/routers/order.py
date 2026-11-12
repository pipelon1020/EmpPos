# src/routers/order.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.dependencies import get_db, get_current_user
from src.models.order import Order, OrderItem
from src.models.user import User
from src.schemas.order import OrderClose, OrderOut

router = APIRouter(prefix="/orders", tags=["orders"])

@router.post("/", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def close_order(data: OrderClose, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not data.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La orden no tiene items")

    # verificar que el total coincida con los items
    calculated_total = sum(item.unit_price * item.quantity for item in data.items)
    if calculated_total != data.total:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El total no coincide con los items")

    order = Order(
        name=data.name,
        payment_type=data.payment_type,
        total=data.total,
    )
    db.add(order)
    db.flush()  # para obtener el id antes del commit

    for item in data.items:
        db_item = OrderItem(
            order_id=order.id,
            product_id=item.product_id,
            product_name=item.product_name,
            unit_price=item.unit_price,
            quantity=item.quantity,
        )
        db.add(db_item)

    db.commit()
    db.refresh(order)
    return order

@router.get("/", response_model=list[OrderOut])
def get_orders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Order).order_by(Order.closed_at.desc()).all()

@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada")
    return order