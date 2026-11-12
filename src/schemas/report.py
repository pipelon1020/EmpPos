# src/models/report.py
from datetime import date
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator


# ---------- Requests (body JSON) ----------

class PeriodRequest(BaseModel):
    period: Literal["daily", "weekly", "monthly"] = "daily"


class TopProductsRequest(BaseModel):
    period: Literal["daily", "weekly", "monthly"] = "monthly"
    limit: int = Field(default=10, ge=1, le=50)


class DailyBreakdownRequest(BaseModel):
    period: Literal["weekly", "monthly"] = "monthly"


class DateRangeRequest(BaseModel):
    date_from: date
    date_to: date

    @model_validator(mode="after")
    def validate_range(self):
        if self.date_from > self.date_to:
            raise ValueError("date_from no puede ser mayor que date_to")
        return self


# ---------- Responses ----------

class SummaryResponse(BaseModel):
    period: str
    from_: str = Field(alias="from")
    to: str
    total_revenue: float
    total_orders: int
    by_payment_type: Dict[str, float]

    model_config = {"populate_by_name": True}


class TopProduct(BaseModel):
    product_id: int
    product_name: str
    total_quantity: int
    total_revenue: float


class DayTotals(BaseModel):
    total_revenue: float
    total_orders: int


class DailyBreakdownResponse(BaseModel):
    period: str
    breakdown: Dict[str, DayTotals]


class DailySales(BaseModel):
    date: str
    total_revenue: float
    total_orders: int
    by_payment_type: Dict[str, float]


class SalesReport(BaseModel):
    date_from: str
    date_to: str
    total_revenue: float
    total_orders: int
    average_ticket: float
    by_payment_type: Dict[str, float]
    sales: List[DailySales]