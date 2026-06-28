"""앱 통합 테스트 (HTTP 요청 → 라우터 → 서비스 → DB).

운영 인프라 미접속: get_db 를 인메모리 SQLite 로, redis 를 fakeredis 로 오버라이드.
실행: python tests/test_app_integration.py
"""
from __future__ import annotations

import asyncio
import os

os.environ["YGVCS_PRIMARY_SERVER_ENABLED"] = "false"
os.environ["YGVCS_SCHEDULER_ENABLED"] = "false"

import fakeredis.aioredis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.models.tables import Storage, StorageDeviceRelation, SysUser
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


async def _prepare():
    redis_util.set_client(fakeredis.aioredis.FakeRedis(decode_responses=True))
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        for m in (SysUser, Storage, StorageDeviceRelation):
            await conn.run_sync(lambda c, mm=m: mm.__table__.create(c))
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as db:
        db.add(SysUser(user_id=1, user_name="admin", password="1234", client_type="3"))
        await db.commit()
    return sm


def main() -> None:
    sm = asyncio.run(_prepare())

    async def override_get_db():
        async with sm() as session:
            yield session

    from fastapi.testclient import TestClient
    from app.main import app

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        # health
        check("GET /health 200", client.get("/health").status_code == 200)

        # userLogin 성공
        r = client.post("/service/warp/user/userLogin", json={"userName": "admin", "password": "1234"})
        body = r.json()
        check("userLogin 성공 200/code0", r.status_code == 200 and body["resultCode"] == "0")
        check("userLogin data.userName", body["data"]["userName"] == "admin")
        check("userLogin 비밀번호 미노출", "password" not in (body["data"] or {}))

        # userLogin 비번 오류
        r = client.post("/service/warp/user/userLogin", json={"userName": "admin", "password": "x"})
        check("userLogin 비번오류 code1", r.json()["resultCode"] == "1")

        # 폼 검증(빈 입력)
        r = client.post("/service/warp/user/userLogin", json={})
        check("userLogin 빈입력 code1", r.json()["resultCode"] == "1")

        # getSiteInfo (빈 목록)
        r = client.post("/service/warp/site/getSiteInfo", json={})
        b = r.json()
        check("getSiteInfo 200/success", r.status_code == 200 and b["resultCode"] == "0")

        # editPassword
        r = client.post("/service/warp/user/editPassword",
                        json={"userName": "admin", "password": "1234", "newPassword": "5678"})
        check("editPassword 성공", r.json()["resultCode"] == "0")
        r = client.post("/service/warp/user/userLogin", json={"userName": "admin", "password": "5678"})
        check("변경된 비번 로그인", r.json()["resultCode"] == "0")

    app.dependency_overrides.clear()
    print(f"\n결과: {ok} passed, {fail} failed")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
