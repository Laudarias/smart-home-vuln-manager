from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models import get_db
from app.models.scan import Scan
from app.models.device import Device
from app.schemas.scan import ScanOut
from scanner.arp_runner import run_arp_scan
from scanner.nmap_runner import run_nmap

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

        # Correr nmap-scan
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

        # Marcar completitud del escaneo
        scan.status         = "done"
        scan.device_count  = len(arp_results)
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