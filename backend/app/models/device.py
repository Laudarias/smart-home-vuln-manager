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
from sqlalchemy.sql import func
from app.database import Base


class Device(Base):
    __tablename__ = "devices"

    id           = Column(Integer, primary_key=True, index=True)
    ip           = Column(String, unique=True, index=True)
    mac          = Column(String)
    manufacturer = Column(String)
    hostname     = Column(String)
    mdns_name    = Column(String)
    netbios_name = Column(String)
    display_name = Column(String)
    os_family    = Column(String)
    os_name      = Column(String)
    os_accuracy  = Column(Integer)
    device_type  = Column(String)
    ports        = Column(JSON)
    status       = Column(String, default="active")
    last_seen    = Column(DateTime, server_default=func.now(), onupdate=func.now())