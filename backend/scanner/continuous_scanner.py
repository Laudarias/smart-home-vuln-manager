"""
Servicio de escaneo continuo/programado.
"""
import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import SCAN_INTERVAL_MINUTES

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")
_scan_function = None   # se inyecta desde main.py para evitar importaciones circulares


def set_scan_function(fn):
    """Registra la función que ejecuta el escaneo completo."""
    global _scan_function
    _scan_function = fn


async def _run_scheduled_scan():
    if _scan_function is None:
        logger.warning("Función de escaneo no registrada en el scheduler.")
        return
    logger.info("Iniciando escaneo programado automático")
    try:
        await asyncio.get_event_loop().run_in_executor(None, _scan_function, "scheduled")
    except Exception as e:
        logger.error(f"Error en escaneo programado: {e}")


def start_scheduler(interval_minutes: int = SCAN_INTERVAL_MINUTES):
    """Inicia el scheduler. Si interval_minutes == 0, no se programa ningún escaneo."""
    if interval_minutes <= 0:
        logger.info("Escaneo continuo desactivado (SCAN_INTERVAL_MINUTES=0).")
        return

    scheduler.add_job(
        _run_scheduled_scan,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="continuous_scan",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Escaneo continuo iniciado: cada {interval_minutes} minutos.")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)


def update_interval(minutes: int):
    """Cambia el intervalo de escaneo en tiempo de ejecución."""
    if minutes <= 0:
        if scheduler.get_job("continuous_scan"):
            scheduler.remove_job("continuous_scan")
        logger.info("Escaneo continuo desactivado.")
        return

    scheduler.reschedule_job(
        "continuous_scan",
        trigger=IntervalTrigger(minutes=minutes),
    )
    logger.info(f"Intervalo de escaneo actualizado a {minutes} minutos.")


def get_next_run_time() -> str | None:
    """Retorna la hora del próximo escaneo como string ISO, o None."""
    job = scheduler.get_job("continuous_scan")
    if job and job.next_run_time:
        return job.next_run_time.isoformat()
    return None

def get_current_interval() -> int:
    """Retorna el intervalo actual en minutos."""
    job = scheduler.get_job("continuous_scan")
    if job and hasattr(job.trigger, 'interval'):
        return int(job.trigger.interval.total_seconds() // 60)
    return 0