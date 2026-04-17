from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models import get_db
from app.models.device import Device
from app.models.vulnerability import Vulnerability
from app.schemas.device import DeviceOut
from app.schemas.vulnerability import VulnerabilityOut

router = APIRouter(prefix="/api/devices", tags=["devices"])

@router.get("/", response_model=list[DeviceOut])
def get_devices(db: Session = Depends(get_db)):
    return db.query(Device).all()

@router.get("/{device_id}", response_model=DeviceOut)
def get_device(device_id: int, db: Session = Depends(get_db)):
    return db.query(Device).filter(Device.id == device_id).first()

@router.get("/{device_id}/vulnerabilities", response_model=list[VulnerabilityOut])
def get_device_vulnerabilities(device_id: int, db: Session = Depends(get_db)):
    return db.query(Vulnerability).filter(Vulnerability.device_id == device_id).order_by(Vulnerability.found_at.desc()).all()