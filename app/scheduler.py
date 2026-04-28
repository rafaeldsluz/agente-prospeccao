"""
Agendador — roda ciclos a cada hora nos turnos 08:00-12:00 e 13:00-17:00.
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.agent import executar_ciclo

logger = logging.getLogger("agente.scheduler")

_scheduler: BackgroundScheduler | None = None

# Executa no início de cada hora dos dois turnos
TURNOS = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17]


def iniciar_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")

    for hora in TURNOS:
        _scheduler.add_job(
            executar_ciclo,
            trigger=CronTrigger(hour=hora, minute=0),
            id=f"ciclo_{hora}h",
            name=f"Ciclo {hora}:00",
            replace_existing=True,
            misfire_grace_time=1800,
        )

    _scheduler.start()
    logger.info("Scheduler iniciado — turnos 08:00-12:00 e 13:00-17:00")
    return _scheduler


def parar_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler parado")


def get_proxima_execucao() -> str:
    if not _scheduler or not _scheduler.running:
        return "Agendador inativo"
    proximos = []
    for hora in TURNOS:
        job = _scheduler.get_job(f"ciclo_{hora}h")
        if job and job.next_run_time:
            proximos.append(job.next_run_time)
    if proximos:
        prox = min(proximos)
        return prox.strftime("%d/%m/%Y às %H:%M")
    return "Não agendado"


def get_agenda() -> list[str]:
    if not _scheduler or not _scheduler.running:
        return []
    agenda = []
    for hora in TURNOS:
        job = _scheduler.get_job(f"ciclo_{hora}h")
        if job and job.next_run_time:
            agenda.append(job.next_run_time.strftime("%H:%M"))
    return agenda
