import subprocess
import re

def get_active_interface() -> str:
    result = subprocess.run(
        ["ip", "route", "show", "default"],
        capture_output=True,
        text=True
    )
    match = re.search(r"dev\s+(\S+)", result.stdout)
    if match:
        return match.group(1)
    return "eth0" # Fallback si no se encuentra la interfaz