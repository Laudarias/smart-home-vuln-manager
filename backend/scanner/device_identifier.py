"""
Identificación de dispositivos.

  1. MAC OUI   → fabricante (ej. "Samsung Electronics")
  2. mDNS      → nombre amigable anunciado por el dispositivo (ej. "TV del salón")
  3. NetBIOS   → nombre Windows (nmblookup)
  4. DNS inv.  → hostname desde el servidor DHCP/DNS local
  5. SSDP/UPnP → dispositivos inteligentes que se anuncian a sí mismos
  6. Inferencia→ tipo de dispositivo basado en fabricante, OS y puertos
"""
import socket
import subprocess
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. MAC OUI → fabricante
# ---------------------------------------------------------------------------

def get_manufacturer(mac: str) -> Optional[str]:
    """Busca el fabricante a partir de los 3 primeros octetos de la MAC."""
    if not mac or len(mac) < 8:
        return None

    # Intento 1: mac-vendor-lookup (base de datos local, sin internet)
    try:
        from mac_vendor_lookup import MacLookup
        return MacLookup().lookup(mac)
    except Exception:
        pass

    # Intento 2: API pública macvendors.com (requiere internet)
    try:
        import urllib.request
        oui = mac.replace(":", "").replace("-", "")[:6].upper()
        url = f"https://api.macvendors.com/{oui}"
        req = urllib.request.Request(url, headers={"User-Agent": "smart-home-scanner/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            vendor = resp.read().decode().strip()
            if vendor and "Not Found" not in vendor:
                return vendor
    except Exception:
        pass

    return None


# ---------------------------------------------------------------------------
# 2. DNS inverso → hostname
# ---------------------------------------------------------------------------

def get_reverse_dns(ip: str) -> Optional[str]:
    """Resuelve el hostname mediante DNS inverso."""
    try:
        result = socket.gethostbyaddr(ip)
        hostname = result[0]
        # Limpiamos sufijos locales para mostrarlo más limpio
        for suffix in [".local", ".home", ".lan", ".localdomain"]:
            hostname = hostname.replace(suffix, "")
        return hostname if hostname != ip else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 3. NetBIOS → nombre Windows
# ---------------------------------------------------------------------------

def get_netbios_name(ip: str) -> Optional[str]:
    """Obtiene el nombre NetBIOS (útil para PCs y portátiles Windows)."""
    try:
        result = subprocess.run(
            ["nmblookup", "-A", ip],
            capture_output=True, text=True, timeout=6,
        )
        for line in result.stdout.splitlines():
            # Las líneas con <00> son el nombre de equipo; ignorar líneas de grupo (<00> GROUP)
            if "<00>" in line and "GROUP" not in line and "No reply" not in line:
                parts = line.strip().split()
                if parts:
                    return parts[0].strip()
    except FileNotFoundError:
        pass  # nmblookup no está instalado; no es crítico
    except Exception as e:
        logger.debug(f"NetBIOS lookup error for {ip}: {e}")
    return None


# ---------------------------------------------------------------------------
# 4. mDNS / Bonjour (avahi-browse)
# ---------------------------------------------------------------------------

def discover_mdns_devices() -> dict[str, str]:
    """
    Retorna {ip: nombre_amigable} para dispositivos que se anuncian
    por mDNS (Apple Bonjour, Chromecast, impresoras, etc.).
    """
    discovered: dict[str, str] = {}
    try:
        result = subprocess.run(
            ["avahi-browse", "--all", "--terminate", "--resolve", "--parsable"],
            capture_output=True, text=True, timeout=15,
        )
        for line in result.stdout.splitlines():
            # Formato parseable de avahi-browse:
            # =;<iface>;<proto>;<name>;<type>;<domain>;<hostname>;<addr>;<port>;<txt>
            if not line.startswith("="):
                continue
            parts = line.split(";")
            if len(parts) >= 8:
                friendly_name = parts[3]
                ip = parts[7]
                if ip and friendly_name and ip not in discovered:
                    discovered[ip] = friendly_name
    except FileNotFoundError:
        pass  # avahi-browse no instalado
    except Exception as e:
        logger.debug(f"mDNS discovery error: {e}")
    return discovered


# ---------------------------------------------------------------------------
# 5. SSDP / UPnP
# ---------------------------------------------------------------------------

def discover_ssdp_devices() -> dict[str, dict]:
    """
    Envía una petición M-SEARCH por multicast y recopila respuestas UPnP.
    Retorna {ip: {"type": ..., "server": ...}}
    """
    SSDP_ADDR = "239.255.255.250"
    SSDP_PORT = 1900
    SSDP_MX   = 3

    msg = (
        "M-SEARCH * HTTP/1.1\r\n"
        f"HOST: {SSDP_ADDR}:{SSDP_PORT}\r\n"
        'MAN: "ssdp:discover"\r\n'
        f"MX: {SSDP_MX}\r\n"
        "ST: ssdp:all\r\n\r\n"
    ).encode()

    devices: dict[str, dict] = {}
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(SSDP_MX + 1)
        sock.sendto(msg, (SSDP_ADDR, SSDP_PORT))

        deadline = time.time() + SSDP_MX + 1
        while time.time() < deadline:
            try:
                data, addr = sock.recvfrom(2048)
                ip = addr[0]
                if ip in devices:
                    continue

                response = data.decode("utf-8", errors="ignore")
                info: dict = {}

                for line in response.splitlines():
                    key, _, value = line.partition(":")
                    key = key.strip().upper()
                    value = value.strip()
                    if key == "SERVER":
                        info["server"] = value
                    elif key == "ST":
                        # Inferir tipo desde Service Type
                        st = value.lower()
                        if "mediarenderer" in st:
                            info["type"] = "smart-tv"
                        elif "mediaserver" in st:
                            info["type"] = "media-server"
                        elif "igd" in st or "router" in st or "gateway" in st:
                            info["type"] = "router"
                        elif "printer" in st:
                            info["type"] = "printer"
                        elif "basicdevice" in st or "rootdevice" in st:
                            info.setdefault("type", "smart-home")

                devices[ip] = info
            except socket.timeout:
                break
        sock.close()
    except Exception as e:
        logger.debug(f"SSDP discovery error: {e}")

    return devices


# ---------------------------------------------------------------------------
# 6. Inferencia de tipo de dispositivo
# ---------------------------------------------------------------------------

_MANUFACTURER_TYPE_MAP = [
    # (fragmentos de fabricante, tipo)
    (["cisco", "asus", "tp-link", "netgear", "d-link", "ubiquiti",
      "mikrotik", "huawei", "zte", "technicolor", "aruba", "fortinet"], "router"),
    (["philips", "ikea", "belkin", "wemo", "sonos", "nest", "ring",
      "amazon", "google", "ecobee", "lutron", "lifx", "tuya",
      "shelly", "espressif", "particle"], "smart-home"),
    (["samsung", "oneplus", "xiaomi", "oppo", "vivo", "motorola",
      "huawei mobile", "lenovo mobile"], "mobile"),
    (["apple"], None),          # Apple puede ser iPhone, Mac o iPad → depende del OS
    (["canon", "epson", "hp inc", "brother", "lexmark", "xerox",
      "kyocera", "ricoh"], "printer"),
    (["synology", "qnap", "western digital", "seagate nas"], "nas"),
    (["lg electronics", "sony", "tcl", "hisense", "vizio", "roku",
      "sharp"], "smart-tv"),
    (["raspberry pi"], "server"),
]

_OS_TYPE_MAP = [
    ("windows", "computer"),
    ("mac os", "computer"),
    ("macos", "computer"),
    ("linux", "computer"),
    ("ios", "mobile"),
    ("iphone", "mobile"),
    ("ipad", "mobile"),
    ("android", "mobile"),
    ("cisco ios", "router"),
    ("mikrotik", "router"),
]


def infer_device_type(
    manufacturer: Optional[str],
    os_name: Optional[str],
    ports: list,
    ssdp_type: Optional[str] = None,
) -> str:
    """Infiere el tipo de dispositivo a partir de la información disponible."""

    # SSDP es la fuente más directa (el propio dispositivo se identifica)
    if ssdp_type:
        return ssdp_type

    mfr = (manufacturer or "").lower()
    osn = (os_name or "").lower()
    port_nums = [int(p.get("port", 0)) for p in (ports or []) if str(p.get("port", "")).isdigit()]

    # Buscar por fabricante
    for fragments, dtype in _MANUFACTURER_TYPE_MAP:
        if any(frag in mfr for frag in fragments):
            if dtype:
                return dtype
            # Apple: diferenciar por OS o puertos
            if "apple" in mfr:
                if "ios" in osn or "iphone" in osn or "ipad" in osn:
                    return "mobile"
                if "mac os" in osn or "macos" in osn or "darwin" in osn:
                    return "computer"
                # Sin OS conocido: si tiene puertos 22/80/443 probablemente es un Mac
                if any(p in port_nums for p in [22, 80, 443, 548]):
                    return "computer"
                return "mobile"

    # Buscar por OS
    for fragment, dtype in _OS_TYPE_MAP:
        if fragment in osn:
            return dtype

    # Heurística por puertos: si tiene 80/443 + 22/23 probablemente es un router
    if {80, 443}.issubset(set(port_nums)) and any(p in port_nums for p in [22, 23, 8080, 8443]):
        return "router"

    return "unknown"


def best_display_name(
    hostname: Optional[str],
    mdns_name: Optional[str],
    netbios_name: Optional[str],
    manufacturer: Optional[str],
    device_type: Optional[str],
    ip: str,
) -> str:
    """Devuelve el mejor nombre para mostrar al usuario."""
    if mdns_name:
        return mdns_name
    if netbios_name:
        return netbios_name
    if hostname:
        return hostname
    if manufacturer and device_type:
        return f"{manufacturer} ({device_type})"
    return ip

def identify_device(device: dict) -> dict:
    """
    Recibe un dict con la información del dispositivo del pipeline
    y lo enriquece con identificación avanzada.

    Entrada esperada:
    {
        "ip": str,
        "mac": str,
        "manufacturer": str,
        "hostname": str | None,
        "os_family": str | None,
        "os_name": str | None,
        "os_accuracy": int | None,
        "ports": list[dict]
    }

    Salida: mismo dict + mdns_name, netbios_name, device_type, display_name
    """
    ip = device.get("ip")
    manufacturer = device.get("manufacturer")
    os_name = device.get("os_name")
    ports = device.get("ports", [])

    # 1. MAC OUI - limpiar fabricante
    if manufacturer:
        # Eliminar texto entre paréntesis
        import re
        manufacturer = re.sub(r'\([^)]*\)', '', manufacturer).strip()
        device["manufacturer"] = manufacturer

    # 2. mDNS/Bonjour
    mdns_devices = discover_mdns_devices()
    mdns_name = mdns_devices.get(ip)
    device["mdns_name"] = mdns_name

    # 3. NetBIOS
    netbios_name = get_netbios_name(ip)
    device["netbios_name"] = netbios_name

    # 4. DNS inverso - actualizar hostname si no existe
    if not device.get("hostname"):
        device["hostname"] = get_reverse_dns(ip)

    # 5. SSDP/UPnP para tipo de dispositivo
    ssdp_devices = discover_ssdp_devices()
    ssdp_info = ssdp_devices.get(ip, {})
    ssdp_type = ssdp_info.get("type")

    # 6. Inferir tipo de dispositivo
    device_type = infer_device_type(manufacturer, os_name, ports, ssdp_type)
    device["device_type"] = device_type

    # 7. Display name
    display_name = best_display_name(
        device.get("hostname"),
        mdns_name,
        netbios_name,
        manufacturer,
        device_type,
        ip
    )
    device["display_name"] = display_name

    return device