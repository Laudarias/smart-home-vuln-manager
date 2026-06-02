import subprocess
import json
import logging

logger = logging.getLogger(__name__)


def run_nuclei(ips: list[str]) -> list[dict]:
    """
    Ejecuta Nuclei sobre la lista de IPs en dos pasadas:
    1. Detección de CVEs conocidos (-tags cve)
    2. Detección de credenciales por defecto (-tags default-login)
    Retorna la lista combinada de hallazgos.
    """
    if not ips:
        return []

    results = []
    for ip in ips:
        # Pasada 1: CVEs conocidos
        results.extend(_scan_ip(ip, tags="cve"))
        # Pasada 2: credenciales por defecto
        results.extend(_scan_ip(ip, tags="default-login"))
    return results


def _scan_ip(ip: str, tags: str = "cve") -> list[dict]:
    """
    Lanza Nuclei contra una IP con las etiquetas especificadas.
    tags: "cve" para vulnerabilidades conocidas, "default-login" para credenciales por defecto.
    """
    cmd = [
        "nuclei",
        "-target", ip,
        "-tags", tags,
        "-timeout", "3",
        "-rate-limit", "50",
        "-jsonl",
        "-silent",
    ]

    # Para CVEs, filtrar por severidad relevante; default-login no usa severidad CVSS
    if tags == "cve":
        cmd += ["-severity", "critical,high,medium,low"]

    result = subprocess.run(
        cmd,
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

        # CVSS score
        cvss_raw = classification.get("cvss-score")
        try:
            cvss_score = float(cvss_raw) if cvss_raw is not None else None
        except (ValueError, TypeError):
            cvss_score = None

        # Para credenciales por defecto, asignar severidad alta si no hay CVSS
        severity = info.get("severity", "").lower()
        if cvss_score is None:
            cvss_score = _severity_to_default_cvss(severity)

        # Para default-login sin severidad declarada, asignar "high" (credencial expuesta es alto riesgo)
        if tags == "default-login" and not severity:
            severity = "high"
            cvss_score = 7.5

        # Referencias
        references = info.get("reference") or []
        if isinstance(references, str):
            references = [references]

        # Solución — enriquecer con texto en español si no viene del template
        solution_raw = info.get("remediation") or info.get("fix") or None
        solution = _enrich_solution(solution_raw, tags, severity)

        # CVE ID
        cve_id = data.get("template-id") or data.get("templateID")

        findings.append({
            "ip":          data.get("host", ip).split(":")[0],
            "cve_id":      cve_id,
            "title":       info.get("name"),
            "severity":    severity,
            "cvss_score":  cvss_score,
            "description": info.get("description"),
            "references":  references,
            "solution":    solution,
            "scan_type":   tags,  # para distinguir origen del hallazgo
        })

    return findings


def _enrich_solution(solution_raw: str | None, tags: str, severity: str) -> str:
    """
    Si Nuclei no provee una solución, genera un texto de remediación
    en español comprensible para un usuario no técnico, basado en el
    tipo de hallazgo y la severidad.
    """
    if solution_raw:
        return solution_raw  # usar el texto original si existe

    if tags == "default-login":
        return (
            "Este dispositivo está usando una contraseña predeterminada de fábrica. "
            "Accede a su configuración y cámbiala por una contraseña única que solo tú conozcas. "
            "Consulta el manual del fabricante si no sabes cómo hacerlo."
        )

    fallback = {
        "critical": (
            "Esta vulnerabilidad es crítica. Actualiza el firmware o software de este "
            "dispositivo lo antes posible. Si no hay actualización disponible, considera "
            "desconectarlo de la red hasta que el fabricante publique un parche."
        ),
        "high": (
            "Actualiza el firmware o software de este dispositivo. "
            "Visita el sitio web del fabricante para descargar la versión más reciente."
        ),
        "medium": (
            "Se recomienda actualizar el firmware de este dispositivo "
            "para reducir el riesgo de seguridad."
        ),
        "low": (
            "Riesgo bajo. Revisa si hay actualizaciones disponibles para este dispositivo."
        ),
    }
    return fallback.get(severity, "Consulta la documentación del fabricante para obtener una actualización.")


def _severity_to_default_cvss(severity: str) -> float | None:
    mapping = {
        "critical": 9.5,
        "high":     7.5,
        "medium":   5.0,
        "low":      2.0,
        "info":     None,
    }
    return mapping.get((severity or "").lower())