"""User 서비스 검증 (로컬 인메모리 SQLite, 운영 DB와 무관).

운영 MySQL(yg_vcs_cloud)에 절대 접속하지 않는다.
임시 sqlite 메모리 DB에 sys_user 테이블만 만들어 로직을 검증한다.
실행: python tests/test_user_service.py
"""
from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.models.tables import SysUser
from app.schemas.user import UserEditForm, UserLoginForm
from app.services.user import user_service


async def _setup() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        # 임시 테스트 DB에만 sys_user 테이블 생성
        await conn.run_sync(lambda c: SysUser.__table__.create(c))
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as db:
        db.add(SysUser(user_id=1, user_name="admin", password="1234", client_type="3"))
        await db.commit()
    return sm


async def main() -> None:
    sm = await _setup()
    ok = 0
    fail = 0

    def check(name: str, cond: bool) -> None:
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"  PASS {name}")
        else:
            fail += 1
            print(f"  FAIL {name}")

    # 1) 로그인 성공
    async with sm() as db:
        r = await user_service.user_login(db, UserLoginForm(userName="admin", password="1234"))
        check("login 성공 -> code 0", r.is_success())
        check("login 성공 -> 비밀번호 미노출", "password" not in (r.data or {}))

    # 2) 없는 사용자
    async with sm() as db:
        r = await user_service.user_login(db, UserLoginForm(userName="nobody", password="1234"))
        check("없는 사용자 -> USER_NAME_ERR", r.resultCode == "1" and "Username error" in r.resultMsg)

    # 3) 비밀번호 오류
    async with sm() as db:
        r = await user_service.user_login(db, UserLoginForm(userName="admin", password="wrong"))
        check("비번 오류 -> USER_PWD_ERR", r.resultCode == "1" and "Wrong password" in r.resultMsg)

    # 4) 비밀번호 변경 성공 후 새 비번 로그인
    async with sm() as db:
        r = await user_service.edit_password(
            db, UserEditForm(userName="admin", password="1234", newPassword="5678")
        )
        check("비번 변경 -> code 0", r.is_success())
    async with sm() as db:
        r = await user_service.user_login(db, UserLoginForm(userName="admin", password="5678"))
        check("변경된 비번으로 로그인", r.is_success())

    # 5) 기존(틀린) 비번으로 변경 시도 실패
    async with sm() as db:
        r = await user_service.edit_password(
            db, UserEditForm(userName="admin", password="oldwrong", newPassword="x")
        )
        check("틀린 기존비번 -> NAME_PWD_ERR", r.resultCode == "1")

    print(f"\n결과: {ok} passed, {fail} failed")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
