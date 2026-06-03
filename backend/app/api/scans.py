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

from app.database import get_db, SessionLocal
from app.models.scan import Scan
from app.models.device import Device
from app.models.vulnerability import Vulnerability
from app.auth import get_current_user
from app.schemas.scan import ScanOut
from app.models.user import User
from scanner.arp_runner import run_arp_scan
from scanner.nmap_runner import run_nmap
from scanner.nuclei_runner import run_nuclei
from scanner.device_identifier import identify_device
from scanner.device_identifier import discover_mdns_devices, discover_ssdp_devices
import scanner.continuous_scanner as cs

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
            scan.status       = "done"
            scan.devices_found = 0
            scan.vulns_found  = 0
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

        # ── 4. Enriquecer y guardar dispositivos ───────────────────────────
        logger.info("Fase 4: enriquecimiento y guardado de dispositivos")
        for d in arp_results:
            ip           = d["ip"]
            mac          = d["mac"]
            manufacturer = d.get("manufacturer")
            nmap_data    = nmap_results.get(ip, {})

            # Merge de datos arp + nmap
            device_data = {
                "ip":          ip,
                "mac":         mac,
                "manufacturer": manufacturer,
                "hostname":    nmap_data.get("hostname"),
                "os_family":   nmap_data.get("os_family"),
                "os_name":     nmap_data.get("os_name"),
                "os_accuracy": nmap_data.get("os_accuracy"),
                "ports":       nmap_data.get("ports", []),
            }

            # Identificar dispositivo (añade mdns_name, netbios_name, device_type, display_name)
            enriched = identify_device(device_data)

            # ── UPSERT atómico: nunca llamar db.add() si el IP ya existe ──
            # Buscar primero; si no existe, crear el objeto y añadirlo.
            # Luego, en ambos casos, actualizar los campos sobre el mismo objeto.
            # Esto evita el IntegrityError por UNIQUE constraint en devices.ip
            # cuando la sesión ya tiene una excepción pendiente o existe una
            # condición de carrera entre escaneos concurrentes.
            device = db.query(Device).filter(Device.ip == ip).first()
            if device is None:
                device = Device(ip=ip)
                db.add(device)

            for key, value in enriched.items():
                setattr(device, key, value)
            device.status    = "active"
            device.last_seen = datetime.now(timezone.utc)

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
                    device_id   = device.id,
                    scan_id     = scan.id,
                    cve_id      = vuln["cve_id"],
                    title       = vuln["title"],
                    severity    = vuln["severity"],
                    cvss_score  = vuln["cvss_score"],
                    description = vuln["description"],
                    solution    = vuln["solution"],
                    references  = vuln["references"],
                ))
                vuln_count += 1

        # ── 6. Finalizar escaneo ───────────────────────────────────────────
        scan.status        = "done"
        scan.devices_found = len(arp_results)
        scan.vulns_found   = vuln_count
        scan.completed_at  = datetime.now(timezone.utc)
        db.commit()
        db.refresh(scan)
        logger.info(f"Escaneo completado: {len(arp_results)} dispositivos, {vuln_count} vulnerabilidades.")
        return scan

    except Exception as e:
        logger.exception("Error durante el escaneo")
        db.rollback()
        scan.status        = "error"
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
        "scanning":         _scan_lock.locked(),
        "interval_minutes": cs.get_current_interval(),
        "next_run":         cs.get_next_run_time(),
    }


@router.put("/interval")
def set_scan_interval(
    body: ScanSettings,
    current_user: User = Depends(get_current_user),
):
    """Cambia el intervalo de escaneo automático (0 = desactivar)."""
    cs.update_interval(body.scan_interval_minutes)
    return {
        "message":          "Intervalo actualizado",
        "interval_minutes": body.scan_interval_minutes,
        "next_run":         cs.get_next_run_time(),
    }