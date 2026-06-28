"""스케줄러.

원본 com.ygcloud.ygvcs.job.ScheduledPool(ThreadPoolTaskScheduler poolSize=5) 대체.
APScheduler(AsyncIOScheduler) 로 주기 작업을 등록한다.
현재 등록: RecordHeartJob.execute (운영 플래그 갱신, 5초 주기).
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.jobs import record_heart_job

LOGGER = logging.getLogger('app')

_scheduler: AsyncIOScheduler | None = None


def start_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = AsyncIOScheduler()
    # 원본 RecordHeartJob: 운영 플래그 주기 갱신
    _job_id = "record_heart_job"
    _interval = 5
    _scheduler.add_job(record_heart_job.execute, "interval", seconds=_interval, id=_job_id, max_instances=3, coalesce=True)
    _scheduler.start()
    LOGGER.info("[Scheduler] %s — 매 %d초마다 실행", _job_id, _interval)
    return _scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
