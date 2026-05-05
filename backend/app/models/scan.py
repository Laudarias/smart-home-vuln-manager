from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime, timezone
from app.models import Base


class Scan(Base):
    __tablename__ = "scans"

    id            = Column(Integer, primary_key=True, index=True)
    scan_type     = Column(String)   # manual | scheduled | discovery
    status        = Column(String, default="pending")   # pending | running | done | error
    started_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at  = Column(DateTime, nullable=True)
    device_count  = Column(Integer, default=0, nullable=True)
    vuln_count    = Column(Integer, default=0, nullable=True)
    error_message = Column(String, nullable=True)