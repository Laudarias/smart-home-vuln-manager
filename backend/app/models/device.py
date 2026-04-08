"""
Modelo para representar los dispositivos conectados a la red.
Cada dispositivo tiene:
- dirección IP
- dirección MAC
- fabricante
- nombre de host (si se pudo resolver)
- familia de sistema operativo (si se pudo detectar)
- puertos abiertos y servicios asociados
- estado (online/offline)
- marca de tiempo de la última vez que se vio el dispositivo en la red
"""

from sqlalchemy import Column, Integer, String, DateTime, JSON
from datetime import datetime, timezone
from app.models import Base

class Device(Base):
    __tablename__ = "devices"

    id           = Column(Integer, primary_key=True, index=True)
    ip           = Column(String, unique=True, index=True)
    mac          = Column(String)
    manufacturer = Column(String)
    hostname     = Column(String, nullable=True)
    os_family    = Column(String, nullable=True)
    status      = Column(String, default="online")   # online/offline
    ports       = Column(JSON, nullable=True)    # JSON string con puertos abiertos y servicios
    last_seen    = Column(DateTime, default=lambda: datetime.now(timezone.utc))