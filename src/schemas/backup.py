# src/schemas/backup.py
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from src.schemas.order import PaymentType


class ProductBackup(BaseModel):
    id: int
    name: str
    price: int
    active: bool = True

    model_config = {"from_attributes": True}


class OrderBackup(BaseModel):
    id: int
    name: str
    payment_type: PaymentType
    total: int
    closed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class OrderItemBackup(BaseModel):
    id: int
    order_id: int
    product_id: int
    product_name: str
    unit_price: int
    quantity: int

    model_config = {"from_attributes": True}


class DatabaseBackup(BaseModel):
    exported_at: Optional[datetime] = None
    products: List[ProductBackup]
    orders: List[OrderBackup]
    order_items: List[OrderItemBackup]


class ImportResult(BaseModel):
    products: int
    orders: int
    order_items: int