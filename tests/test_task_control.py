"""setKeyboardLock / setTask / sendRepeatTask 검증.

운영 인프라 미접속. 채널 가짜 writer + 자동응답으로 검증.
실행: python tests/test_task_control.py
"""
from __future__ import annotations

import asyncio
from datetime import datetime

import fakeredis.aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core import redis_constants as rc
from app.models.tables import UserTask
from app.schemas.task import KeyboardLockSetForm, TaskRepeatSendForm, TaskSetForm
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


def _auto_reply_success(imei: int):
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
            await asyncio.sleep(0.005)
    return asyncio.create_task(loop())


async def setup() -> async_sessionmaker[AsyncSession]:
    redis_util.set_client(fakeredis.aioredis.FakeRedis(decode_responses=True))
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: UserTask.__table__.create(c))
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as db:
        db.add(UserTask(user_task_id=500, device_imei=1001, message_id="MSG-A",
                        send_flag="2", start_site_code=5001, end_site_code=6001,
                        start_handel="1", end_handel="2", start_storage_height=0,
                        end_storage_height=0, created_time=datetime(2024, 1, 1)))
        await db.commit()
    return sm


def _mem(imei, flag="10", lock=1, model=2, user_task_id=500, start=5001, end=6001, task_flag=0):
    return json_util.to_json({
        "flag": flag, "lockState": lock, "model": model, "userTaskId": user_task_id,
        "startSiteCode": start, "endSiteCode": end, "taskFlag": task_flag, "deviceImei": imei,
    })


async def main() -> None:
    sm = await setup()
    imei = 1001

    # --- setKeyboardLock ---
    async with sm() as db:
        r = await user_task_service.set_keyboard_lock(db, KeyboardLockSetForm(deviceImei=imei, lockState=1))
        check("setKeyboardLock 메모리없음 -> notConnected", r.resultCode == "1")

    await redis_util.redis_util.set_to_str(f"{rc.DEVICE_TASK_TABLE}{imei}", _mem(imei, flag="10"))
    channel_manager._channels[imei] = FakeWriter()
    _auto_reply_success(imei)
    async with sm() as db:
        r = await user_task_service.set_keyboard_lock(db, KeyboardLockSetForm(deviceImei=imei, lockState=1))
        check("setKeyboardLock 정상 -> success", r.is_success())
    channel_manager._channels.pop(imei, None)

    # flag 부적합(77) -> unknownPosition
    await redis_util.redis_util.set_to_str(f"{rc.DEVICE_TASK_TABLE}{imei}", _mem(imei, flag="77"))
    async with sm() as db:
        r = await user_task_service.set_keyboard_lock(db, KeyboardLockSetForm(deviceImei=imei, lockState=1))
        check("setKeyboardLock flag=77 -> 실패", r.resultCode == "1")

    # --- setTask: 종료('3') + 미수행 -> DB 취소(7) ---
    await redis_util.redis_util.set_to_str(f"{rc.DEVICE_TASK_TABLE}{imei}", _mem(imei, model=2, user_task_id=999))
    async with sm() as db:
        r = await user_task_service.set_task(db, TaskSetForm(messageId="MSG-A", taskState="3"))
        check("setTask 종료+미수행 -> 취소 성공", r.is_success())
    async with sm() as db:
        from app.repositories.task import user_task_repository
        t = await user_task_repository.select_by_pk(db, 500)
        check("setTask 취소 후 send_flag=7", t.send_flag == "7")

    # setTask: 없는 작업
    async with sm() as db:
        r = await user_task_service.set_task(db, TaskSetForm(messageId="NOPE", taskState="1"))
        check("setTask 없는작업 -> TaskNotExit", r.resultCode == "1")

    # setTask: 시작('1') + 수행중(userTaskId 일치, model=2) -> startOrPause 송신
    await redis_util.redis_util.set_to_str(f"{rc.DEVICE_TASK_TABLE}{imei}", _mem(imei, model=2, user_task_id=500))
    channel_manager._channels[imei] = FakeWriter()
    _auto_reply_success(imei)
    async with sm() as db:
        r = await user_task_service.set_task(db, TaskSetForm(messageId="MSG-A", taskState="1"))
        check("setTask 시작 -> success", r.is_success())
    channel_manager._channels.pop(imei, None)

    # --- sendRepeatTask: 정상 재송신 ---
    await redis_util.redis_util.set_to_str(f"{rc.DEVICE_TASK_TABLE}{imei}", _mem(imei, flag="82"))
    channel_manager._channels[imei] = FakeWriter()
    _auto_reply_success(imei)
    async with sm() as db:
        r = await user_task_service.send_repeat_task(db, TaskRepeatSendForm(messageId="MSG-A"))
        check("sendRepeatTask 정상 -> success", r.is_success())
    channel_manager._channels.pop(imei, None)

    # sendRepeatTask: 키보드 미잠금 -> code4
    await redis_util.redis_util.set_to_str(f"{rc.DEVICE_TASK_TABLE}{imei}", _mem(imei, flag="82", lock=0))
    async with sm() as db:
        r = await user_task_service.send_repeat_task(db, TaskRepeatSendForm(messageId="MSG-A"))
        check("sendRepeatTask 미잠금 -> code4", r.resultCode == "4")

    print(f"\n결과: {ok} passed, {fail} failed")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
