"""
Modelo de dispositivo.

Campos de identificación enriquecida:
  - manufacturer  → fabricante desde OUI de la MAC (ej. "Apple, Inc.")
  - hostname      → nombre desde DNS/mDNS/NetBIOS (ej. "iphone-de-juan")
  - mdns_name     → nombre anunciado por mDNS/Bonjour (ej. "Living Room TV")
  - netbios_name  → nombre NetBIOS (Windows)
  - os_name       → sistema operativo detectado por nmap -O (ej. "Windows 11")
  - os_accuracy   → confianza de la detección OS en % (ej. 95)
  - device_type   → categoría inferida (router, mobile, computer, smart-home, etc.)
"""
from sqlalchemy import Column, Integer, String, DateTime, JSON
from datetime import datetime, timezone
from app.models import Base


class Device(Base):
    __tablename__ = "devices"

    id           = Column(Integer, primary_key=True, index=True)
    ip           = Column(String, unique=True, nullable=False, index=True)
    mac          = Column(String, nullable=True)

    # Identificación
    manufacturer = Column(String, nullable=True)   # de MAC OUI
    hostname     = Column(String, nullable=True)   # DNS / nmap hostname
    mdns_name    = Column(String, nullable=True)   # mDNS / Bonjour
    netbios_name = Column(String, nullable=True)   # NetBIOS (Windows)

    # Sistema operativo
    os_name      = Column(String, nullable=True)   # ej. "Linux 5.15" / "Windows 11"
    os_accuracy  = Column(Integer, nullable=True)  # confianza en %

    # Tipo de dispositivo (inferido)
    device_type  = Column(String, nullable=True)   # router|mobile|computer|smart-home|tv|printer|nas|unknown

    # Puertos abiertos como lista JSON
    ports        = Column(JSON, default=list)

    # Estado
    status       = Column(String, default="online")   # online | offline
    first_seen   = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen    = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                          onupdate=lambda: datetime.now(timezone.utc))