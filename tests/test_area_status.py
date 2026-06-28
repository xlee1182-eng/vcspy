"""editAreaStatus(一键清满库) 검증 — 회귀 복구 확인.

실행: python tests/test_area_status.py
"""
from __future__ import annotations

import asyncio

import fakeredis.aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.tables import (
    Sequence,
    Storage,
    TaskTempDevice,
    TaskTempSite,
    TaskTemplate,
    UserTask,
)
from app.schemas.site import AreaStatusEditForm
from app.services.storage import storage_service
from app.utils import redis_util

ok = 0
fail = 0


def check(name: str, cond: bool) -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS {name}")
    else:
        fail += 1
        print(f"  FAIL {name}")


async def setup() -> async_sessionmaker[AsyncSession]:
    redis_util.set_client(fakeredis.aioredis.FakeRedis(decode_responses=True))
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        for m in (TaskTemplate, TaskTempSite, TaskTempDevice, Storage, UserTask, Sequence):
            await conn.run_sync(lambda c, mm=m: mm.__table__.create(c))
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as db:
        # 실행중 템플릿(run_status=0): 시작측(type1) 1개 + 종료측(type2) 2개
        db.add(TaskTemplate(task_template_id=100, template_name="T", run_status="0"))
        db.add(TaskTempSite(task_temp_site_id=1, task_template_id=100, site_type="1", site_code=5001, order_index=1))
        db.add(TaskTempSite(task_temp_site_id=2, task_template_id=100, site_type="2", site_code=6001, order_index=1))
        db.add(TaskTempSite(task_temp_site_id=3, task_template_id=100, site_type="2", site_code=6002, order_index=2))
        # 시작 보관위치: status1(findStorage type1 status1 매칭용)
        db.add(Storage(storage_id=1, storage_name="A1", site_code=5001, site_status="1", is_enable="0", storage_hight=0))
        # 종료측: 6001 빈자리(status0 → 작업 생성), 6002 작업중(status2 → 스킵)
        db.add(Storage(storage_id=10, storage_name="E1", site_code=6001, site_status="0", is_enable="0", storage_hight=0))
        db.add(Storage(storage_id=11, storage_name="E2", site_code=6002, site_status="2", is_enable="0", storage_hight=0))
        await db.commit()
    return sm


async def main() -> None:
    sm = await setup()

    # 실행중 아님(run_status=1) -> noTaskTemp
    async with sm() as db:
        db.add(TaskTemplate(task_template_id=200, template_name="X", run_status="1"))
        await db.commit()
        r = await storage_service.edit_area_status(db, AreaStatusEditForm(taskTemplateId=200, siteStatus="0", type="1"))
        check("미실행 템플릿 -> noTaskTemp", r.resultCode == "1")

    # 없는 템플릿 -> noTaskTemp
    async with sm() as db:
        r = await storage_service.edit_area_status(db, AreaStatusEditForm(taskTemplateId=999, siteStatus="0", type="1"))
        check("없는 템플릿 -> noTaskTemp", r.resultCode == "1")

    # 정상: type=2 종료측 2사이트 중 6001만 작업 생성(6002는 status2라 스킵)
    async with sm() as db:
        r = await storage_service.edit_area_status(db, AreaStatusEditForm(taskTemplateId=100, siteStatus="0", type="2"))
        check("editAreaStatus 성공", r.is_success())
    async with sm() as db:
        from app.repositories.task import user_task_repository
        tasks = await user_task_repository.select_all(db)
        check("작업 1건 생성(작업중 사이트 스킵)", len(tasks) == 1)
        check("생성된 작업 종료=6001", tasks and tasks[0].end_site_code == 6001)

    print(f"\n결과: {ok} passed, {fail} failed")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
