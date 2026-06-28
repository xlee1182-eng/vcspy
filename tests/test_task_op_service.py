"""TaskOpService.createTask 검증 (인메모리 SQLite).

작업 생성 상태머신: 조건검증 → UserTask(send_flag=1) 생성 → 보관위치 상태 갱신.
실행: python tests/test_task_op_service.py
"""
from __future__ import annotations

import asyncio
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.tables import (
    Sequence,
    Storage,
    TaskTempDevice,
    TaskTempSite,
    TaskTemplate,
    UserTask,
)
from app.repositories.task import user_task_repository
from app.services.task_op_service import TaskCreateForm, task_op_service

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
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        for m in (TaskTemplate, TaskTempSite, TaskTempDevice, Storage, UserTask, Sequence):
            await conn.run_sync(lambda c, mm=m: mm.__table__.create(c))
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as db:
        # 실행중 템플릿(run_status=0): 시작 5001(type1), 종료 6001(type2)
        db.add(TaskTemplate(task_template_id=100, template_name="T", run_status="0"))
        db.add(TaskTempSite(task_temp_site_id=1, task_template_id=100, site_type="1", site_code=5001, order_index=1))
        db.add(TaskTempSite(task_temp_site_id=2, task_template_id=100, site_type="2", site_code=6001, order_index=1))
        # 보관위치: 시작 5001(status0), 종료 6001(status0)
        db.add(Storage(storage_id=1, storage_name="A1", site_code=5001, site_status="0", storage_hight=10))
        db.add(Storage(storage_id=2, storage_name="B1", site_code=6001, site_status="0", storage_hight=20))
        # 템플릿에 장비 1대 등록 → 지정차 작업
        db.add(TaskTempDevice(task_temp_device_id=1, task_template_id=100, device_imei=1001))
        await db.commit()
    return sm


async def main() -> None:
    sm = await setup()

    # 1) codeAct="2"(입고): 작업 생성 성공
    async with sm() as db:
        r = await task_op_service.create_task(db, TaskCreateForm(device_imei="cam1", code=5001, code_act="2", device_type="2"))
        check("createTask(입고) 성공", r.status is True)

    # 2) UserTask 생성 검증
    async with sm() as db:
        tasks = await user_task_repository.select_all(db)
        check("UserTask 1건 생성", len(tasks) == 1)
        t = tasks[0]
        check("send_flag='1'", t.send_flag == "1")
        check("task_type='1'(지정차, 장비1대)", t.task_type == "1")
        check("device_imei=1001 배정", t.device_imei == 1001)
        check("start=5001,end=6001", t.start_site_code == 5001 and t.end_site_code == 6001)
        check("funCode=B2, lift=100", t.fun_code == "B2" and t.lift_height == 100)

    # 3) 보관위치 상태: 시작=2, 종료=3
    async with sm() as db:
        from app.repositories.site import storage_repository
        s1 = await storage_repository.select_by_pk(db, 1)
        s2 = await storage_repository.select_by_pk(db, 2)
        check("시작 보관위치 status=2", s1.site_status == "2")
        check("종료 보관위치 status=3", s2.site_status == "3")

    # 4) 이미 진행중 작업이 있는 사이트 -> 거부
    async with sm() as db:
        r = await task_op_service.create_task(db, TaskCreateForm(device_imei="cam2", code=5001, code_act="2", device_type="2"))
        check("진행중 사이트 -> taskIsExecuted", r.status is False and "ongoing" in (r.msg or "").lower())

    # 5) 템플릿 없는 사이트 -> siteNotTaskTemplate
    async with sm() as db:
        r = await task_op_service.create_task(db, TaskCreateForm(device_imei="cam3", code=9999, code_act="2", device_type="2"))
        check("템플릿 없음 -> 실패", r.status is False)

    # 6) 잘못된 codeAct -> 실패
    async with sm() as db:
        r = await task_op_service.create_task(db, TaskCreateForm(device_imei="cam4", code=5001, code_act="9", device_type="2"))
        check("잘못된 codeAct -> 실패", r.status is False)

    print(f"\n결과: {ok} passed, {fail} failed")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
