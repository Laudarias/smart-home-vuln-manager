import subprocess
import json
from scanner.utils import get_active_interface

def run_nuclei(ips: list[str]) -> list[dict]:
    if not ips:
        return []

    results = []
    for ip in ips:
        findings = scan_ip(ip)
        results.extend(findings)
    return results

def scan_ip(ip: str) -> list[dict]:
    result = subprocess.run(
        [
            "nuclei",
            "-target", ip,
            "-severity", "critical,high,medium",
            "-tags", "cve",
            "-timeout", "3",
            "-rate-limit", "50",
            "-jsonl",
            "-silent"
        ],
        capture_output=True,
        text=True
    )

    findings = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            findings.append({
                "ip": ip,
                "template_id": data.get("templateID"),
                "name": data.get("info", {}).get("name"),
                "severity": data.get("info", {}).get("severity"),
                "description": data.get("info", {}).get("description"),
                "matched_at": data.get("matched-at"),
                "cve_id": data.get("info", {}).get("classification", {}).get("cve-id", []),
            })
        except json.JSONDecodeError:
            continue
    return findings