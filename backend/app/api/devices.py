from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models.device import Device
from app.models.vulnerability import Vulnerability
from app.auth import get_current_user

router = APIRouter(prefix="/api/devices", tags=["devices"])

SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

@router.get("/")
def list_devices(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Lista todos los dispositivos con sus vulnerabilidades abiertas."""
    devices = db.query(Device).all()
    result = []

    for device in devices:
        # Obtener vulnerabilidades abiertas
        vulns = db.query(Vulnerability).filter(
            Vulnerability.device_id == device.id,
            Vulnerability.status == "open"
        ).all()

        # Ordenar por severidad
        vulns_sorted = sorted(vulns, key=lambda v: SEVERITY_ORDER.get(v.severity or "info", 999))

        # Contar por severidad
        vuln_summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for v in vulns:
            sev = v.severity or "info"
            if sev in vuln_summary:
                vuln_summary[sev] += 1

        result.append({
            "id": device.id,
            "ip": device.ip,
            "mac": device.mac,
            "manufacturer": device.manufacturer,
            "hostname": device.hostname,
            "mdns_name": device.mdns_name,
            "netbios_name": device.netbios_name,
            "display_name": device.display_name or device.ip,
            "os_family": device.os_family,
            "os_name": device.os_name,
            "os_accuracy": device.os_accuracy,
            "device_type": device.device_type,
            "ports": device.ports,
            "status": device.status,
            "last_seen": device.last_seen,
            "vulnerabilities": [
                {
                    "id": v.id,
                    "cve_id": v.cve_id,
                    "severity": v.severity,
                    "cvss_score": v.cvss_score,
                    "title": v.title,
                    "description": v.description,
                    "solution": v.solution,
                    "references": v.references,
                    "status": v.status,
                    "found_at": v.found_at,
                    "resolved_at": v.resolved_at,
                }
                for v in vulns_sorted
            ],
            "vuln_summary": vuln_summary,
        })

    return result

@router.get("/{id}")
def get_device(id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """Obtiene el detalle de un dispositivo con todas sus vulnerabilidades."""
    device = db.query(Device).filter(Device.id == id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    # Todas las vulnerabilidades (abiertas y resueltas)
    vulns = db.query(Vulnerability).filter(Vulnerability.device_id == id).all()

    return {
        "id": device.id,
        "ip": device.ip,
        "mac": device.mac,
        "manufacturer": device.manufacturer,
        "hostname": device.hostname,
        "mdns_name": device.mdns_name,
        "netbios_name": device.netbios_name,
        "display_name": device.display_name or device.ip,
        "os_family": device.os_family,
        "os_name": device.os_name,
        "os_accuracy": device.os_accuracy,
        "device_type": device.device_type,
        "ports": device.ports,
        "status": device.status,
        "last_seen": device.last_seen,
        "vulnerabilities": [
            {
                "id": v.id,
                "cve_id": v.cve_id,
                "severity": v.severity,
                "cvss_score": v.cvss_score,
                "title": v.title,
                "description": v.description,
                "solution": v.solution,
                "references": v.references,
                "status": v.status,
                "found_at": v.found_at,
                "resolved_at": v.resolved_at,
            }
            for v in vulns
        ],
    }

@router.post("/{device_id}/vulnerabilities/{vuln_id}/resolve")
def resolve_vuln(
    device_id: int,
    vuln_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Marca una vulnerabilidad como resuelta."""
    vuln = db.query(Vulnerability).filter(
        Vulnerability.id == vuln_id,
        Vulnerability.device_id == device_id
    ).first()

    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerabilidad no encontrada")

    vuln.status = "resolved"
    vuln.resolved_at = datetime.utcnow()
    db.commit()

    return {"message": "Vulnerabilidad marcada como resuelta"}
