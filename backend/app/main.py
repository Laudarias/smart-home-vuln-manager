from fastapi import FastAPI
from app.models import Base, engine
from app.models.device import Device
from app.models.scan import Scan
from app.api.scans import router as scans_router

app = FastAPI(title="Smart Home Vulnerability Manager")

@app.on_event("startup")
def startup():
    # Crear las tablas en la base de datos si no existen
    Base.metadata.create_all(bind=engine)

# Incluir router de escaneos    
app.include_router(scans_router)

@app.get("/api/health")
def health_check():
    return {"status": "ok"}