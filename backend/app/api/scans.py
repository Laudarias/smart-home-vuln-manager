"""
Pipeline completo:
  1. arp-scan            → descubrir IPs + MACs
  2. mDNS / SSDP         → nombres y tipos de dispositivos (en paralelo con nmap)
  3. MAC OUI             → fabricante
  4. nmap -sV -O         → puertos, versiones, OS
  5. NetBIOS / DNS inv.  → nombres adicionales
  6. Nuclei              → vulnerabilidades CVE con CVSS
"""
import threading
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models import get_db
from app.models.scan import Scan
from app.models.device import Device
from app.models.vulnerability import Vulnerability
from app.schemas.scan import ScanOut
from app.auth import get_current_user
from app.models.user import User
from scanner.arp_runner import run_arp_scan
from scanner.nmap_runner import run_nmap
from scanner.nuclei_runner import run_nuclei
from scanner.device_identifier import (
    get_manufacturer,
    get_reverse_dns,
    get_netbios_name,
    discover_mdns_devices,
    discover_ssdp_devices,
    infer_device_type,
)
from scanner.continuous_scanner import update_interval, get_next_scan_time

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/scans", tags=["scans"])

# Lock para evitar escaneos simultáneos
_scan_lock = threading.Lock()


# ── Schemas ──────────────────────────────────────────────────────────────────

class ScanSettings(BaseModel):
    scan_interval_minutes: int


# ── Pipeline principal ───────────────────────────────────────────────────────

def run_full_scan(scan_type: str = "manual", db: Session | None = None):
    """
    Ejecuta el pipeline completo de escaneo.
    Puede llamarse desde la API (manual) o desde el scheduler (scheduled).
    """
    if not _scan_lock.acquire(blocking=False):
        raise RuntimeError("Ya hay un escaneo en curso. Por favor espera.")

    # Si no se pasa una sesión, crear una propia
    _own_db = db is None
    if _own_db:
        from app.models import SessionLocal
        db = SessionLocal()

    scan = Scan(
        status="running",
        scan_type=scan_type,
        started_at=datetime.now(timezone.utc),
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    try:
        # ── 1. arp-scan ────────────────────────────────────────────────────
        logger.info("Fase 1: arp-scan")
        arp_results = run_arp_scan()
        if not arp_results:
            scan.status      = "done"
            scan.device_count = 0
            scan.vuln_count  = 0
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()
            return scan

        ips = [d["ip"] for d in arp_results]

        # ── 2. mDNS + SSDP (en hilo paralelo con nmap) ────────────────────
        logger.info("Fase 2: mDNS + SSDP")
        mdns_map: dict[str, str] = {}
        ssdp_map: dict[str, dict] = {}

        def _passive_discover():
            nonlocal mdns_map, ssdp_map
            mdns_map = discover_mdns_devices()
            ssdp_map = discover_ssdp_devices()

        passive_thread = threading.Thread(target=_passive_discover)
        passive_thread.start()

        # ── 3. nmap ────────────────────────────────────────────────────────
        logger.info("Fase 3: nmap")
        nmap_results = run_nmap(ips)

        passive_thread.join(timeout=20)  # esperar mDNS/SSDP máximo 20s

        # ── 4. Guardar/actualizar dispositivos ─────────────────────────────
        logger.info("Fase 4: enriquecimiento y guardado de dispositivos")
        for d in arp_results:
            ip  = d["ip"]
            mac = d["mac"]
            nmap_data = nmap_results.get(ip, {})
            ports     = nmap_data.get("ports", [])

            # Fabricante desde MAC OUI
            manufacturer = d.get("manufacturer") or get_manufacturer(mac) or None

            # Nombre del dispositivo (prioridad: mDNS > nmap hostname > NetBIOS > DNS)
            mdns_name    = mdns_map.get(ip)
            hostname     = nmap_data.get("hostname") or get_reverse_dns(ip)
            netbios_name = get_netbios_name(ip)

            # OS
            os_name      = nmap_data.get("os_name")
            os_accuracy  = nmap_data.get("os_accuracy")

            # Tipo de dispositivo
            ssdp_type    = ssdp_map.get(ip, {}).get("type")
            device_type  = infer_device_type(manufacturer, os_name, ports, ssdp_type)

            device = db.query(Device).filter(Device.ip == ip).first()
            if device:
                device.mac          = mac
                device.manufacturer = manufacturer
                device.hostname     = hostname
                device.mdns_name    = mdns_name
                device.netbios_name = netbios_name
                device.os_name      = os_name
                device.os_accuracy  = os_accuracy
                device.device_type  = device_type
                device.ports        = ports
                device.status       = "online"
                device.last_seen    = datetime.now(timezone.utc)
            else:
                db.add(Device(
                    ip=ip,
                    mac=mac,
                    manufacturer=manufacturer,
                    hostname=hostname,
                    mdns_name=mdns_name,
                    netbios_name=netbios_name,
                    os_name=os_name,
                    os_accuracy=os_accuracy,
                    device_type=device_type,
                    ports=ports,
                    status="online",
                ))

        # Marcar como offline los dispositivos que no aparecieron en este escaneo
        db.query(Device).filter(Device.ip.notin_(ips)).update(
            {"status": "offline"}, synchronize_session=False
        )
        db.commit()

        # ── 5. Nuclei ──────────────────────────────────────────────────────
        logger.info("Fase 5: Nuclei")
        ips_with_ports = [ip for ip, data in nmap_results.items() if data.get("ports")]
        nuclei_results = run_nuclei(ips_with_ports)

        vuln_count = 0
        for vuln in nuclei_results:
            device = db.query(Device).filter(Device.ip == vuln["ip"]).first()
            if device:
                db.add(Vulnerability(
                    device_id=device.id,
                    scan_id=scan.id,
                    template_id=vuln["template_id"],
                    cve_id=vuln["cve_id"],
                    name=vuln["name"],
                    severity=vuln["severity"],
                    cvss_score=vuln["cvss_score"],
                    description=vuln["description"],
                    matched_at=vuln["matched_at"],
                    solution=vuln["solution"],
                    references=vuln["references"],
                ))
                vuln_count += 1

        # ── 6. Finalizar escaneo ───────────────────────────────────────────
        scan.status      = "done"
        scan.device_count = len(arp_results)
        scan.vuln_count  = vuln_count
        scan.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(scan)
        logger.info(f"Escaneo completado: {len(arp_results)} dispositivos, {vuln_count} vulnerabilidades.")
        return scan

    except Exception as e:
        logger.exception("Error durante el escaneo")
        scan.status       = "error"
        scan.error_message = str(e)
        scan.completed_at  = datetime.now(timezone.utc)
        db.commit()
        raise

    finally:
        _scan_lock.release()
        if _own_db:
            db.close()


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/discover", response_model=ScanOut)
def discover(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lanza un escaneo completo de la red de forma manual."""
    try:
        scan = run_full_scan(scan_type="manual", db=db)
        return scan
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=list[ScanOut])
def get_scans(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(Scan).order_by(Scan.started_at.desc()).limit(50).all()


@router.get("/status")
def scan_status(current_user: User = Depends(get_current_user)):
    """Informa si hay un escaneo en curso y cuándo es el próximo escaneo automático."""
    return {
        "scanning": _scan_lock.locked(),
        "next_scheduled_scan": get_next_scan_time(),
    }


@router.post("/settings")
def update_settings(
    body: ScanSettings,
    current_user: User = Depends(get_current_user),
):
    """Cambia el intervalo de escaneo automático (0 = desactivar)."""
    update_interval(body.scan_interval_minutes)
    return {
        "message": f"Intervalo actualizado a {body.scan_interval_minutes} minutos.",
        "next_scheduled_scan": get_next_scan_time(),
    }