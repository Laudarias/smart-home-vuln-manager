# backend/app/main.py
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.models import create_tables
from app.auth import get_or_create_user
from app.database import SessionLocal
from app.config import DEFAULT_SCAN_INTERVAL_MINUTES
from app.api.auth import router as auth_router
from app.api.devices import router as devices_router
from app.api.scans import router as scans_router
import scanner.continuous_scanner as cs

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Directorio del build del frontend (relativo a la raíz del proyecto)
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


# ── Lifespan (startup / shutdown) ────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Iniciando smart-home-vuln-manager…")
    create_tables()

    # Crear usuario por defecto si no existe
    db = SessionLocal()
    try:
        user = get_or_create_user(db)
        if user.is_default_password:
            logger.warning(
                "⚠️  Contraseña por defecto activa (admin123). "
                "Cámbiala desde la interfaz lo antes posible."
            )
    finally:
        db.close()

    cs.start_scheduler(DEFAULT_SCAN_INTERVAL_MINUTES)

    yield  # ← la app está corriendo

    # Shutdown
    cs.stop_scheduler()
    logger.info("Servidor detenido.")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Smart Home Vulnerability Manager",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — permite que el frontend (dev server Vite en :5173 y Electron) llame a la API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(devices_router)
app.include_router(scans_router)


# ── Health check ───────────────────────────────────────────────────
@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok"}


# ── Servir el frontend React estático ────────────────────────────────────────
if FRONTEND_DIST.exists():
    # Archivos estáticos (JS, CSS, imágenes)
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        """Ruta catch-all: sirve index.html para que React Router funcione."""
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return {"detail": "Frontend no compilado. Ejecuta 'npm run build' en /frontend."}
else:
    logger.warning(
        f"Frontend build no encontrado en {FRONTEND_DIST}. "
        "Ejecuta 'npm run build' en la carpeta frontend/ para compilarlo."
    )