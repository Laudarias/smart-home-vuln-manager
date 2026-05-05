from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import get_db
from app.models.device import Device
from app.models.vulnerability import Vulnerability
from app.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.get("/")
def get_devices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    devices = db.query(Device).all()
    result = []
    for d in devices:
        # Contar vulnerabilidades por severidad para este dispositivo
        vuln_counts = (
            db.query(Vulnerability.severity, func.count(Vulnerability.id))
            .filter(Vulnerability.device_id == d.id)
            .group_by(Vulnerability.severity)
            .all()
        )
        counts = {sev: cnt for sev, cnt in vuln_counts}

        result.append({
            "id":            d.id,
            "ip":            d.ip,
            "mac":           d.mac,
            "manufacturer":  d.manufacturer,
            "hostname":      d.hostname,
            "mdns_name":     d.mdns_name,
            "netbios_name":  d.netbios_name,
            "os_name":       d.os_name,
            "os_accuracy":   d.os_accuracy,
            "device_type":   d.device_type,
            "ports":         d.ports,
            "status":        d.status,
            "first_seen":    d.first_seen.isoformat() if d.first_seen else None,
            "last_seen":     d.last_seen.isoformat() if d.last_seen else None,
            # Resumen de vulnerabilidades
            "vuln_critical": counts.get("critical", 0),
            "vuln_high":     counts.get("high", 0),
            "vuln_medium":   counts.get("medium", 0),
            "vuln_low":      counts.get("low", 0),
            "vuln_total":    sum(counts.values()),
        })
    return result


@router.get("/{device_id}")
def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado.")
    return device


@router.get("/{device_id}/vulnerabilities")
def get_device_vulnerabilities(
    device_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Vulnerability)
        .filter(Vulnerability.device_id == device_id)
        .order_by(Vulnerability.found_at.desc())
        .all()
    )