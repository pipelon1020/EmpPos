from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from src.routers import auth, product, order, report
from src.database import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Empanadas POS")

app.include_router(auth.router)
app.include_router(product.router)
app.include_router(order.router)
app.include_router(report.router)

app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

#uvicorn main:app --reload