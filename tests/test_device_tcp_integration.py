"""Device initLocation/terminateTask 통합 검증 (TCP 응답 시뮬레이션).

운영 인프라 미접속. 채널에 가짜 writer 를 등록하고, 송신 직후 응답을 주입해
요청/응답 상관까지 포함한 흐름을 검증한다.
실행: python tests/test_device_tcp_integration.py
"""
from __future__ import annotations

import asyncio
from datetime import datetime

import fakeredis.aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core import redis_constants as rc
from app.models.tables import Device, ForkliftLine
from app.schemas.device import DeviceInitForm, DeviceTerminateForm
from app.services.device import device_service
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
        self.sent = bytearray()

    def write(self, data):
        self.sent.extend(data)


async def setup() -> async_sessionmaker[AsyncSession]:
    redis_util.set_client(fakeredis.aioredis.FakeRedis(decode_responses=True))
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        for m in (Device, ForkliftLine):
            await conn.run_sync(lambda c, mm=m: mm.__table__.create(c))
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as db:
        db.add(ForkliftLine(forklift_line_id=1, device_imei=1001, start_site_code=100,
                            end_site_code=200, step_number=2, return_line_id=55))
        await db.commit()
    return sm


def _auto_reply(imei: int):
    """송신된 프레임에서 msgNo/fun 을 읽어 같은 상관키로 응답을 주입."""
    fw = channel_manager._channels[imei]

    async def reply():
        for _ in range(100):
            if fw.sent:
                break
            await asyncio.sleep(0.01)
        sent = bytes(fw.sent)
        msg_no_hex = bp.print_hex_string(sent[4:8])
        fun = bp.print_hex_string(sent[12:13])  # 송신 프레임의 실제 fun
        resp = bp.hex_string_to_bytes(
            bp.get_crc_to_send("40BF807F" + msg_no_hex + bp.int_to_hex(imei, 4) + fun + "FF00", "123456789")
        )
        channel_manager.receive_msg(resp, ip="10.0.0.9")
    return asyncio.create_task(reply())


async def main():
    sm = await setup()

    # --- initLocation: 메모리테이블 미존재 -> notConnected ---
    async with sm() as db:
        r = await device_service.init_location(db, DeviceInitForm(deviceImei=1001, siteCode=200))
        check("initLocation 메모리없음 -> notConnected", r.resultCode == "1" and "not connected" in r.resultMsg)

    # 메모리테이블 등록(유휴 flag=77)
    await redis_util.redis_util.set_to_str(
        f"{rc.DEVICE_TASK_TABLE}1001", json_util.to_json({"flag": "77", "deviceImei": 1001})
    )

    # --- initLocation: 비유휴 상태 차단 ---
    await redis_util.redis_util.set_to_str(
        f"{rc.DEVICE_TASK_TABLE}1002", json_util.to_json({"flag": "10", "deviceImei": 1002})
    )
    async with sm() as db:
        r = await device_service.init_location(db, DeviceInitForm(deviceImei=1002, siteCode=200))
        check("initLocation 비유휴 -> notIdle", r.resultCode == "1" and "not idle" in r.resultMsg)

    # --- initLocation: 정상 (채널 등록 + 응답 시뮬) ---
    channel_manager._channels[1001] = FakeWriter()
    _auto_reply(1001)
    async with sm() as db:
        r = await device_service.init_location(db, DeviceInitForm(deviceImei=1001, siteCode=200))
        check("initLocation 정상 -> success", r.is_success())
    channel_manager._channels.pop(1001, None)

    # --- initLocation: 학습라인 없음 ---
    await redis_util.redis_util.set_to_str(
        f"{rc.DEVICE_TASK_TABLE}1003", json_util.to_json({"flag": "78", "deviceImei": 1003})
    )
    channel_manager._channels[1003] = FakeWriter()
    async with sm() as db:
        r = await device_service.init_location(db, DeviceInitForm(deviceImei=1003, siteCode=999))
        check("initLocation 라인없음 -> NotLearn", r.resultCode == "1" and "route" in r.resultMsg.lower())
    channel_manager._channels.pop(1003, None)

    # --- terminateTask: 정상 ---
    channel_manager._channels[1001] = FakeWriter()
    _auto_reply(1001)
    async with sm() as db:
        r = await device_service.terminate_task(db, DeviceTerminateForm(deviceImei=1001))
        check("terminateTask 정상 -> success", r.is_success())
    channel_manager._channels.pop(1001, None)

    # --- terminateTask: 메모리없음 ---
    async with sm() as db:
        r = await device_service.terminate_task(db, DeviceTerminateForm(deviceImei=7777))
        check("terminateTask 메모리없음 -> notConnected", r.resultCode == "1")

    print(f"\n결과: {ok} passed, {fail} failed")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
