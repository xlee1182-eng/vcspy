"""addTask(sendTask) + 프레임 빌더 + 응답파서 검증.

운영 인프라 미접속. 채널 가짜 writer + 자동응답으로 TCP 송신/응답 상관까지 검증.
실행: python tests/test_send_task.py
"""
from __future__ import annotations

import asyncio
from datetime import datetime

import fakeredis.aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core import redis_constants as rc
from app.models.tables import Sequence, SiteManage, UserTask
from app.schemas.task import TaskWayPointsForm, WebTaskAddForm
from app.services.send_task import send_task_service
from app.services.user_task import user_task_service
from app.tcp import byte_process as bp
from app.tcp.channel_manager import channel_manager
from app.tcp.response_parser import is_0xff_or_0x00
from app.tcp.tcp_client import TaskModel
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
        self._buf = bytearray()

    def write(self, data):
        self._buf.extend(data)
        self.frames.append(bytes(data))


# ---------- 프레임 빌더 단위 검증 ----------
def test_builders():
    class UT:
        user_task_id = 123
        start_site_code = 5001
        start_handel = "1"
        start_storage_height = 10
        end_site_code = 6001
        end_handel = "2"
        end_storage_height = 20

    frame = send_task_service.append_task_msg(UT, 1001, None)
    fb = bp.hex_string_to_bytes(frame)
    check("appendTaskMsg 헤더 40BF807F", frame.startswith("40BF807F"))
    check("appendTaskMsg fun=B2", bp.print_hex_string(fb[12:13]) == "B2")
    check("appendTaskMsg userTaskId", bp.bytes_to_int(fb[4:8], 4) == 123)
    check("appendTaskMsg 종단 50AFA05F", fb[-4:] == bytes([0x50, 0xAF, 0xA0, 0x5F]))

    way = send_task_service.append_way_points_task_msg(
        [{"siteCode": 7000, "siteHandel": "1", "storageHeight": 5}]
    )
    check("wayPoints 길이(7바이트=14hex)", len(way) == 14)

    appended = send_task_service.append_task(UT, 1001, None)
    check("appendTask 2프레임", len(appended) == 2)
    sb = bp.hex_string_to_bytes(appended[1])
    check("startTaskCmd fun=07", bp.print_hex_string(sb[12:13]) == "07")


# ---------- 응답파서 검증 ----------
def test_parser():
    # B2 성공: flag(byte15=resp[30:32])="FF"
    task = TaskModel()
    task.funCode = "B2"
    # head(8)+msgNo(8)+imei(8)+fun(2)=26, byte13=00 byte14=00 byte15=FF
    task.responseMsg = "20BF407F00000001000003E9B2" + "0000FF" + "0" * 20
    r = is_0xff_or_0x00(task)
    check("응답파서 B2 FF -> 성공", r.status is True)

    # B2 실패: flag=01 -> 숫자 매핑
    task.responseMsg = "20BF407F00000001000003E9B2" + "000001" + "0" * 20
    r = is_0xff_or_0x00(task)
    check("응답파서 B2 비FF -> 실패", r.status is False and r.msg == "1")


# ---------- addTask 통합 ----------
async def setup() -> async_sessionmaker[AsyncSession]:
    redis_util.set_client(fakeredis.aioredis.FakeRedis(decode_responses=True))
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        for m in (UserTask, SiteManage, Sequence):
            await conn.run_sync(lambda c, mm=m: mm.__table__.create(c))
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as db:
        db.add(SiteManage(manage_id=1, site_manage_id=5001, site_manage_name="출발지"))
        db.add(SiteManage(manage_id=2, site_manage_id=6001, site_manage_name="도착지"))
        await db.commit()
    return sm


def _auto_reply_success(imei: int):
    """송신 프레임마다 funcode 위치에 맞춰 FF 성공 응답을 주입."""
    fw = channel_manager._channels[imei]
    seen = {"n": 0}

    async def loop():
        for _ in range(200):
            if len(fw.frames) > seen["n"]:
                sent = fw.frames[seen["n"]]
                seen["n"] += 1
                msg_no = bp.print_hex_string(sent[4:8])
                fun = bp.print_hex_string(sent[12:13])
                # B2/특수: flag at byte15 -> data="0000FF"; 그 외(07 등): byte14 -> data="00FF"
                from app.tcp.response_parser import _FLAG_AT_30
                data = "0000FF" if fun in _FLAG_AT_30 else "00FF"
                resp = bp.hex_string_to_bytes(
                    bp.get_crc_to_send("40BF407F" + msg_no + bp.int_to_hex(imei, 4) + fun + data, "123456789")
                )
                channel_manager.receive_msg(resp, ip="10.0.0.9")
            await asyncio.sleep(0.005)
    return asyncio.create_task(loop())


async def main() -> None:
    test_builders()
    test_parser()

    sm = await setup()
    imei = 1001

    def mem(flag="82", lock=1, start=5001, end=6001, task_flag=0):
        return json_util.to_json({
            "flag": flag, "lockState": lock, "startSiteCode": start,
            "endSiteCode": end, "taskFlag": task_flag, "deviceImei": imei,
        })

    # 장비 미연결
    async with sm() as db:
        f = WebTaskAddForm(messageId="M1", deviceImei=imei, startSiteCode=5001, endSiteCode=6001)
        r = await user_task_service.add_task(db, f)
        check("addTask 메모리없음 -> notConnected", r.resultCode == "1")

    await redis_util.redis_util.set_to_str(f"{rc.DEVICE_TASK_TABLE}{imei}", mem())

    # lockState=0 -> 코드4
    await redis_util.redis_util.set_to_str(f"{rc.DEVICE_TASK_TABLE}{imei}", mem(lock=0))
    async with sm() as db:
        r = await user_task_service.add_task(db, WebTaskAddForm(messageId="M1", deviceImei=imei, startSiteCode=5001, endSiteCode=6001))
        check("addTask 키보드미잠금 -> code4", r.resultCode == "4")

    await redis_util.redis_util.set_to_str(f"{rc.DEVICE_TASK_TABLE}{imei}", mem())

    # start==end
    async with sm() as db:
        r = await user_task_service.add_task(db, WebTaskAddForm(messageId="M1", deviceImei=imei, startSiteCode=5001, endSiteCode=5001))
        check("addTask 시작=종료 -> 실패", r.resultCode == "1")

    # 정상 송신 (자동응답 FF)
    channel_manager._channels[imei] = FakeWriter()
    _auto_reply_success(imei)
    async with sm() as db:
        r = await user_task_service.add_task(
            db, WebTaskAddForm(messageId="M-OK", deviceImei=imei, startSiteCode=5001, endSiteCode=6001,
                               startHandel="1", endHandel="2",
                               taskWayPoints=[TaskWayPointsForm(siteCode=7000, siteHandel="1", storageHeight=3)])
        )
        check("addTask 정상 -> success(messageId)", r.is_success() and r.data == "M-OK")
    async with sm() as db:
        t = await user_task_service.get_task_info(db, None, "M-OK")
        check("addTask 후 send_flag='2'", t and t["send_flag"] == "2")

    # 중복 messageId
    channel_manager._channels[imei] = FakeWriter()
    _auto_reply_success(imei)
    async with sm() as db:
        r = await user_task_service.add_task(db, WebTaskAddForm(messageId="M-OK", deviceImei=imei, startSiteCode=5001, endSiteCode=6001))
        check("addTask 중복 messageId -> code5", r.resultCode == "5")
    channel_manager._channels.pop(imei, None)

    print(f"\n결과: {ok} passed, {fail} failed")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
