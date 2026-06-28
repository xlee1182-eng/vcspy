"""UserTask 조회/취소/초기화 검증 (인메모리 SQLite + fakeredis).

실행: python tests/test_user_task_service.py
"""
from __future__ import annotations

import asyncio
from datetime import datetime

import fakeredis.aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.tables import UserTask
from app.services.user_task import user_task_service
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
        await conn.run_sync(lambda c: UserTask.__table__.create(c))
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as db:
        db.add(UserTask(user_task_id=1, device_imei=1001, message_id="MSG-1",
                        send_flag="1", pick_place_state="0", created_time=datetime(2024, 1, 1)))
        db.add(UserTask(user_task_id=2, device_imei=1001, message_id="MSG-2",
                        send_flag="3", pick_place_state="2"))
        db.add(UserTask(user_task_id=3, device_imei=2002, message_id="MSG-3", send_flag="1"))
        await db.commit()
    return sm


async def main() -> None:
    sm = await setup()

    # 1) getTaskResult: send_flag 반환 + Redis 캐시 생성
    async with sm() as db:
        r = await user_task_service.get_task_result(db, None, "MSG-2")
        check("getTaskResult send_flag=3", r.is_success() and r.data == "3")
    cached = await redis_util.redis_util.get_str_to_object("task_state_MSG-2")
    check("getTaskResult Redis 캐시 생성", cached is not None and cached["send_flag"] == "3")

    # 2) getPickPlaceState
    async with sm() as db:
        r = await user_task_service.get_pick_place_state(db, None, "MSG-2")
        check("getPickPlaceState=2", r.is_success() and r.data == "2")

    # 3) messageId 누락
    async with sm() as db:
        r = await user_task_service.get_task_result(db, None, None)
        check("messageId 누락 -> 실패", r.resultCode == "1" and "Message ID" in r.resultMsg)

    # 4) 없는 작업
    async with sm() as db:
        r = await user_task_service.get_task_result(db, None, "NOPE")
        check("없는 작업 -> TaskNotExit", r.resultCode == "1" and "does not exist" in r.resultMsg)

    # 5) cancelTask: device 1001 의 send_flag='1' 만 '7' 로
    async with sm() as db:
        r = await user_task_service.cancel_task(db, 1001)
        check("cancelTask 성공", r.is_success())
    async with sm() as db:
        from app.repositories.task import user_task_repository
        t1 = await user_task_repository.select_by_pk(db, 1)
        t2 = await user_task_repository.select_by_pk(db, 2)
        t3 = await user_task_repository.select_by_pk(db, 3)
        check("cancel: 1001 미실행 -> 7", t1.send_flag == "7")
        check("cancel: 완료작업(3)은 불변", t2.send_flag == "3")
        check("cancel: 다른장비(2002)는 불변", t3.send_flag == "1")

    # 6) deviceImei 누락
    async with sm() as db:
        r = await user_task_service.cancel_task(db, None)
        check("cancel deviceImei 누락 -> 실패", r.resultCode == "1")

    # 7) clearTask: 전체 삭제
    async with sm() as db:
        r = await user_task_service.clear_task(db)
        check("clearTask 성공", r.is_success())
    async with sm() as db:
        from app.repositories.task import user_task_repository
        rows = await user_task_repository.select_all(db)
        check("clearTask 후 0건", len(rows) == 0)

    print(f"\n결과: {ok} passed, {fail} failed")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
