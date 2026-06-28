"""callDeviceTask / sendPointsTask 검증.

실행: python tests/test_task_warp.py
"""
from __future__ import annotations

import asyncio

import fakeredis.aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core import redis_constants as rc
from app.models.tables import Sequence, UserTask
from app.schemas.task import TaskCallForm, TaskPointsForm
from app.services.user_task import user_task_service
from app.tcp import byte_process as bp
from app.tcp.channel_manager import channel_manager
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
        for _ in range(300):
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
            await asyncio.sleep(0.004)
    return asyncio.create_task(loop())


async def setup() -> async_sessionmaker[AsyncSession]:
    redis_util.set_client(fakeredis.aioredis.FakeRedis(decode_responses=True))
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        for m in (UserTask, Sequence):
            await conn.run_sync(lambda c, mm=m: mm.__table__.create(c))
    return async_sessionmaker(engine, expire_on_commit=False)


async def main() -> None:
    sm = await setup()

    # ---------- callDeviceTask ----------
    async with sm() as db:
        r = await user_task_service.call_device_task(db, TaskCallForm(siteCode=5001, callType="0", userName="op"))
        check("callDeviceTask 생성 성공", r.is_success())
    async with sm() as db:
        from app.repositories.task import user_task_repository
        rows = await user_task_repository.select_all(db)
        check("호출작업 1건(taskType=4,flag=1)", len(rows) == 1 and rows[0].task_type == "4" and rows[0].send_flag == "1")

    # 이미 호출작업 존재 -> 중복 거부
    async with sm() as db:
        r = await user_task_service.call_device_task(db, TaskCallForm(siteCode=5002, callType="0"))
        check("호출작업 중복 -> callTaskIsExists", r.resultCode == "1" and "call task" in r.resultMsg)

    # siteCode 누락
    async with sm() as db:
        r = await user_task_service.call_device_task(db, TaskCallForm(siteCode=None, callType="0"))
        check("callDeviceTask siteCode 누락 -> 실패", r.resultCode == "1")

    # ---------- sendPointsTask ----------
    imei = 1001
    # 메모리 미연결
    async with sm() as db:
        r = await user_task_service.send_points_task(db, TaskPointsForm(deviceImei=imei, startSiteCode=5001, endSiteCode=6001))
        check("sendPointsTask 미연결 -> notConnected", r.resultCode == "1")

    await redis_util.redis_util.set_to_str(f"{rc.DEVICE_TASK_TABLE}{imei}", json_util.to_json({
        "flag": "82", "lockState": 1, "startSiteCode": 5001, "endSiteCode": 6001, "taskFlag": 0, "deviceImei": imei,
    }))

    # 정상 송신
    channel_manager._channels[imei] = FakeWriter()
    _auto_reply(imei)
    async with sm() as db:
        r = await user_task_service.send_points_task(
            db, TaskPointsForm(deviceImei=imei, startSiteCode=5001, endSiteCode=6001,
                               startHandel="1", endHandel="2", userName="op")
        )
        check("sendPointsTask 정상 -> success", r.is_success())
    async with sm() as db:
        from app.repositories.task import user_task_repository
        pts = [t for t in await user_task_repository.select_all(db) if t.task_type == "1"]
        check("sendPointsTask 저장(taskType=1)", len(pts) == 1 and pts[0].start_site_code == 5001)
    channel_manager._channels.pop(imei, None)

    print(f"\n결과: {ok} passed, {fail} failed")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
