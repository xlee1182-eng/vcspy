"""ForkliftLine 서비스 검증 (인메모리 SQLite + fakeredis).

실행: python tests/test_forklift_line_service.py
"""
from __future__ import annotations

import asyncio

import fakeredis.aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.tables import ForkliftLine
from app.services.forklift_line import forklift_line_service
from app.utils import json_util, redis_util

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
        await conn.run_sync(lambda c: ForkliftLine.__table__.create(c))
    return async_sessionmaker(engine, expire_on_commit=False)


async def main() -> None:
    sm = await setup()

    # 1) addForkLineList: 일괄 추가
    async with sm() as db:
        lines = [
            ForkliftLine(forklift_line_id=1, device_imei=1001, start_site_code=100, end_site_code=200,
                         step_number=2, return_line_id=55, line_name="L1"),
            ForkliftLine(forklift_line_id=2, device_imei=1001, start_site_code=300, end_site_code=400,
                         step_number=1, return_parent_id=66, line_name="L2"),
        ]
        r = await forklift_line_service.add_fork_line_list(db, lines)
        check("addForkLineList 성공", r.is_success())

    # 2) getLineToInit: 시작/종료 정밀 매칭 (step_number>1, return값 존재)
    async with sm() as db:
        res = await forklift_line_service.get_line_to_init(db, 1001, start_site_code=100, end_site_code=200)
        check("getLineToInit 1건", len(res) == 1 and res[0]["returnLineId"] == 55)

    # 3) step_number=1 은 제외
    async with sm() as db:
        res = await forklift_line_service.get_line_to_init(db, 1001, start_site_code=300, end_site_code=400)
        check("getLineToInit step1 제외", len(res) == 0)

    # 4) getLineToInit2: site_code 매칭(시작 또는 종료)
    async with sm() as db:
        res = await forklift_line_service.get_line_to_init(db, 1001, site_code=200)
        check("getLineToInit2 site_code 매칭", len(res) == 1 and res[0]["returnLineId"] == 55)

    # 5) getAllForkliftLine: Redis 리스트 반환
    await redis_util.redis_util.set_to_str(
        "forklift_all", json_util.to_json([{"forklift_line_id": 1, "line_name": "L1"}])
    )
    r = await forklift_line_service.get_all_forklift_line()
    check("getAllForkliftLine Redis 반환", isinstance(r.data, list) and len(r.data) == 1)

    # 6) 빈 리스트 추가 -> 실패
    async with sm() as db:
        r = await forklift_line_service.add_fork_line_list(db, [])
        check("빈 추가 -> 실패", r.resultCode == "1")

    print(f"\n결과: {ok} passed, {fail} failed")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
