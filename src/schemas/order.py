from pydantic import BaseModel, Field, model_validator, computed_field
from datetime import datetime
from enum import Enum

class PaymentType(str, Enum):
    efectivo = "efectivo"
    nequi = "nequi"
    daviplata = "daviplata"

class OrderItemIn(BaseModel):
    product_id: int
    product_name: str
    unit_price: int
    quantity: int = Field(gt=0)

class OrderClose(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    items: list[OrderItemIn]
    payment_type: PaymentType
    total: int = Field(gt=0)
    amount_received: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_payment(self):
        if self.payment_type != PaymentType.efectivo:
            self.amount_received = self.total
        else:
            if self.amount_received < self.total:
                raise ValueError("El monto recibido no puede ser menor al total")
        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Orden 1",
                "items": [
                    {"product_id": 1, "product_name": "Empanada carne", "unit_price": 2500, "quantity": 3},
                    {"product_id": 3, "product_name": "Gaseosa", "unit_price": 2000, "quantity": 2}
                ],
                "payment_type": "efectivo",
                "total": 11500,
                "amount_received": 20000
            }
        }
    }

class OrderItemOut(BaseModel):
    product_id: int
    product_name: str
    unit_price: int
    quantity: int

    @computed_field
    @property
    def subtotal(self) -> int:
        return self.unit_price * self.quantity

    model_config = {"from_attributes": True}

class OrderOut(BaseModel):
    id: int
    name: str
    items: list[OrderItemOut]
    payment_type: PaymentType
    total: int
    closed_at: datetime

    model_config = {"from_attributes": True}