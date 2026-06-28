"""하트비트 메모리테이블 파싱/저장 검증.

알려진 바이트값으로 하트비트 프레임을 구성해 파싱 결과와 Redis 저장을 확인한다.
실행: python tests/test_heartbeat.py
"""
from __future__ import annotations

import asyncio

import fakeredis.aioredis

from app.core import redis_constants as rc
from app.services.device_memory_table import parse_memory_table, save_or_update_device
from app.tcp import byte_process as bp
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


def build_heartbeat(imei, user_task_id, flag_hex, start, end, fork_status=0, task_flag=0, lock=1, battery=88) -> bytes:
    """원본 오프셋에 맞춰 하트비트 프레임(>=160바이트) 구성."""
    b = bytearray(160)
    b[0:4] = bytes([0x20, 0xBF, 0x40, 0x7F])  # FRAME_RECV_HEAD
    b[4:8] = bp.int_to_bytes(user_task_id, 4)
    b[8:12] = bp.int_to_bytes(imei, 4)
    b[12] = 0x00  # fun=00
    b[14] = int(flag_hex, 16)  # flag
    b[15:18] = bp.int_to_bytes(start, 3)
    b[18:21] = bp.int_to_bytes(end, 3)
    b[25:27] = bp.int_to_bytes(120, 2)  # forkHeight
    b[29] = battery
    b[30] = fork_status & 3
    b[31] = (task_flag & 0x0F) << 4  # taskFlag at high nibble
    b[120] = (lock & 1) << 3  # lockState bit3
    b[127:129] = bp.int_to_bytes(5, 2)  # buttonNumber
    b[148] = 70  # wifiStrength
    b[151] = 2   # floor
    return bytes(b)


async def main() -> None:
    redis_util.set_client(fakeredis.aioredis.FakeRedis(decode_responses=True))

    frame = build_heartbeat(1001, 555, "82", 5001, 6001, fork_status=1, task_flag=0, lock=1, battery=88)
    t = parse_memory_table(frame)

    check("imei 파싱", t["deviceImei"] == 1001)
    check("userTaskId 파싱", t["userTaskId"] == 555)
    check("flag 파싱", t["flag"] == "82")
    check("model = flag>>6", t["model"] == (0x82 >> 6))  # 2
    check("startSiteCode", t["startSiteCode"] == 5001)
    check("endSiteCode", t["endSiteCode"] == 6001)
    check("forkHeight", t["forkHeight"] == 120)
    check("battery", t["batteryLevel"] == 88)
    check("forkStatus &3", t["forkStatus"] == 1)
    check("taskFlag >>4", t["taskFlag"] == 0)
    check("lockState bit3", t["lockState"] == 1)
    check("buttonNumber", t["buttonNumber"] == 5)
    check("wifiStrength", t["wifiStrength"] == 70)
    check("floor", t["floor"] == 2)

    # taskFlag 비0 케이스
    f2 = build_heartbeat(1001, 1, "10", 0, 0, task_flag=3, lock=0)
    t2 = parse_memory_table(f2)
    check("taskFlag=3", t2["taskFlag"] == 3)
    check("lockState=0", t2["lockState"] == 0)
    check("model(flag=10)>>6=0", t2["model"] == 0)

    # 저장 검증: DEVICE_TASK_TABLE 에 dict 저장 → 소비처가 읽는 형태
    await save_or_update_device(frame)
    stored = await redis_util.redis_util.get_str_to_object(f"{rc.DEVICE_TASK_TABLE}1001")
    check("DEVICE_TASK_TABLE 저장(dict)", isinstance(stored, dict) and stored["flag"] == "82")
    hb = await redis_util.redis_util.get_str_to_object(f"{rc.DEVICE_HEART_BEAT}1001", str)
    check("DEVICE_HEART_BEAT 저장(HEX)", isinstance(hb, str) and len(hb) > 0)
    suc = await redis_util.redis_util.get_str_to_object(f"{rc.DEVICE_TABLE_PREXFIX}1001")
    check("deviceTable_suc 저장", isinstance(suc, dict) and suc["deviceImei"] == 1001)

    print(f"\n결과: {ok} passed, {fail} failed")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
