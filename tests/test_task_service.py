"""Task 템플릿 서비스 검증 (인메모리 SQLite).

운영 인프라 미접속. 실행: python tests/test_task_service.py
"""
from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.tables import (
    TaskTempDevice,
    TaskTempSite,
    TaskTempSpareSite,
    TaskTemplate,
)
from app.schemas.task import DeviceReg, SiteForm, TaskAddForm, TaskEditForm, TaskEditInfoForm
from app.services.task import task_service

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
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        for m in (TaskTemplate, TaskTempSite, TaskTempDevice, TaskTempSpareSite):
            await conn.run_sync(lambda c, mm=m: mm.__table__.create(c))
    return async_sessionmaker(engine, expire_on_commit=False)


def _add_form() -> TaskAddForm:
    return TaskAddForm(
        taskName="템플릿A", userId="u1", userName="admin",
        startSites=[SiteForm(siteCode=5001, storageName="A1",
                             standbyList=[SiteForm(siteCode=5901, storageName="A1-예비", orderNo=1)])],
        endSites=[SiteForm(siteCode=6001, storageName="B1")],
        devices=[DeviceReg(deviceImei=1001, deviceName="AGV-1")],
    )


async def main() -> None:
    sm = await setup()

    # 1) addTaskTemp: 템플릿+사이트+예비+장비 생성
    async with sm() as db:
        r = await task_service.add_task_temp(db, _add_form())
        check("addTaskTemp 성공", r.is_success())

    # 생성된 templateId 확보
    async with sm() as db:
        from app.repositories.task import task_template_repository
        templates = await task_template_repository.select_all(db)
        check("템플릿 1건", len(templates) == 1)
        tid = templates[0].task_template_id
        check("run_status 기본 '1'", templates[0].run_status == "1")

    # 2) selectTaskTempInfo: 구조 + standbyList
    async with sm() as db:
        r = await task_service.select_task_temp_info(db, TaskEditForm(taskTemplateId=tid))
        data = r.data
        check("selectInfo startSites 1", len(data["startSites"]) == 1)
        check("selectInfo standbyList 1", len(data["startSites"][0]["standbyList"]) == 1)
        check("selectInfo endSites 1", len(data["endSites"]) == 1)
        check("selectInfo devices 1", len(data["devices"]) == 1)

    # 3) editTaskTemp: 실행상태 '0' 전환 (충돌 없음)
    async with sm() as db:
        r = await task_service.edit_task_temp(db, TaskEditForm(taskTemplateId=tid, runStatus="0", userId="u1"))
        check("editTaskTemp 실행전환 성공", r.is_success())

    # 4) 같은 사이트로 다른 템플릿을 실행(0) 전환 시도 -> 충돌 실패
    async with sm() as db:
        # 두번째 템플릿(같은 startSite 5001) 생성
        f2 = _add_form()
        f2.taskName = "템플릿B"
        await task_service.add_task_temp(db, f2)
        templates = await __import__("app.repositories.task", fromlist=["task_template_repository"]).task_template_repository.select_all(db)
        tid2 = [t.task_template_id for t in templates if t.task_template_id != tid][0]
        r = await task_service.edit_task_temp(db, TaskEditForm(taskTemplateId=tid2, runStatus="0", userId="u1"))
        check("중복 사이트 실행전환 -> 충돌 실패", r.resultCode == "1" and "executed" in r.resultMsg)

    # 5) editTaskTempInfo: 삭제 후 재생성(이름 변경)
    async with sm() as db:
        r = await task_service.edit_task_temp_info(
            db, TaskEditInfoForm(taskTemplateId=tid, taskName="템플릿A-수정", userId="u1", userName="admin",
                                 startSites=[SiteForm(siteCode=5002, storageName="A2")],
                                 endSites=[SiteForm(siteCode=6002, storageName="B2")]),
        )
        check("editTaskTempInfo 성공", r.is_success())
    async with sm() as db:
        r = await task_service.select_task_temp_info(db, TaskEditForm(taskTemplateId=tid))
        check("editInfo 반영(이름)", r.data["task"]["template_name"] == "템플릿A-수정")
        check("editInfo 반영(사이트 교체)", r.data["startSites"][0]["site_code"] == 5002)

    # 6) delTaskTemp
    async with sm() as db:
        r = await task_service.del_task_temp(db, TaskEditForm(taskTemplateId=tid))
        check("delTaskTemp 성공", r.is_success())
    async with sm() as db:
        r = await task_service.select_task_temp_info(db, TaskEditForm(taskTemplateId=tid))
        check("delTaskTemp 후 조회 -> TaskNotExit", r.resultCode == "1")

    # 7) 없는 템플릿 editTaskTemp
    async with sm() as db:
        r = await task_service.edit_task_temp(db, TaskEditForm(taskTemplateId=999999, runStatus="1"))
        check("없는 템플릿 edit -> TaskNotExit", r.resultCode == "1")

    print(f"\n결과: {ok} passed, {fail} failed")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
