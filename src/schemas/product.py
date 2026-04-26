from pydantic import BaseModel, Field

class Product(BaseModel):
    name: str = Field(min_length=2)
    price: int= Field(gt= 99)
    active: bool = True   

    model_config= {
        "json_schema_extra": {
            "example": {
                    "name": "Empanadas",
                    "price": 3700,
                    "active": True

            }
        }
    }

class ProductUpdate(BaseModel):            # para editar 
    name: str | None = Field(default=None, min_length=2)
    price: int | None = Field(default=None, gt=99)
    active: bool | None = None

class ProductOut(BaseModel):
    id: int
    name: str
    price: int
    active: bool

    model_config = {"from_attributes": True}