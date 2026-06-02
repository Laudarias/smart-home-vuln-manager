from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database import Base

class Scan(Base):
    __tablename__ = "scans"
    id            = Column(Integer, primary_key=True, index=True)
    status        = Column(String, default="running")
    scan_type     = Column(String, default="full")
    devices_found = Column(Integer, default=0)
    vulns_found   = Column(Integer, default=0)
    started_at    = Column(DateTime, server_default=func.now())
    completed_at  = Column(DateTime)
    error_message = Column(String)