"""Task 템플릿 서비스.

원본 com.ygcloud.ygvcs.service.task.impl.TaskService 이식 (순수 DB CRUD).
addTaskTemp / editTaskTemp / editTaskTempInfo / delTaskTemp / selectTaskTempInfo.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.jsonresult import JsonResult
from app.models.tables import (
    TaskTempDevice,
    TaskTempSite,
    TaskTempSpareSite,
    TaskTemplate,
)
from app.repositories.task import (
    task_temp_device_repository,
    task_temp_site_repository,
    task_temp_spare_site_repository,
    task_template_repository,
)
from app.schemas.task import TaskAddForm, TaskEditForm, TaskEditInfoForm
from app.utils import json_util
from app.utils.id_utils import next_id_long

RUN_STATUS_0 = "0"  # 실행중
RUN_STATUS_1 = "1"  # 미실행


class TaskService:
    async def add_task_temp(self, db: AsyncSession, form: TaskAddForm) -> JsonResult:
        """원본 addTaskTemp: 템플릿 + 시작/종료 사이트(+예비) + 장비 생성."""
        run_status = RUN_STATUS_1
        if form.taskTemplateId is None:
            template_id = next_id_long()
        else:
            template_id = form.taskTemplateId
            existing = await task_template_repository.select_by_pk(db, template_id)
            if existing is not None and existing.run_status:
                run_status = existing.run_status
            # 기존 템플릿/사이트/장비/예비 삭제
            await task_template_repository.delete_by_pk(db, template_id)
            await task_temp_site_repository.delete(db, {"task_template_id": template_id})
            await task_temp_device_repository.delete(db, {"task_template_id": template_id})
            await task_temp_spare_site_repository.delete(db, {"task_template_id": template_id})

        now = datetime.now()
        template = TaskTemplate(
            task_template_id=template_id,
            template_name=form.taskName,
            created_by=form.userId,
            created_date=now,
            updated_by=form.userId,
            updated_date=now,
            run_status=run_status,
        )
        await task_template_repository.insert(db, template)

        await self._insert_sites(db, form, template_id, form.startSites, "1")
        await self._insert_sites(db, form, template_id, form.endSites, "2")

        for dev in form.devices or []:
            await task_temp_device_repository.insert(
                db,
                TaskTempDevice(
                    task_temp_device_id=next_id_long(),
                    task_template_id=template_id,
                    device_imei=dev.deviceImei,
                    created_by=form.userId,
                    created_date=now,
                    updated_by=form.userId,
                    updated_date=now,
                ),
            )
        await db.commit()
        return JsonResult.success()

    async def _insert_sites(self, db, form, template_id, sites, site_type) -> None:
        now = datetime.now()
        for i, site in enumerate(sites):
            await task_temp_site_repository.insert(
                db,
                TaskTempSite(
                    task_temp_site_id=next_id_long(),
                    task_template_id=template_id,
                    site_code=site.siteCode,
                    site_name=site.storageName,
                    order_index=i + 1,
                    site_type=site_type,
                    created_by=form.userId,
                    created_date=now,
                    updated_by=form.userId,
                    updated_date=now,
                ),
            )
            for sb in site.standbyList or []:
                await task_temp_spare_site_repository.insert(
                    db,
                    TaskTempSpareSite(
                        task_temp_spare_site_id=next_id_long(),
                        task_template_id=template_id,
                        site_type=site_type,
                        main_site_code=site.siteCode,
                        main_site_name=site.storageName,
                        site_code=sb.siteCode,
                        site_name=sb.storageName,
                        order_index=sb.orderNo,
                        created_by=form.userName,
                        created_date=now,
                    ),
                )

    async def edit_task_temp(self, db: AsyncSession, form: TaskEditForm) -> JsonResult:
        """원본 editTaskTemp: 실행상태 전환. 실행(0) 전환 시 사이트 충돌 검사."""
        template = await task_template_repository.select_one(db, {"task_template_id": form.taskTemplateId})
        if template is None:
            return JsonResult.fail("1", messages.get_msg("TaskService.editTaskTemp.TaskNotExit"))

        if form.runStatus == RUN_STATUS_0:
            for site_type in ("1", "2"):
                sites = await task_temp_site_repository.select(
                    db, {"task_template_id": form.taskTemplateId, "site_type": site_type}
                )
                for s in sites:
                    running = await task_temp_site_repository.select_run_task_temp_by_site(
                        db, s.site_code, s.site_type, form.taskTemplateId
                    )
                    if running:
                        return JsonResult.fail(
                            "1",
                            messages.get_msg("TaskService.editTaskTemp.SiteExitAnTask1")
                            + str(s.site_code)
                            + messages.get_msg("TaskService.editTaskTemp.SiteExitAnTask2")
                            + (running[0].template_name or "")
                            + messages.get_msg("TaskService.editTaskTemp.SiteExitAnTask3"),
                        )

        template.run_status = form.runStatus
        template.updated_by = form.userId
        template.updated_date = datetime.now()
        await task_template_repository.update_by_pk(db, template)
        await db.commit()
        return JsonResult.success()

    async def del_task_temp(self, db: AsyncSession, form: TaskEditForm) -> JsonResult:
        """원본 delTaskTemp: 사이트/장비/템플릿/예비 삭제."""
        await task_temp_site_repository.delete(db, {"task_template_id": form.taskTemplateId})
        await task_temp_device_repository.delete(db, {"task_template_id": form.taskTemplateId})
        await task_template_repository.delete_by_pk(db, form.taskTemplateId)
        await task_temp_spare_site_repository.delete(db, {"task_template_id": form.taskTemplateId})
        await db.commit()
        return JsonResult.success()

    async def edit_task_temp_info(self, db: AsyncSession, form: TaskEditInfoForm) -> JsonResult:
        """원본 editTaskTempInfo: 삭제 후 재생성."""
        await self.del_task_temp(db, TaskEditForm(taskTemplateId=form.taskTemplateId))
        add_form = TaskAddForm(
            taskTemplateId=form.taskTemplateId,
            taskName=form.taskName,
            devices=form.devices,
            startSites=form.startSites,
            endSites=form.endSites,
            userId=form.userId,
            userName=form.userName,
        )
        return await self.add_task_temp(db, add_form)

    async def select_task_temp_info(self, db: AsyncSession, form: TaskEditForm) -> JsonResult:
        """원본 selectTaskTempInfo: 템플릿 + 시작/종료 사이트(예비포함) + 장비."""
        template = await task_template_repository.select_by_pk(db, form.taskTemplateId)
        if template is None:
            return JsonResult.fail("1", messages.get_msg("TaskService.editTaskTemp.TaskNotExit"))

        spares = await task_temp_spare_site_repository.select(db, {"task_template_id": form.taskTemplateId})
        # site_type -> main_site_code -> [spare...]
        spare_map: dict[str, dict[int, list]] = {}
        for sp in spares:
            spare_map.setdefault(sp.site_type, {}).setdefault(sp.main_site_code, []).append(sp)

        async def build_sites(site_type: str) -> list[dict]:
            sites = await task_temp_site_repository.select_by_template_type_ordered(
                db, form.taskTemplateId, site_type
            )
            result = []
            type_map = spare_map.get(site_type, {})
            for s in sites:
                d = json_util.to_dict(s)
                standby = []
                for sp in type_map.get(s.site_code, []):
                    standby.append({
                        "siteCode": sp.site_code,
                        "siteName": sp.site_name,
                        "storageName": sp.site_name,
                        "orderNo": sp.order_index,
                    })
                d["standbyList"] = standby
                result.append(d)
            return result

        start_sites = await build_sites("1")
        end_sites = await build_sites("2")
        devices = await task_temp_device_repository.select(db, {"task_template_id": form.taskTemplateId})

        return JsonResult.success({
            "task": json_util.to_dict(template),
            "startSites": start_sites,
            "endSites": end_sites,
            "devices": [json_util.to_dict(x) for x in devices],
        })


task_service = TaskService()
