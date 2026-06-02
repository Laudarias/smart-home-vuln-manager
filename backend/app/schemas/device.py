from pydantic import BaseModel
from datetime import datetime
from typing import Any

class DeviceOut(BaseModel):
    id: int
    ip: str
    mac: str | None = None
    manufacturer: str | None = None
    hostname: str | None = None
    os_family: str | None = None
    status: str
    ports: list[Any] | None = None
    last_seen: datetime

    class Config:
        from_attributes = True