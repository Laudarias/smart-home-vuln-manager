import subprocess
import re
import platform
import logging
from threading import Thread, Event

logger = logging.getLogger(__name__)

# Evento para detener el monitoreo pasivo
_stop_event = Event()
_monitor_thread = None


def is_passive_monitoring_supported() -> bool:
    """
    El monitoreo pasivo con tcpdump solo está disponible en Linux nativo
    (Raspberry Pi). En WSL2 y Windows no se puede capturar tráfico de red completo.
    """
    return platform.system() == "Linux" and not _is_wsl()


def _is_wsl() -> bool:
    """Detecta si estamos corriendo dentro de WSL2."""
    try:
        with open("/proc/version", "r") as f:
            return "microsoft" in f.read().lower()
    except Exception:
        return False


def start_passive_monitor(interface: str, on_new_device_callback=None):
    """
    Inicia el monitoreo pasivo de tráfico ARP en segundo plano.
    Detecta nuevos dispositivos que aparecen en la red sin escanear activamente.

    Args:
        interface: Interfaz de red a monitorear (ej. "eth0", "wlan0")
        on_new_device_callback: Función a llamar cuando se detecta un nuevo dispositivo.
                                 Recibe un dict {"ip": str, "mac": str}
    """
    global _monitor_thread, _stop_event

    if not is_passive_monitoring_supported():
        logger.info("Monitoreo pasivo no disponible en esta plataforma (WSL2/Windows). Modo A activo.")
        return

    _stop_event.clear()
    _monitor_thread = Thread(
        target=_run_tcpdump_monitor,
        args=(interface, on_new_device_callback),
        daemon=True,
    )
    _monitor_thread.start()
    logger.info(f"Monitoreo pasivo iniciado en interfaz {interface}")


def stop_passive_monitor():
    """Detiene el monitoreo pasivo."""
    global _stop_event
    _stop_event.set()
    logger.info("Monitoreo pasivo detenido.")


def _run_tcpdump_monitor(interface: str, callback=None):
    """
    Ejecuta tcpdump filtrando solo paquetes ARP.
    Cuando detecta un nuevo dispositivo, llama al callback.
    tcpdump requiere privilegios de root o la capability CAP_NET_RAW.
    En la Raspberry Pi, el script de instalación configura esto via sudoers.
    """
    seen_macs = set()

    # Filtro ARP: captura solo anuncios de la capa 2, sin escribir a disco
    cmd = [
        "sudo", "tcpdump",
        "-i", interface,
        "-l",           # line-buffered para leer en tiempo real
        "-n",           # no resolver nombres (más rápido)
        "arp",          # solo paquetes ARP
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )

        for line in proc.stdout:
            if _stop_event.is_set():
                proc.terminate()
                break

            # Ejemplo de línea tcpdump ARP:
            # "12:34:56 ARP, Request who-has 192.168.1.50 tell 192.168.1.1, length 28"
            # Extraer IP y, si está disponible, MAC
            ip_match = re.search(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", line)
            # tcpdump -n con arp no siempre muestra MAC en el texto, pero sí la IP origen
            # Para obtener MAC necesitaríamos -e flag
            if ip_match:
                ip = ip_match.group(1)
                if ip not in seen_macs and callback:
                    seen_macs.add(ip)
                    logger.debug(f"Nuevo dispositivo detectado pasivamente: {ip}")
                    callback({"ip": ip, "mac": None, "source": "passive"})

    except Exception as e:
        logger.warning(f"Error en monitoreo pasivo: {e}")