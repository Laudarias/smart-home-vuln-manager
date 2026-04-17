from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models import get_db
from app.models.scan import Scan
from app.models.device import Device
from app.models.vulnerability import Vulnerability
from app.schemas.scan import ScanOut
from scanner.arp_runner import run_arp_scan
from scanner.nmap_runner import run_nmap
from scanner.nuclei_runner import run_nuclei

router = APIRouter(prefix="/api/scans", tags=["scans"])

@router.post("/discover", response_model=ScanOut)
def discover_devices(db: Session = Depends(get_db)):
    # Registrar inicio de escaneo (estado, tipo, timestamp)
    scan = Scan(
        status="running",
        scan_type="discovery",
        started_at=datetime.now(timezone.utc)
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    try:
        # Correr arp-scan
        arp_results = run_arp_scan()
        ips = [d["ip"] for d in arp_results]

        # Correr nmap
        nmap_results = run_nmap(ips)

        # Guardar/actualizar dispositivos
        for d in arp_results:
            ip = d["ip"]
            nmap_data = nmap_results.get(ip, {})

            device = db.query(Device).filter(Device.ip == ip).first()
            if device:
                device.mac          = d["mac"]
                device.manufacturer = d["manufacturer"]
                device.hostname     = nmap_data.get("hostname")
                device.os_family    = nmap_data.get("os_family")
                device.ports       = nmap_data.get("ports", [])
                device.last_seen    = datetime.now(timezone.utc)
                device.status       = "online"
            else:
                db.add(Device(
                    ip=d["ip"],
                    mac=d["mac"],
                    manufacturer=d["manufacturer"],
                    hostname=nmap_data.get("hostname"),
                    os_family=nmap_data.get("os_family"),
                    ports=nmap_data.get("ports", []),
                    status="online"
                ))

        db.commit()

        # Correr nuclei
        ips_with_ports = [ip for ip, data in nmap_results.items() if data.get("ports")]
        vuln_count = 0
        nuclei_results = run_nuclei(ips_with_ports)

        # Guardar vulnerabilidades
        for vuln in nuclei_results:
            device = db.query(Device).filter(Device.ip == vuln["ip"]).first()
            if device:
                db.add(Vulnerability(
                    device_id=device.id,
                    template_id=vuln["template_id"],
                    name=vuln["name"],
                    severity=vuln["severity"],
                    description=vuln["description"],
                    matched_at=vuln["matched_at"],
                    cve_id=vuln["cve_id"]
                ))
                vuln_count += 1

        # Marcar completitud del escaneo
        scan.status         = "done"
        scan.device_count  = len(arp_results)
        scan.vuln_count    = vuln_count
        scan.completed_at   = datetime.now(timezone.utc)
        db.commit()
        db.refresh(scan)
        return scan

    except Exception as e:
        scan.status        = "error"
        scan.error_message = str(e)
        scan.completed_at  = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=list[ScanOut])
def get_scans(db: Session = Depends(get_db)):
    return db.query(Scan).order_by(Scan.started_at.desc()).all()