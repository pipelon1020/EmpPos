# src/routers/backup.py
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.dependencies import get_db, get_current_user
from src.models.product import Product
from src.models.order import Order, OrderItem
from src.models.user import User
from src.schemas.backup import DatabaseBackup, ImportResult

router = APIRouter(prefix="/backup", tags=["backup"])


def require_admin(current_user: User):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se necesita permiso de administrador"
        )


def run_import(db: Session, backup: DatabaseBackup, replace: bool = False) -> ImportResult:
    has_data = (
        db.query(Product).first() or db.query(Order).first() or db.query(OrderItem).first()
    )
    if has_data and not replace:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La base de datos destino no está vacía. Usa replace=true para reemplazar los datos"
        )

    # Validar integridad antes de tocar la BD
    product_ids = {p.id for p in backup.products}
    order_ids = {o.id for o in backup.orders}

    for item in backup.order_items:
        if item.order_id not in order_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"order_item {item.id} referencia una orden inexistente ({item.order_id})"
            )
        if item.product_id not in product_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"order_item {item.id} referencia un producto inexistente ({item.product_id})"
            )

    try:
        if has_data and replace:
            # Orden inverso por las llaves foráneas
            db.query(OrderItem).delete()
            db.query(Order).delete()
            db.query(Product).delete()
            db.flush()

        db.add_all([Product(**p.model_dump()) for p in backup.products])
        db.add_all([Order(**o.model_dump()) for o in backup.orders])
        db.flush()
        db.add_all([OrderItem(**i.model_dump()) for i in backup.order_items])
        db.flush()

        if db.bind.dialect.name == "postgresql":
            for table in ("products", "orders", "order_items"):
                db.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {table}), 1), "
                    f"(SELECT MAX(id) IS NOT NULL FROM {table}))"
                ))

        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al importar: {e}"
        )

    return ImportResult(
        products=len(backup.products),
        orders=len(backup.orders),
        order_items=len(backup.order_items),
    )


# ---------- Exportar ----------

@router.get("/export", response_model=DatabaseBackup)
def export_database(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    require_admin(current_user)

    return DatabaseBackup(
        exported_at=datetime.now(timezone.utc),
        products=db.query(Product).order_by(Product.id).all(),
        orders=db.query(Order).order_by(Order.id).all(),
        order_items=db.query(OrderItem).order_by(OrderItem.id).all(),
    )


# ---------- Importar pegando el JSON en el body ----------

@router.post("/import", response_model=ImportResult, status_code=status.HTTP_201_CREATED)
def import_database(
    body: DatabaseBackup,
    replace: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    require_admin(current_user)
    return run_import(db, body, replace)


# ---------- Importar subiendo el archivo backup.json ----------

@router.post("/import-file", response_model=ImportResult, status_code=status.HTTP_201_CREATED)
def import_database_file(
    file: UploadFile = File(..., description="Archivo JSON generado por /backup/export"),
    replace: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    require_admin(current_user)

    if not (file.filename or "").lower().endswith(".json"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe ser .json"
        )

    try:
        backup = DatabaseBackup.model_validate_json(file.file.read())
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"El JSON no tiene el formato del backup: {e.errors()}"
        )

    return run_import(db, backup, replace)