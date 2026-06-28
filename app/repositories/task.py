"""Task 관련 리포지토리 (작업 템플릿/임시 사이트·장비·예비위치)."""
from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import (
    TaskTempDevice,
    TaskTempSite,
    TaskTempSpareSite,
    TaskTemplate,
    UserTask,
)
from app.repositories.base import BaseRepository


class TaskTemplateRepository(BaseRepository[TaskTemplate]):
    def __init__(self) -> None:
        super().__init__(TaskTemplate)


class TaskTempSiteRepository(BaseRepository[TaskTempSite]):
    def __init__(self) -> None:
        super().__init__(TaskTempSite)

    async def select_by_template_type_ordered(
        self, db: AsyncSession, task_template_id: int, site_type: str
    ) -> Sequence[TaskTempSite]:
        """원본 selectByCondition(taskTemplateId, siteType) order by order_index asc."""
        stmt = (
            sa_select(TaskTempSite)
            .where(TaskTempSite.task_template_id == task_template_id)
            .where(TaskTempSite.site_type == site_type)
            .order_by(TaskTempSite.order_index.asc())
        )
        res = await db.execute(stmt)
        return res.scalars().all()

    async def select_run_task_temp_by_site(
        self, db: AsyncSession, site_code: int, site_type: str, task_template_id: int | None
    ) -> Sequence[TaskTemplate]:
        """원본 selectRunTaskTempBySite: 해당 사이트가 실행중(run_status=0) 템플릿에 있는지.

        SQL: yg_task_temp_site t join yg_task_template t1
             where t.site_code=? and t.site_type=? and t1.run_status='0'
             [and t1.task_template_id != ?]
        """
        stmt = (
            sa_select(TaskTemplate)
            .join(TaskTempSite, TaskTempSite.task_template_id == TaskTemplate.task_template_id)
            .where(TaskTempSite.site_code == site_code)
            .where(TaskTempSite.site_type == site_type)
            .where(TaskTemplate.run_status == "0")
        )
        if task_template_id is not None:
            stmt = stmt.where(TaskTemplate.task_template_id != task_template_id)
        res = await db.execute(stmt)
        return res.scalars().all()


    async def find_storage(
        self, db: AsyncSession, task_template_id: int, site_type: str, site_status: str
    ):
        """원본 selectRunSiteStorage(findStorage): 템플릿의 해당 타입/상태 보관위치 1건.

        SQL: yg_task_temp_site t1 join yg_storage t2 on t1.site_code=t2.site_code
             where t2.site_status=? and t1.site_type=? and t1.task_template_id=?
             order by t1.order_index asc
        """
        from app.models.tables import Storage

        stmt = (
            sa_select(Storage)
            .join(TaskTempSite, TaskTempSite.site_code == Storage.site_code)
            .where(Storage.site_status == site_status)
            .where(TaskTempSite.site_type == site_type)
            .where(TaskTempSite.task_template_id == task_template_id)
            .order_by(TaskTempSite.order_index.asc())
        )
        res = await db.execute(stmt)
        return res.scalars().first()


class TaskTempDeviceRepository(BaseRepository[TaskTempDevice]):
    def __init__(self) -> None:
        super().__init__(TaskTempDevice)


class TaskTempSpareSiteRepository(BaseRepository[TaskTempSpareSite]):
    def __init__(self) -> None:
        super().__init__(TaskTempSpareSite)


class UserTaskRepository(BaseRepository[UserTask]):
    def __init__(self) -> None:
        super().__init__(UserTask)

    async def select_run_task_by_type(
        self, db: AsyncSession, device_imei: int, send_flag: str, task_type: str
    ) -> Sequence[UserTask]:
        """원본 selectRunTaskByType: 템플릿에 이 장비가 등록된 작업.

        SQL: yg_user_task t1 join yg_task_temp_device t2 on task_template_id
             where t2.device_imei=? and t1.send_flag=? and t1.task_type=? order by user_task_id asc
        """
        stmt = (
            sa_select(UserTask)
            .join(TaskTempDevice, TaskTempDevice.task_template_id == UserTask.task_template_id)
            .where(TaskTempDevice.device_imei == device_imei)
            .where(UserTask.send_flag == send_flag)
            .where(UserTask.task_type == task_type)
            .order_by(UserTask.user_task_id.asc())
        )
        res = await db.execute(stmt)
        return res.scalars().all()

    async def select_by_flag_type(
        self, db: AsyncSession, send_flag: str, task_type: str, desc: bool = False
    ) -> Sequence[UserTask]:
        """send_flag + task_type 조건으로 user_task_id 정렬 조회."""
        order = UserTask.user_task_id.desc() if desc else UserTask.user_task_id.asc()
        stmt = (
            sa_select(UserTask)
            .where(UserTask.send_flag == send_flag)
            .where(UserTask.task_type == task_type)
            .order_by(order)
        )
        res = await db.execute(stmt)
        return res.scalars().all()

    async def select_by_flags_type(
        self, db: AsyncSession, send_flags: list[str], task_type: str
    ) -> Sequence[UserTask]:
        """send_flag IN (...) AND task_type=? (호출작업 중복 검사용)."""
        stmt = (
            sa_select(UserTask)
            .where(UserTask.send_flag.in_(send_flags))
            .where(UserTask.task_type == task_type)
        )
        res = await db.execute(stmt)
        return res.scalars().all()

    async def select_by_device_flag(
        self, db: AsyncSession, device_imei: int, send_flag: str
    ) -> Sequence[UserTask]:
        """deviceImei + send_flag, user_task_id asc."""
        stmt = (
            sa_select(UserTask)
            .where(UserTask.device_imei == device_imei)
            .where(UserTask.send_flag == send_flag)
            .order_by(UserTask.user_task_id.asc())
        )
        res = await db.execute(stmt)
        return res.scalars().all()

    async def find_site_task(self, db: AsyncSession, site_code: int) -> Sequence[UserTask]:
        """원본 findSiteTask: 진행중(send_flag in 1,2) 이고 시작/종료가 site_code 인 작업.

        createTask 는 start=end=code 로 호출하므로 (start_site_code=code or end_site_code=code).
        """
        from sqlalchemy import or_

        stmt = (
            sa_select(UserTask)
            .where(UserTask.send_flag.in_(["1", "2"]))
            .where(or_(UserTask.start_site_code == site_code, UserTask.end_site_code == site_code))
        )
        res = await db.execute(stmt)
        return res.scalars().all()

    async def select_all_ordered_desc(
        self, db: AsyncSession, send_flag: str | None = None
    ) -> Sequence[UserTask]:
        """원본 getUserTaskInfo용: 전체(또는 sendFlag 필터) 작업을 user_task_id desc 정렬."""
        stmt = sa_select(UserTask).order_by(UserTask.user_task_id.desc())
        if send_flag:
            stmt = stmt.where(UserTask.send_flag == send_flag)
        res = await db.execute(stmt)
        return res.scalars().all()

    async def select_by_start_site_code(
        self, db: AsyncSession, site_code: int
    ) -> Sequence[UserTask]:
        """startSiteCode 기준 user_task_id desc 정렬 조회 (getTaskByCode용)."""
        stmt = (
            sa_select(UserTask)
            .where(UserTask.start_site_code == site_code)
            .order_by(UserTask.user_task_id.desc())
        )
        res = await db.execute(stmt)
        return res.scalars().all()

    async def select_for_get_task_info(
        self,
        db: AsyncSession,
        message_ids: list[str] | None,
        device_imeis: list[int] | None,
    ) -> Sequence[UserTask]:
        """원본 getTaskInfo용: messageIds AND deviceImeis IN 필터, 둘 다 없으면 전체. user_task_id desc."""
        stmt = sa_select(UserTask).order_by(UserTask.user_task_id.desc())
        if message_ids:
            stmt = stmt.where(UserTask.message_id.in_(message_ids))
        if device_imeis:
            stmt = stmt.where(UserTask.device_imei.in_(device_imeis))
        res = await db.execute(stmt)
        return res.scalars().all()

    async def get_count_task_by_type(
        self, db: AsyncSession, task_type: str | None = None
    ) -> Sequence[UserTask]:
        """원본 getCountTask: send_flag IN ('3','4','7') 작업 집계 (task_type 선택 필터)."""
        stmt = sa_select(UserTask).where(UserTask.send_flag.in_(["3", "4", "7"]))
        if task_type:
            stmt = stmt.where(UserTask.task_type == task_type)
        res = await db.execute(stmt)
        return res.scalars().all()


task_template_repository = TaskTemplateRepository()
task_temp_site_repository = TaskTempSiteRepository()
task_temp_device_repository = TaskTempDeviceRepository()
task_temp_spare_site_repository = TaskTempSpareSiteRepository()
user_task_repository = UserTaskRepository()
