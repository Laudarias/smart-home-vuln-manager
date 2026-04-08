import subprocess
import re

def run_arp_scan() -> list[dict]:
    results = subprocess.run(
        ["sudo", "arp-scan", "--interface=eth2", "--localnet"],
        capture_output=True,
        text=True
        )
    return parse_arp_scan_output(results.stdout)

def parse_arp_scan_output(output: str) -> list[dict]:
    devices = []
    pattern = re.compile(r"^(\d{1,3}(?:\.\d{1,3}){3})\s+([\da-f:]{17})\s+(.+)$", re.IGNORECASE)
    lines = output.splitlines()
    for line in lines:
        match = pattern.match(line.strip())
        if match:
            ip, mac, manufacturer = match.groups()
            if manufacturer.startswith("(Unknown"):
                manufacturer = "Desconocido"
            devices.append({
                "ip": ip,
                "mac": mac.upper(),
                "manufacturer": manufacturer.strip()
            })
    return devices