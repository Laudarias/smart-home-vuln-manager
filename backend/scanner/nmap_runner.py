import subprocess
import xml.etree.ElementTree as ET
import logging
from .utils import get_active_interface

logger = logging.getLogger(__name__)


def run_nmap(ips: list[str]) -> dict[str, dict]:
    if not ips:
        return {}

    interface = get_active_interface()
    ip_args = ips  # nmap acepta lista directa de IPs

    cmd = [
        "sudo", "nmap",
        "-sV",              # versiones de servicios
        "-O",               # detección de OS
        "--osscan-guess",   # adivinar OS con confianza baja
        "--open",           # mostrar sólo puertos abiertos
        "--script=banner,nbstat,smb-os-discovery",  # info adicional de nombre/OS
        "-oX", "-",         # salida XML por stdout
        "-T4",
        "--max-retries=1",
        "--host-timeout=45s",
        "-e", interface,
    ] + ip_args

    logger.info(f"nmap command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode not in (0, 1):  # 1 = algún host offline, no es error
        logger.warning(f"nmap stderr: {result.stderr[:500]}")

    return parse_nmap_xml(result.stdout)


def parse_nmap_xml(xml_output: str) -> dict[str, dict]:
    """
    Parsea la salida XML de nmap y retorna un dict:
    { "192.168.1.x": {
        "hostname": str | None,
        "os_name": str | None,
        "os_accuracy": int | None,
        "ports": [ {"port":str, "protocol":str, "service":str, "version":str} ]
      }
    }
    """
    devices: dict[str, dict] = {}

    try:
        root = ET.fromstring(xml_output)
    except ET.ParseError as e:
        logger.error(f"nmap XML parse error: {e}")
        return devices

    for host in root.findall("host"):
        status = host.find("status")
        if status is None or status.get("state") != "up":
            continue

        addr_elem = host.find("address[@addrtype='ipv4']")
        if addr_elem is None:
            continue
        ip = addr_elem.get("addr")

        # ── Hostname ──────────────────────────────────────────────────────
        hostname = None
        hostnames_elem = host.find("hostnames")
        if hostnames_elem is not None:
            hn = hostnames_elem.find("hostname[@type='PTR']") or hostnames_elem.find("hostname")
            if hn is not None:
                hostname = hn.get("name")

        # ── Sistema operativo ─────────────────────────────────────────────
        os_name: str | None = None
        os_accuracy: int | None = None
        os_elem = host.find("os")
        if os_elem is not None:
            # osmatch ordenados por accuracy (mayor primero)
            best_match = None
            for osmatch in os_elem.findall("osmatch"):
                try:
                    acc = int(osmatch.get("accuracy", "0"))
                except ValueError:
                    acc = 0
                if best_match is None or acc > best_match[1]:
                    best_match = (osmatch.get("name"), acc)
            if best_match:
                os_name, os_accuracy = best_match

        # Intentar obtener OS desde scripts (smb-os-discovery, nbstat)
        hostscript_elem = host.find("hostscript")
        if hostscript_elem is not None and os_name is None:
            for script in hostscript_elem.findall("script"):
                sid = script.get("id", "")
                output = script.get("output", "")
                if sid == "smb-os-discovery" and "OS:" in output:
                    for part in output.split("\n"):
                        if part.strip().startswith("OS:"):
                            os_name = part.split(":", 1)[1].strip()
                            break
                elif sid == "nbstat":
                    # nbstat a veces da el OS en el output
                    if "Windows" in output:
                        os_name = os_name or "Windows"

        # ── Puertos ───────────────────────────────────────────────────────
        ports: list[dict] = []
        ports_elem = host.find("ports")
        if ports_elem is not None:
            for port_elem in ports_elem.findall("port"):
                state = port_elem.find("state")
                if state is None or state.get("state") != "open":
                    continue
                service = port_elem.find("service")
                ports.append({
                    "port":     port_elem.get("portid"),
                    "protocol": port_elem.get("protocol"),
                    "service":  service.get("name")    if service is not None else None,
                    "version":  (
                        f"{service.get('product', '')} {service.get('version', '')}".strip()
                        if service is not None else None
                    ),
                })

        devices[ip] = {
            "hostname":    hostname,
            "os_name":     os_name,
            "os_accuracy": os_accuracy,
            "ports":       ports,
        }

    return devices