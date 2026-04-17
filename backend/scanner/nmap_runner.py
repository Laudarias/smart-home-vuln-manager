import subprocess
import xml.etree.ElementTree as ET
from .utils import get_active_interface

def run_nmap(ips: list[str]) -> dict[str, dict]:
    if not ips:
        return {}
    
    interface = get_active_interface()    
    result = subprocess.run(
        ["sudo", "nmap", "-sV", "--open", "-oX", "-", "-T4", "--max-retries=1", "--host-timeout=30s", "-e", interface] + ips,
        capture_output=True,
        text=True
    )
    parsed = parse_nmap_output(result.stdout)
    return parsed

def parse_nmap_output(xml_output: str) -> dict[str, dict]:
    devices = {}

    try:
        root = ET.fromstring(xml_output)
    except ET.ParseError:
        return devices  # Retornar vacío si no se pudo parsear el XML

    for host in root.findall("host"):
        # Solo procesar hosts que estén "up"
        status = host.find("status").get("state")
        if status is None or status != "up":
            continue

        # Extraer IP, puertos y sistema operativo
        address = host.find("address[@addrtype='ipv4']")
        if address is None:
            continue
        ip = address.get("addr")

        # Obtener hostname si existe
        hostname = None
        hostnames = host.find("hostnames")
        if hostnames is not None:
            hostname_elem = hostnames.find("hostname")
            if hostname_elem is not None:
                hostname = hostname_elem.get("name")

        # Obtener OS si existe
        os_family = None
        os_elem = host.find("os")
        if os_elem is not None:
            osmatch = os_elem.find("osmatch")
            if osmatch is not None:
                os_family = osmatch.get("name")

        # Obtener puertos y servicios
        ports = []
        ports_elem = host.find("ports")
        if ports_elem is not None:
            for port in ports_elem.findall("port"):
                state = port.find("state")
                if state is None or state.get("state") != "open":
                    continue
                service = port.find("service")
                ports.append({
                    "port": port.get("portid"),
                    "protocol": port.get("protocol"),
                    "service": service.get("name") if service is not None else None,
                    "version": service.get("version") if service is not None else None,
                })

        devices[ip] = {
            "hostname": hostname,
            "os_family": os_family,
            "ports": ports
        }
    
    return devices
