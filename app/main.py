"""yg-vcs FastAPI 진입점.

원본 Spring Boot(YgVcsApplication)의 대체. 기동 시:
  - HTTP API (FastAPI)
  - TCP 통신 서버들(primary/cam/callBox) ─ 이식 진행 중
  - WebSocket 서버 ─ 이식 진행 중
  - 스케줄러(job) ─ 이식 진행 중
context-path는 원본과 동일하게 /ygvcs 를 사용한다.
"""
from __future__ import annotations

import app.utils.WriteConsoleLog as __UTIL_WRITECONSOLELOG
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.routers import (  # noqa: E402
    device, forklift_line, process_warp, site, task, traffic, user, user_task, user_task_warp,
)


LOGGER = __UTIL_WRITECONSOLELOG.SETLOGGER()

import logging
for _name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    _uv = logging.getLogger(_name)
    _uv.handlers = LOGGER.handlers
    _uv.propagate = False


async def _check_mysql() -> None:
    from sqlalchemy import text
    from app.core.database import get_engine
    LOGGER.info("[MySQL] 연결중... %s:%s  db=%s", settings.db_host, settings.db_port, settings.db_name)
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        LOGGER.info("[MySQL] 연결 OK")
    except Exception as e:
        LOGGER.error("[MySQL] 연결 실패: %s", e)


async def _check_redis() -> None:
    import redis.asyncio as aioredis
    LOGGER.info("[Redis] 연결중... %s:%s  db=%s", settings.redis_host, settings.redis_port, settings.redis_db)
    client = aioredis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password,
        db=settings.redis_db,
        socket_timeout=3,
        protocol=2,
    )
    try:
        await client.ping()
        LOGGER.info("[Redis] 연결 OK")
    except Exception as e:
        LOGGER.error("[Redis] 연결 실패: %s", e)
    finally:
        await client.aclose()


async def _init_redis_data() -> None:
    """원본 Java 시작 시 Redis에 초기값을 세팅하던 로직."""
    from app.core import redis_constants as rc
    from app.core.database import get_sessionmaker
    from app.models.tables import ForkliftLine
    from app.utils import json_util
    from app.utils.redis_util import redis_util
    from sqlalchemy import select as sa_select

    # 1. communication_key
    await redis_util.set_to_str(rc.COMMUN_KEY_PREXFIX, settings.communication_key)
    LOGGER.info("[Redis] communication_key = %s", settings.communication_key)

    # 2. forklift_all — DB에서 전체 노선 로드
    try:
        async with get_sessionmaker()() as db:
            res = await db.execute(sa_select(ForkliftLine))
            lines = res.scalars().all()
        line_list = [json_util.to_dict(l) for l in lines]
        await redis_util.set_to_str(rc.FORKLIFT_ALL, line_list)
        LOGGER.info("[Redis] forklift_all  (%d건)", len(line_list))
    except Exception as e:
        LOGGER.error("[Redis] forklift_all 실패: %s", e)

    # 3. serverIsReady
    await redis_util.set_to_str("serverIsReady", "yes")
    LOGGER.info("[Redis] serverIsReady = yes")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _check_mysql()
    await _check_redis()
    await _init_redis_data()
    # 차량(AGV) TCP 서버 기동 (원본 PrimaryNettyServer)
    from app.tcp.primary_server import start_primary_server

    servers = []
    if settings.primary_server_enabled:
        servers.append(await start_primary_server(settings.primary_server_port))
    if settings.cam_server_enabled:
        from app.tcp.cam_server import start_cam_server
        servers.append(await start_cam_server(settings.cam_server_port))
    if settings.callbox_server_enabled:
        from app.tcp.callbox_server import start_callbox_server
        servers.append(await start_callbox_server(settings.callbox_server_port))
    if settings.ws_server_enabled:
        from app.ws.ws_server import start_ws_server
        servers.append(await start_ws_server(settings.ws_server_port))
    # 스케줄러 기동 (RecordHeartJob 등)
    from app.jobs.scheduler import start_scheduler, stop_scheduler

    if settings.scheduler_enabled:
        start_scheduler()
    yield
    stop_scheduler()
    for s in servers:
        await s.stop()


_sub = FastAPI(
    title="yg-vcs (Python)",
    version=settings.server_version,
    docs_url="/swagger-ui/",
    openapi_url="/v3/api-docs",
)


@_sub.get("/health")
async def health() -> dict:
    return {"status": "UP", "app": settings.app_name, "version": settings.server_version}

_sub.include_router(process_warp.router) # /service/warp/process
_sub.include_router(user.router) # /service/warp/user
_sub.include_router(device.router) # /service/warp/device
_sub.include_router(site.site_router) # /service/warp/site
_sub.include_router(site.storage_device_router) # /service/warp/storageDevice
_sub.include_router(task.router) # /service/warp/task
_sub.include_router(user_task_warp.router) # /service/warp/userTask


_sub.include_router(device.web_router) # /service/web/device
_sub.include_router(user_task.router) # /service/web/userTask
_sub.include_router(site.site_manage_router) # /service/web/siteManage
_sub.include_router(forklift_line.router) # /service/web/forkliftLine
_sub.include_router(traffic.router) # /service/web/traffic


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
app.mount(settings.context_path, _sub)
