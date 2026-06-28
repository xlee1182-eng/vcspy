"""스케줄러(RecordHeartJob) + 작업 픽업(editAndGetAnTask) 검증.

실행: python tests/test_scheduler.py
"""
from __future__ import annotations

import asyncio
from datetime import datetime

import fakeredis.aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.jobs import record_heart_job
from app.jobs.record_heart_job import RecordHeart
from app.models.tables import TaskTempDevice, UserTask
from app.services.task_op_service import task_op_service
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
        for m in (UserTask, TaskTempDevice):
            await conn.run_sync(lambda c, mm=m: mm.__table__.create(c))
    return async_sessionmaker(engine, expire_on_commit=False)


async def main() -> None:
    sm = await setup()

    # ---------- RecordHeartJob ----------
    await record_heart_job.execute()
    check("recordHeart 기본(미설정=True)", RecordHeart.record_heart is True)
    check("serverIsReady 기본 False", RecordHeart.server_is_ready is False)

    await redis_util.redis_util.set_to_str("record.heart", "off")
    await redis_util.redis_util.set_to_str("serverIsReady", "yes")
    await redis_util.redis_util.set_to_str("is.open.traffic", "on")
    await record_heart_job.execute()
    check("recordHeart off 반영", RecordHeart.record_heart is False)
    check("serverIsReady yes 반영", RecordHeart.server_is_ready is True)
    check("openTraffic on 반영", RecordHeart.open_traffic is True)

    # ---------- editAndGetAnTask 우선순위 ----------
    # ① 지정 미실행작업(deviceImei 1001, send_flag=1) 우선
    async with sm() as db:
        db.add(UserTask(user_task_id=10, device_imei=1001, send_flag="1", task_type="1", created_time=datetime(2024, 1, 1)))
        db.add(UserTask(user_task_id=11, device_imei=None, send_flag="1", task_type="2"))
        await db.commit()
    async with sm() as db:
        t = await task_op_service.edit_and_get_an_task(db, 1001)
        check("픽업 ① 지정작업 우선", t is not None and t.user_task_id == 10)

    # ② 지정작업 없으면 미지정(taskType=2)
    async with sm() as db:
        t = await task_op_service.edit_and_get_an_task(db, 2002)
        check("픽업 ④ 미지정작업", t is not None and t.user_task_id == 11)

    # ③ 다중차(taskType=3) + 템플릿에 장비 등록
    async with sm() as db:
        db.add(UserTask(user_task_id=20, send_flag="1", task_type="3", task_template_id=500))
        db.add(TaskTempDevice(task_temp_device_id=1, task_template_id=500, device_imei=3003))
        await db.commit()
    async with sm() as db:
        t = await task_op_service.edit_and_get_an_task(db, 3003)
        check("픽업 ② 다중차(장비등록)", t is not None and t.user_task_id == 20)

    # ④ 호출장비(taskType=4) desc 우선순위(미지정보다 먼저)
    async with sm() as db:
        db.add(UserTask(user_task_id=30, send_flag="1", task_type="4"))
        await db.commit()
    async with sm() as db:
        t = await task_op_service.edit_and_get_an_task(db, 4004)
        check("픽업 ③ 호출장비(4)가 미지정보다 우선", t is not None and t.task_type == "4")

    # 픽업할 작업 없음
    async with sm() as db:
        # 모든 작업 완료 처리
        from app.repositories.task import user_task_repository
        await user_task_repository.update_by_example(db, {"send_flag": "3"}, {})
        await db.commit()
    async with sm() as db:
        t = await task_op_service.edit_and_get_an_task(db, 9999)
        check("픽업 없음 -> None", t is None)

    print(f"\n결과: {ok} passed, {fail} failed")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
