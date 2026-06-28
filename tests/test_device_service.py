"""Device 서비스 검증 (인메모리 SQLite + fakeredis, 운영 인프라 미접속).

운영 MySQL/Redis 에 접속하지 않는다.
실행: python tests/test_device_service.py
"""
from __future__ import annotations

import asyncio

import fakeredis.aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.tables import Device, StorageDeviceRelation, TaskTempDevice
from app.schemas.device import DeviceAddForm, DeviceDelForm, DeviceEditForm, DeviceInfoForm
from app.services.device import device_service
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
        for model in (Device, StorageDeviceRelation, TaskTempDevice):
            await conn.run_sync(lambda c, m=model: m.__table__.create(c))
    return async_sessionmaker(engine, expire_on_commit=False)


async def main() -> None:
    sm = await setup()

    # 1) 장비 추가 성공
    async with sm() as db:
        r = await device_service.add_device(
            db, DeviceAddForm(deviceImei="1001", deviceName="AGV-1", type="1", isEnable="0", userName="admin")
        )
        check("addDevice 성공", r.is_success())

    # 2) 중복 IMEI
    async with sm() as db:
        r = await device_service.add_device(
            db, DeviceAddForm(deviceImei="1001", deviceName="AGV-x", type="1", isEnable="0")
        )
        check("addDevice 중복 IMEI -> imeiExists", r.resultCode == "1" and "IMEI already exists" in r.resultMsg)

    # 3) 중복 이름
    async with sm() as db:
        r = await device_service.add_device(
            db, DeviceAddForm(deviceImei="1002", deviceName="AGV-1", type="1", isEnable="0")
        )
        check("addDevice 중복 이름 -> nameExists", r.resultCode == "1" and "name already exists" in r.resultMsg)

    # 4) 카메라(type=2) action 누락
    async with sm() as db:
        r = await device_service.add_device(
            db, DeviceAddForm(deviceImei="2001", deviceName="CAM-1", type="2", isEnable="0")
        )
        check("addDevice 카메라 action 누락 -> actionNotNull", r.resultCode == "1")

    # 5) getDeviceInfo: type별 분류 + flag 합성(메모리테이블 없으면 FF)
    async with sm() as db:
        r = await device_service.get_device_info(db, DeviceInfoForm())
        agv = (r.data or {}).get("deviceAGV") or []
        check("getDeviceInfo AGV 1대", len(agv) == 1)
        check("getDeviceInfo flag=FF(메모리없음)", agv and agv[0]["flag"] == "FF")

    # 6) editDevice: 이름 변경
    async with sm() as db:
        r = await device_service.edit_device(
            db, DeviceEditForm(deviceImei="1001", deviceName="AGV-1-rn", isEnable="1", userName="admin")
        )
        check("editDevice 성공", r.is_success())
    async with sm() as db:
        d = await device_service.get_device_info(db, DeviceInfoForm())
        agv = (d.data or {}).get("deviceAGV") or []
        check("editDevice 반영(이름/사용여부)", agv and agv[0]["device_name"] == "AGV-1-rn" and agv[0]["is_enable"] == "1")

    # 7) editDevice 없는 장비
    async with sm() as db:
        r = await device_service.edit_device(db, DeviceEditForm(deviceImei="9999"))
        check("editDevice 없는 장비 -> noDevice", r.resultCode == "1")

    # 8) delDevice
    async with sm() as db:
        r = await device_service.del_device(db, DeviceDelForm(deviceImei="1001"))
        check("delDevice 성공", r.is_success())
    async with sm() as db:
        d = await device_service.get_device_info(db, DeviceInfoForm())
        agv = (d.data or {}).get("deviceAGV") or []
        check("delDevice 후 AGV 0대", len(agv) == 0)

    # 9) getAgvHeartList: 하트비트 키 파싱
    #   redis 값 형식: 따옴표 포함 hex 문자열, [17:25] 구간이 imei(4byte hex)
    r = await redis_util.redis_util.set_to_str("device_heart_beat1001", '"20BF407F0000000012F78B89"')
    async with sm() as db:
        res = await device_service.get_agv_heart_list(DeviceInfoForm())
        check("getAgvHeartList 1건", isinstance(res.data, list) and len(res.data) == 1)
        check("getAgvHeartList imei 파싱", bool(res.data) and res.data[0]["deviceImei"] == 0x12F78B89)

    print(f"\n결과: {ok} passed, {fail} failed")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
