from pydantic import BaseModel
from datetime import datetime

class ScanOut(BaseModel):
    id: int
    status: str
    scan_type: str
    started_at: datetime
    completed_at: datetime | None = None
    device_count: int | None = None
    vuln_count: int | None = None
    error_message: str | None = None

    class Config:
        from_attributes = True