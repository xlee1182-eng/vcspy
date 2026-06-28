"""카메라 점유상태 처리(비전) 검증.

점유 비트 분해 + 디바운스(5회) + 보관위치 상태 갱신.
실행: python tests/test_camera.py
"""
from __future__ import annotations

import asyncio

import fakeredis.aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core import redis_constants as rc
from app.models.tables import (
    Device,
    Storage,
    StorageDeviceRelation,
    TaskTemplate,
    TaskTempSite,
    TaskTempDevice,
    UserTask,
    Sequence,
    SiteManage,
)
from app.services.camera_table import camera_table_service
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


async def setup() -> async_sessionmaker[AsyncSession]:
    redis_util.set_client(fakeredis.aioredis.FakeRedis(decode_responses=True))
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        for m in (Device, Storage, StorageDeviceRelation, TaskTemplate, TaskTempSite,
                  TaskTempDevice, UserTask, Sequence, SiteManage):
            await conn.run_sync(lambda c, mm=m: mm.__table__.create(c))
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as db:
        # 카메라(type=2) 등록
        db.add(Device(device_imei="12120002", device_name="CAM", type="2", is_enable="0", action="1"))
        # 슬롯1(order_no=1) → site_code 52900 바인딩
        db.add(StorageDeviceRelation(storage_device_relation_id=1, device_imei="12120002",
                                     order_no=1, site_code=52900, device_name="CAM"))
        # 보관위치 52900 (현재 상태 0=빈자리)
        db.add(Storage(storage_id=1, storage_name="C1", site_code=52900, site_status="0", is_enable="0"))
        await db.commit()
    return sm


async def main() -> None:
    sm = await setup()
    cam = 12120002

    # bytes_to_binary 동작
    check("bytes_to_binary(0x0F)", bp.bytes_to_binary(bytes([0, 0, 0, 0x0F])) == "1111")

    # 슬롯 분해: storageCount=1, state bit=1 (점유) → 슬롯1 상태 "1"
    # 첫 관측: 캐시만 생성(60s), 아직 갱신 안 함
    async with sm() as db:
        await camera_table_service.is_update_storage(db, cam, 1, "1")
    cs = await redis_util.redis_util.get_str_to_object(f"{rc.CAMERA_STATES}{cam}1")
    check("첫 관측 -> 캐시 생성(number=1)", isinstance(cs, dict) and cs["number"] == 1 and cs["state"] == "1")

    # 디바운스: 같은 상태 반복 관측 → number 증가, 5회 전엔 미적용
    async with sm() as db:
        for _ in range(3):
            await camera_table_service.is_update_storage(db, cam, 1, "1")
    cs = await redis_util.redis_util.get_str_to_object(f"{rc.CAMERA_STATES}{cam}1")
    check("반복 관측 -> number 증가(<5)", isinstance(cs, dict) and 1 < cs["number"] < 5)
    async with sm() as db:
        from app.repositories.site import storage_repository
        s = (await storage_repository.select(db, {"site_code": 52900}))[0]
        check("5회 전 -> 상태 미변경(여전히 0)", s.site_status == "0")

    # 5회 이상 → 적용: editScanStorageStatus 경유로 상태 반영 + OLD_CAMERA_STATE 기록
    async with sm() as db:
        for _ in range(4):
            await camera_table_service.is_update_storage(db, cam, 1, "1")
    old = await redis_util.redis_util.get_str_to_object(f"{rc.OLD_CAMERA_STATE}{cam}1", str)
    check("5회 이상 -> OLD_CAMERA_STATE 기록", old == "1")

    # 같은 상태 재관측 → oldCameraState 동일이라 즉시 스킵
    async with sm() as db:
        await camera_table_service.is_update_storage(db, cam, 1, "1")
        check("동일 oldState -> 스킵(예외없음)", True)

    # 미등록 카메라 -> 무시
    async with sm() as db:
        await camera_table_service.is_update_storage(db, 99999999, 1, "1")
        check("미등록 카메라 -> 무시", True)

    # analyzingStorageState: 2슬롯 비트 분해 (state=0b10 → 슬롯1=0, 슬롯2=1)
    async with sm() as db:
        db.add(StorageDeviceRelation(storage_device_relation_id=2, device_imei="12120002",
                                     order_no=2, site_code=53000, device_name="CAM"))
        db.add(Storage(storage_id=2, storage_name="C2", site_code=53000, site_status="0", is_enable="0"))
        await db.commit()
    async with sm() as db:
        await camera_table_service.analyzing_storage_state(db, cam, 2, bytes([0, 0, 0, 0b10]))
        cs2 = await redis_util.redis_util.get_str_to_object(f"{rc.CAMERA_STATES}{cam}2")
        check("2슬롯 분해: 슬롯2 상태=1 관측", isinstance(cs2, dict) and cs2["state"] == "1")

    print(f"\n결과: {ok} passed, {fail} failed")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
