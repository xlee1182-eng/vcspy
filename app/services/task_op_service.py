"""TaskOpService — 작업 생성 상태머신.

원본 com.ygcloud.ygvcs.service.task.service.TaskOpService.createTask 이식.
createTask 는 DB 기반: 조건 검증 → UserTask(send_flag='1') 생성 → 시작/종료 보관위치
상태 갱신(2/3). 실제 차량 송신은 별도(스케줄러가 send_flag='1' 픽업)이므로 전부 테스트 가능.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import constants as C
from app.core import messages
from app.models.tables import UserTask
from app.repositories.site import storage_repository
from app.repositories.task import (
    task_temp_device_repository,
    task_temp_site_repository,
    user_task_repository,
)
from app.services.sequence_service import sequence_service
from app.tcp.json_msg import JsonMsg


class TaskCreateForm:
    """원본 form.task.TaskCreateForm."""

    def __init__(self, device_imei=None, code: int = 0, code_act: str | None = None, device_type: str | None = None):
        self.deviceImei = device_imei
        self.code = code
        self.codeAct = code_act
        self.deviceType = device_type


class TaskOpService:
    def __init__(self) -> None:
        self._device_busy: set = set()

    async def create_task(self, db: AsyncSession, form: TaskCreateForm) -> JsonMsg:
        """원본 createTask."""
        # 동일 외설 장비 중복 처리 방지
        if form.deviceImei in self._device_busy:
            return JsonMsg.fail()
        self._device_busy.add(form.deviceImei)
        try:
            # 1) 해당 사이트에 진행중 작업이 있으면 거부
            running = await user_task_repository.find_site_task(db, form.code)
            if running:
                return JsonMsg.fail(f"【{form.code}】{messages.get_msg('TaskService.createTask.taskIsExecuted')}")

            task_template_id = None
            start_storage = None
            end_storage = None
            device_imei = None
            task_type = None
            user_task_id = None

            if form.codeAct == C.CODE_ACT[1]:  # "1" 호출(창고 비우기)
                templates = await task_temp_site_repository.select_run_task_temp_by_site(
                    db, form.code, C.SITE_TYPE[2], None
                )
                if not templates:
                    return JsonMsg.fail(
                        f"code【{form.code}】，{messages.get_msg('TaskService.createTask.siteNotTaskTemplate')}"
                    )
                task_template_id = templates[0].task_template_id
                start_storage = await task_temp_site_repository.find_storage(
                    db, task_template_id, C.SITE_TYPE[1], C.SITE_STATUS[1]
                )
                if start_storage is None:
                    return JsonMsg.fail(messages.get_msg("TaskService.createTask.notStartSite"))
                end_storage = await storage_repository.select_one(db, {"site_code": form.code})
                if end_storage is None:
                    return JsonMsg.fail(messages.get_msg("site.editStorage.noStorage"))

            elif form.codeAct == "2":  # 입고(창고 채우기)
                templates = await task_temp_site_repository.select_run_task_temp_by_site(
                    db, form.code, C.SITE_TYPE[1], None
                )
                if not templates:
                    return JsonMsg.fail(
                        f"code【{form.code}】，{messages.get_msg('TaskService.createTask.siteNotTaskTemplate')}"
                    )
                task_template_id = templates[0].task_template_id
                end_storage = await task_temp_site_repository.find_storage(
                    db, task_template_id, C.SITE_TYPE[2], C.SITE_STATUS[0]
                )
                if end_storage is None:
                    return JsonMsg.fail(messages.get_msg("TaskService.createTask.notEndSite"))
                start_storage = await storage_repository.select_one(db, {"site_code": form.code})
                if start_storage is None:
                    return JsonMsg.fail(messages.get_msg("site.editStorage.noStorage"))
            else:
                return JsonMsg.fail()

            # 2) 템플릿에 등록된 장비로 작업유형 결정
            regs = await task_temp_device_repository.select(db, {"task_template_id": task_template_id})
            if regs:
                user_task_id = await sequence_service.add_and_get_user_task_id(db)
                if len(regs) == 1:
                    device_imei = regs[0].device_imei
                    task_type = C.TASK_TYPE[0]  # 지정 차량
                else:
                    task_type = C.TASK_TYPE[2]  # 다중 차량
            else:
                task_type = C.TASK_TYPE[1]  # 미지정 차량

            # 3) UserTask 생성 (send_flag='1')
            now = datetime.now()
            ut = UserTask(
                user_task_id=user_task_id,
                device_imei=device_imei,
                start_site_code=start_storage.site_code,
                start_site_name=start_storage.storage_name,
                fun_code="B2",
                is_loop="0",
                lift_height=100,
                start_handel=C.HANDLES[1],
                start_storage_height=start_storage.storage_hight,
                end_site_code=end_storage.site_code,
                end_site_name=end_storage.storage_name,
                end_handel=C.HANDLES[2],
                end_storage_height=end_storage.storage_hight,
                task_type=task_type,
                task_is_cancel=C.TASK_IS_CANCEL[0],
                pick_place_state="0",
                send_flag="1",
                device_type=form.deviceType,
                created_imei=str(form.deviceImei),
                created_by="sys",
                created_time=now,
                updated_by="sys",
                updated_date=now,
                task_template_id=task_template_id,
            )
            await user_task_repository.insert(db, ut)

            # 4) 보관위치 상태 갱신: 시작=2(취화중), 종료=3(방화중)
            start_storage.site_status = "2"
            start_storage.updated_date = now
            await storage_repository.update_by_pk(db, start_storage)
            end_storage.site_status = "3"
            end_storage.updated_date = now
            await storage_repository.update_by_pk(db, end_storage)

            await db.commit()
            return JsonMsg.ok()
        finally:
            self._device_busy.discard(form.deviceImei)


    async def edit_and_get_an_task(self, db: AsyncSession, device_imei: int):
        """원본 editAndGetAnTask: 장비가 수행할 다음 작업 1건 선택.

        우선순위: ① 이 장비 지정 미실행작업 → ② 다중차(3)·장비 등록 작업 →
                  ③ 호출장비(4, desc) → ④ 미지정(2, asc). 없으면 None.
        """
        if device_imei in self._device_busy:
            return None
        self._device_busy.add(device_imei)
        try:
            # ① deviceImei + send_flag='1'
            rows = await user_task_repository.select_by_device_flag(db, device_imei, C.SEND_FLAG_ARR[1])
            if rows:
                return rows[0]
            # ② 다중차(taskType=3) 중 이 장비가 템플릿에 등록된 작업
            rows = await user_task_repository.select_run_task_by_type(
                db, device_imei, C.SEND_FLAG_ARR[1], C.TASK_TYPE[2]
            )
            if rows:
                return rows[0]
            # ③ 호출장비 작업(taskType=4) desc
            rows = await user_task_repository.select_by_flag_type(db, "1", "4", desc=True)
            if rows:
                return rows[0]
            # ④ 미지정(taskType=2) asc
            rows = await user_task_repository.select_by_flag_type(db, C.SEND_FLAG_ARR[1], C.TASK_TYPE[1])
            if rows:
                return rows[0]
            return None
        finally:
            self._device_busy.discard(device_imei)


task_op_service = TaskOpService()
