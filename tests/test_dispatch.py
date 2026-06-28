"""자동 디스패치 검증: 유휴 하트비트 → 작업 픽업 → 송신 → send_flag=2.

실행: python tests/test_dispatch.py
"""
from __future__ import annotations

import asyncio
from datetime import datetime

import fakeredis.aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.tables import TaskTempDevice, UserTask
from app.services.send_task import send_task_service
from app.tcp import byte_process as bp
from app.tcp.channel_manager import channel_manager
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


class FakeWriter:
    def __init__(self):
        self.frames = []

    def write(self, data):
        self.frames.append(bytes(data))


def _auto_reply(imei: int):
    fw = channel_manager._channels[imei]
    seen = {"n": 0}

    async def loop():
        from app.tcp.response_parser import _FLAG_AT_30
        for _ in range(400):
            while len(fw.frames) > seen["n"]:
                sent = fw.frames[seen["n"]]
                seen["n"] += 1
                msg_no = bp.print_hex_string(sent[4:8])
                fun = bp.print_hex_string(sent[12:13])
                data = "0000FF" if fun in _FLAG_AT_30 else "00FF"
                resp = bp.hex_string_to_bytes(
                    bp.get_crc_to_send("40BF407F" + msg_no + bp.int_to_hex(imei, 4) + fun + data, "123456789")
                )
                channel_manager.receive_msg(resp, ip="10.0.0.9")
            await asyncio.sleep(0.003)
    return asyncio.create_task(loop())


async def setup() -> async_sessionmaker[AsyncSession]:
    redis_util.set_client(fakeredis.aioredis.FakeRedis(decode_responses=True))
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        for m in (UserTask, TaskTempDevice):
            await conn.run_sync(lambda c, mm=m: mm.__table__.create(c))
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as db:
        db.add(UserTask(user_task_id=700, device_imei=1001, send_flag="1", task_type="1",
                        start_site_code=5001, end_site_code=6001, start_handel="1", end_handel="2",
                        start_storage_height=0, end_storage_height=0, created_time=datetime(2024, 1, 1)))
        await db.commit()
    return sm


async def main() -> None:
    sm = await setup()
    imei = 1001

    # should_dispatch 판정
    idle = {"deviceImei": imei, "taskFlag": 0, "forkStatus": 0, "flag": "82", "startSiteCode": 5001, "lockState": 1}
    busy = {"deviceImei": imei, "taskFlag": 1, "forkStatus": 0, "flag": "82", "startSiteCode": 5001, "lockState": 1}
    check("should_dispatch 유휴=True", send_task_service.should_dispatch(idle) is True)
    check("should_dispatch taskFlag!=0=False", send_task_service.should_dispatch(busy) is False)
    check("should_dispatch flag비유휴=False",
          send_task_service.should_dispatch({**idle, "flag": "77"}) is False)
    check("should_dispatch startSite=0=False",
          send_task_service.should_dispatch({**idle, "startSiteCode": 0}) is False)

    # serverIsReady 아니면 디스패치 안 함
    channel_manager._channels[imei] = FakeWriter()
    _auto_reply(imei)
    async with sm() as db:
        sent = await send_task_service.dispatch_task(db, idle)
        check("serverIsReady 아님 -> 디스패치 안함", sent is False)

    # serverIsReady=yes → 디스패치 성공
    await redis_util.redis_util.set_to_str("serverIsReady", "yes")
    channel_manager._channels[imei] = FakeWriter()
    _auto_reply(imei)
    async with sm() as db:
        sent = await send_task_service.dispatch_task(db, idle)
        check("유휴+ready -> 디스패치 성공", sent is True)
    async with sm() as db:
        from app.repositories.task import user_task_repository
        t = await user_task_repository.select_by_pk(db, 700)
        check("디스패치 후 send_flag='2'", t.send_flag == "2")
        check("디스패치 후 device_imei 배정", t.device_imei == imei)

    # 더 픽업할 작업 없으면 디스패치 False
    channel_manager._channels[imei] = FakeWriter()
    _auto_reply(imei)
    async with sm() as db:
        sent = await send_task_service.dispatch_task(db, idle)
        check("픽업할 작업 없음 -> False", sent is False)

    # 미잠금(lockState=0)이면 taskLock 프레임이 선행됨 (총 3프레임: lock+task+start)
    async with sm() as db:
        db.add(UserTask(user_task_id=701, device_imei=1001, send_flag="1", task_type="1",
                        start_site_code=5001, end_site_code=6001, start_handel="1", end_handel="2",
                        start_storage_height=0, end_storage_height=0))
        await db.commit()
    fw = FakeWriter()
    channel_manager._channels[imei] = fw
    _auto_reply(imei)
    async with sm() as db:
        await send_task_service.dispatch_task(db, {**idle, "lockState": 0})
        check("미잠금 -> taskLock 선행(3프레임)", len(fw.frames) == 3)
        check("첫 프레임이 taskLock(fun=B3)", bp.print_hex_string(fw.frames[0][12:13]) == "B3")
    channel_manager._channels.pop(imei, None)

    print(f"\n결과: {ok} passed, {fail} failed")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
