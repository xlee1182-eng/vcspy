"""Storage/Site 서비스 검증 (인메모리 SQLite + fakeredis).

운영 인프라 미접속. 실행: python tests/test_storage_service.py
"""
from __future__ import annotations

import asyncio
from datetime import datetime

import fakeredis.aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.tables import Device, SiteManage, Storage, StorageDeviceRelation
from app.schemas.site import (
    SiteEditForm,
    SiteInfoForm,
    StorageDeviceAddForm,
    StorageDeviceDelForm,
    StorageDeviceInfoForm,
    StorageInfo,
)
from app.services.storage import storage_device_relation_service, storage_service
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
        for model in (Device, Storage, StorageDeviceRelation, SiteManage):
            await conn.run_sync(lambda c, m=model: m.__table__.create(c))
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as db:
        db.add(Device(device_imei="1001", device_name="AGV-1", type="1", is_enable="0", action="2"))
        db.add(Storage(storage_id=10, storage_name="A1", site_code=5001, site_name="A1",
                       site_status="0", site_type="2", is_enable="0", created_date=datetime(2024, 1, 1)))
        db.add(Storage(storage_id=11, storage_name="A2", site_code=5002, site_name="A2",
                       site_status="0", site_type="1", is_enable="0", created_date=datetime(2024, 1, 2)))
        await db.commit()
    return sm


async def main() -> None:
    sm = await setup()

    # 1) getSiteInfo: 2개, 바인딩 장비정보는 아직 없음
    async with sm() as db:
        r = await storage_service.get_site_info(db, SiteInfoForm())
        check("getSiteInfo 2건", len(r.data) == 2)
        check("getSiteInfo 정렬(site_type asc)", r.data[0]["site_type"] == "1")
        check("getSiteInfo 미바인딩 deviceImei None", r.data[0]["deviceImei"] is None)

    # 2) editStorageDevice: 1001 에 5001,5002 바인딩
    async with sm() as db:
        r = await storage_device_relation_service.edit_storage_device(
            db, StorageDeviceAddForm(
                deviceImei="1001", type="1", deviceName="AGV-1", userName="admin",
                storageInfos=[StorageInfo(siteCode=5001, siteName="A1", siteType="2", orderNo=1),
                              StorageInfo(siteCode=5002, siteName="A2", siteType="1", orderNo=2)],
            ))
        check("editStorageDevice 성공", r.is_success())

    # 3) getSiteByDevice: 2건, order_no 정렬
    async with sm() as db:
        r = await storage_service.get_site_by_device(db, StorageDeviceInfoForm(deviceImei="1001"))
        check("getSiteByDevice 2건", len(r.data) == 2)
        check("getSiteByDevice 정렬", r.data[0]["order_no"] == 1)

    # 4) 다른 장비가 같은 site_code 바인딩 시도 -> 충돌 실패
    async with sm() as db:
        db.add(Device(device_imei="1002", device_name="AGV-2", type="1", is_enable="0", action="2"))
        await db.commit()
        r = await storage_device_relation_service.edit_storage_device(
            db, StorageDeviceAddForm(
                deviceImei="1002", type="1", deviceName="AGV-2",
                storageInfos=[StorageInfo(siteCode=5001, siteName="A1", siteType="2", orderNo=1)],
            ))
        check("다른장비 중복바인딩 -> 실패", r.resultCode == "1" and "bound" in r.resultMsg.lower())

    # 5) getSiteInfo 후 바인딩 장비정보 합성됨
    async with sm() as db:
        r = await storage_service.get_site_info(db, SiteInfoForm())
        s5001 = next(x for x in r.data if x["site_code"] == 5001)
        check("getSiteInfo 바인딩 후 deviceImei 합성", s5001["deviceImei"] == "1001")

    # 6) editStorage: 이름/사용여부 변경
    async with sm() as db:
        r = await storage_service.edit_storage(db, SiteEditForm(storageId="10", siteName="A1-rn", isEnable="1", userName="admin"))
        check("editStorage 성공", r.is_success())
    async with sm() as db:
        s = await storage_service.get_storage_by_code(db, 5001)
        check("editStorage 반영", s.site_name == "A1-rn" and s.is_enable == "1")

    # 7) editStorageRowStatus: site_code 상태 일괄 변경
    async with sm() as db:
        await storage_service.edit_storage_row_status(db, 5002, "2")
        s = await storage_service.get_storage_by_code(db, 5002)
        check("editStorageRowStatus 반영", s.site_status == "2")

    # 8) delStorageDevice
    async with sm() as db:
        r = await storage_device_relation_service.del_storage_device(db, StorageDeviceDelForm(siteCode=5001))
        check("delStorageDevice 성공", r.is_success())
    async with sm() as db:
        r = await storage_service.get_site_by_device(db, StorageDeviceInfoForm(deviceImei="1001"))
        check("delStorageDevice 후 1건", len(r.data) == 1)

    # 9) appendStorage(순수 객체 구성)
    sm_e = SiteManage(manage_id=1, site_manage_id=7000, site_manage_name="새위치", site_attr="9",
                      created_by="admin", created_date=datetime(2024, 1, 1))
    st = storage_service.append_storage(sm_e)
    check("appendStorage site_type(9->1)", st.site_type == "1" and st.site_code == 7000 and st.is_enable == "0")

    # 10) editStorageStatus(actionType='1' -> 단순 상태갱신, 작업생성 없음)
    async with sm() as db:
        r = await storage_service.edit_storage_status(db, "0", "0", 5002, "1", "1")
        check("editStorageStatus actionType=1 -> 상태갱신", r.is_success())
        s = await storage_service.get_storage_by_code(db, 5002)
        check("editStorageStatus 상태 반영", s.site_status == "1")

    # 11) editStorageStatus 미존재 사이트 -> noStorage
    async with sm() as db:
        r = await storage_service.edit_storage_status(db, "0", "0", 99999, "1", "1")
        check("editStorageStatus 미존재 -> noStorage", r.resultCode == "1")

    print(f"\n결과: {ok} passed, {fail} failed")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
