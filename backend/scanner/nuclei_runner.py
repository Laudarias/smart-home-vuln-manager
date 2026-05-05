import subprocess
import json
import logging

logger = logging.getLogger(__name__)


def run_nuclei(ips: list[str]) -> list[dict]:
    if not ips:
        return []

    results = []
    for ip in ips:
        findings = _scan_ip(ip)
        results.extend(findings)
    return results


def _scan_ip(ip: str) -> list[dict]:
    result = subprocess.run(
        [
            "nuclei",
            "-target", ip,
            "-severity", "critical,high,medium,low",
            "-tags", "cve",
            "-timeout", "3",
            "-rate-limit", "50",
            "-jsonl",
            "-silent",
        ],
        capture_output=True,
        text=True,
    )

    findings = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        info = data.get("info", {})
        classification = info.get("classification", {})

        # CVSS score: puede venir como número o como string "7.5"
        cvss_raw = classification.get("cvss-score")
        try:
            cvss_score = float(cvss_raw) if cvss_raw is not None else None
        except (ValueError, TypeError):
            cvss_score = None

        # Si no hay CVSS, inferir desde severity
        if cvss_score is None:
            cvss_score = _severity_to_default_cvss(info.get("severity", ""))

        # Referencias: Nuclei las da como lista bajo "reference"
        references = info.get("reference") or []
        if isinstance(references, str):
            references = [references]

        # Solución / remediación
        solution = info.get("remediation") or info.get("fix") or None

        cve_ids = classification.get("cve-id") or []
        if isinstance(cve_ids, str):
            cve_ids = [cve_ids]

        findings.append({
            "ip":          data.get("host", ip).split(":")[0],
            "template_id": data.get("template-id") or data.get("templateID"),
            "name":        info.get("name"),
            "severity":    info.get("severity"),
            "cvss_score":  cvss_score,
            "description": info.get("description"),
            "matched_at":  data.get("matched-at"),
            "cve_id":      cve_ids,
            "references":  references,
            "solution":    solution,
        })

    return findings


def _severity_to_default_cvss(severity: str) -> float | None:
    """
    Asigna una puntuación CVSS representativa cuando Nuclei
    no proporciona una puntuación exacta.
    Basado en los rangos del estándar CVSS v3.
    """
    mapping = {
        "critical": 9.5,
        "high":     7.5,
        "medium":   5.0,
        "low":      2.0,
        "info":     None,
    }
    return mapping.get((severity or "").lower())