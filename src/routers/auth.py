# src/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext
from src.dependencies import get_db, get_current_user
from src.models.user import User
from src.schemas.user import UserCreate, UserOut, ChangePassword, ChangeUsername
from src.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_token(username: str, is_admin: bool) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": username,
        "is_admin": is_admin,
        "exp": expire
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)

# --- Login ---

@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos"
        )
    if not user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )
    token = create_token(user.username, user.is_admin)
    return {"access_token": token, "token_type": "bearer", "is_admin": user.is_admin}

# --- Crear usuario (solo admin) ---

@router.post("/users", response_model=UserOut)
def create_user(user: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se necesita permiso de administrador")
    existing = db.query(User).filter(User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El username ya existe")
    new_user = User(
        username=user.username,
        name=user.name,
        password_hash=hash_password(user.password),
        is_admin=user.is_admin,
        active=user.active
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# --- Listar usuarios (solo admin) ---

@router.get("/users", response_model=list[UserOut])
def get_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se necesita permiso de administrador")
    return db.query(User).all()

# --- Activar / desactivar usuario (solo admin) ---

@router.patch("/users/{username}/active")
def toggle_active(username: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se necesita permiso de administrador")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    if user.username == current_user.username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No puedes desactivarte a ti mismo")
    user.active = not user.active
    db.commit()
    return {"username": user.username, "active": user.active}

# --- Cambiar username (cualquier usuario, solo el suyo) ---

@router.patch("/users/username", response_model=UserOut)
def change_username(data: ChangeUsername, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    existing = db.query(User).filter(User.username == data.new_username).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El username ya está en uso")
    current_user.username = data.new_username
    db.commit()
    db.refresh(current_user)
    return current_user

# --- Cambiar contraseña (cualquier usuario, solo la suya) ---

@router.patch("/users/password")
def change_password(data: ChangePassword, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contraseña actual incorrecta")
    current_user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"detail": "Contraseña actualizada"}