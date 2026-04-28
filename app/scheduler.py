"""
Agendador — prospecção a cada hora (08-17h) + follow-ups diários (10h e 14h).
"""
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.agent import executar_ciclo
from app.messaging.followup import executar_followups

logger = logging.getLogger("agente.scheduler")

_scheduler: BackgroundScheduler | None = None

TURNOS = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17]
FOLLOWUP_HORAS = [10, 14]


def iniciar_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")

    # Ciclos de prospecção horários
    for hora in TURNOS:
        _scheduler.add_job(
            executar_ciclo,
            trigger=CronTrigger(hour=hora, minute=0),
            id=f"ciclo_{hora}h",
            name=f"Prospecção {hora}:00",
            replace_existing=True,
            misfire_grace_time=1800,
        )

    # Follow-ups automáticos
    for hora in FOLLOWUP_HORAS:
        _scheduler.add_job(
            executar_followups,
            trigger=CronTrigger(hour=hora, minute=30),
            id=f"followup_{hora}h",
            name=f"Follow-up {hora}:30",
            replace_existing=True,
            misfire_grace_time=1800,
        )

    _scheduler.start()
    logger.info("Scheduler iniciado — prospecção 08-17h + follow-ups 10:30 e 14:30")
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
        return min(proximos).strftime("%d/%m/%Y às %H:%M")
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
