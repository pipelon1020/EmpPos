
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.dependencies import get_db, get_current_user
from src.models.product import Product as Product_Bd
from src.schemas.product import Product, ProductUpdate, ProductOut
from src.models.user import User

router = APIRouter(prefix="/products", tags=["products"])

# --- Obtener todos los productos activos ---

@router.get("/", response_model=list[ProductOut])
def get_productos(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Product_Bd).filter(Product_Bd.active == True).all()

# --- Obtener todos incluyendo inactivos (solo admin) ---

@router.get("/todos", response_model=list[ProductOut])
def get_todos(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se necesita permiso de administrador")
    return db.query(Product_Bd).all()

# --- Crear producto ---

@router.post("/", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_producto(product: Product, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    nuevo = Product_Bd(
        name=product.name,
        price=product.price,
        active=product.active
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo

# --- Editar producto ---

@router.patch("/{product_id}", response_model=ProductOut)
def update_producto(product_id: int, data: ProductUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = db.query(Product_Bd).filter(Product_Bd.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    if data.name is not None:
        product.name = data.name
    if data.price is not None:
        product.price = data.price
    if data.active is not None:
        product.active = data.active
    db.commit()
    db.refresh(product)
    return product

# --- Eliminar producto ---

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_producto(product_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se necesita permiso de administrador")
    product = db.query(Product_Bd).filter(Product_Bd.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    db.delete(product)
    db.commit()