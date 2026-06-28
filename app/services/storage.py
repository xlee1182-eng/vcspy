"""Storage / StorageDeviceRelation 서비스.

원본 StorageServiceImpl, StorageDeviceRelationServiceImpl 이식.
- 테스트 가능(DB/Redis) 메서드: getSiteInfo, editStorage, getStorageByCode,
  appendStorage, editStorageRowStatus, getSiteByDevice, editStorageDevice, delStorageDevice.
- 작업 생성 의존 메서드(editStorageStatus/editAreaStatus/editScanStorageStatus/
  editStorageStatusByDevice): TaskOpService(Task+TCP) 이식 후 완성 → 현재 NotImplemented.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core import redis_constants as rc
from app.core.jsonresult import JsonResult
from app.models.tables import Storage, StorageDeviceRelation
from app.repositories.device import device_repository
from app.repositories.site import (
    site_manage_repository,
    storage_device_relation_repo,
    storage_repository,
)
from app.repositories.task import task_temp_site_repository
from app.schemas.site import (
    SiteEditForm,
    SiteInfoForm,
    StorageDeviceAddForm,
    StorageDeviceDelForm,
    StorageDeviceInfoForm,
)
from app.utils import json_util
from app.utils.id_utils import next_id
from app.utils.redis_util import redis_util


def _to_int(v) -> int | None:
    if v is None:
        return None
    if isinstance(v, int):
        return v
    s = str(v)
    return int(s) if s.lstrip("-").isdigit() else None


class StorageService:
    async def get_site_info(self, db: AsyncSession, form: SiteInfoForm) -> JsonResult:
        """원본 getSiteInfo: 보관위치 목록에 바인딩 장비정보(transient) 합성.

        camelCase 키 반환(원본 StorageEntity JSON 포맷 일치).
        """
        storages = await storage_repository.select_ordered(db)
        relations = await storage_device_relation_repo.select_all(db)
        site_map = {r.site_code: r for r in relations} if relations else {}

        result = []
        for s in storages:
            rel = site_map.get(s.site_code)
            result.append({
                "storageId": s.storage_id,
                "storageName": s.storage_name,
                "storageHight": s.storage_hight,
                "siteName": s.site_name,
                "siteCode": s.site_code,
                "siteStatus": s.site_status,
                "siteType": s.site_type,
                "customerId": s.customer_id,
                "areaId": s.area_id,
                "areaName": s.area_name,
                "createdBy": s.created_by,
                "createdDate": s.created_date,
                "updatedBy": s.updated_by,
                "updatedDate": s.updated_date,
                "isEnable": s.is_enable,
                "deviceImei": rel.device_imei if rel else None,
                "deviceName": rel.device_name if rel else None,
                "type": rel.type if rel else None,
            })
        return JsonResult.success(result)

    async def edit_storage(self, db: AsyncSession, form: SiteEditForm) -> JsonResult:
        """원본 editStorage."""
        storage = await storage_repository.select_by_pk(db, _to_int(form.storageId))
        if storage is None:
            return JsonResult.fail("1", messages.get_msg("site.editStorage.noStorage"))
        if form.siteName and form.siteName.strip():
            storage.site_name = form.siteName
        if form.isEnable and form.isEnable.strip():
            storage.is_enable = form.isEnable
        storage.updated_by = form.userName
        storage.updated_date = datetime.now()
        await storage_repository.update_by_pk(db, storage)
        await db.commit()
        await redis_util.set_to_str(f"{rc.STORAGE_}{storage.site_code}", json_util.to_dict(storage))
        return JsonResult.success()

    async def get_storage_by_code(self, db: AsyncSession, site_code: int) -> Storage | None:
        """원본 getStorageByCode."""
        rows = await storage_repository.select(db, {"site_code": site_code})
        return rows[0] if rows else None

    def append_storage(self, site_manage) -> Storage:
        """원본 appendStorage: SiteManage 로 신규 Storage 구성(미저장)."""
        return Storage(
            storage_id=int(next_id()),
            storage_name=site_manage.site_manage_name,
            storage_hight=0,
            site_name=site_manage.site_manage_name,
            site_code=site_manage.site_manage_id,
            site_status="0",
            site_type="1" if site_manage.site_attr == "9" else "2",
            customer_id=site_manage.customer_id,
            created_by=site_manage.created_by,
            created_date=site_manage.created_date,
            is_enable="0",
        )

    async def edit_storage_row_status(self, db: AsyncSession, site_code: int, site_status: str) -> JsonResult:
        """원본 editStorageRowStatus: site_code 의 모든 보관위치 상태 갱신."""
        await storage_repository.update_by_example(
            db,
            {"site_status": site_status, "updated_date": datetime.now()},
            {"site_code": site_code},
        )
        await db.commit()
        return JsonResult.success()

    async def get_site_by_device(self, db: AsyncSession, form: StorageDeviceInfoForm) -> JsonResult:
        """원본 SiteWarpWebService.getSiteByDevice."""
        device = await device_repository.select_by_pk(db, form.deviceImei)
        if device is None:
            return JsonResult.fail("1", messages.get_msg("device.getDevice.noDevice"))
        relations = await storage_device_relation_repo.select_by_device_ordered(db, form.deviceImei)
        msg = JsonResult.success()
        msg.data = [json_util.to_dict(r) for r in relations]
        return msg

    async def edit_storage_status(
        self, db: AsyncSession, device_imei: str | None, device_type: str | None,
        site_code: int, site_status: str, action_type: str | None,
    ) -> JsonResult:
        """원본 editStorageStatus: 보관위치 상태 변경 또는 작업 생성.

        - 보관위치 미존재/비활성 → noStorage
        - deviceImei 유효 & action='1' 또는 actionType='1' → 단순 상태갱신
        - 그 외 → TaskOpService.createTask (codeAct: status0→1 호출, else 2 입고)
        """
        from app.services.task_op_service import TaskCreateForm, task_op_service

        rows = await storage_repository.select(db, {"site_code": site_code})
        if not rows or rows[0].is_enable == "1":
            return JsonResult.fail("1", messages.get_msg("site.editStorageStatus.noStorage"))

        async def _update_status() -> None:
            await storage_repository.update_by_example(
                db, {"site_status": site_status, "updated_date": datetime.now()}, {"site_code": site_code}
            )
            await db.commit()

        code_act = "1" if site_status == "0" else "2"

        if device_imei and device_imei != "0":
            device = await device_repository.select_by_pk(db, device_imei)
            if device is None or device.is_enable == "1":
                return JsonResult.fail("1", messages.get_msg("device.getDevice.noDevice"))
            if device.action == "1" or action_type == "1":
                await _update_status()
                return JsonResult.success()
            task = await task_op_service.create_task(
                db, TaskCreateForm(device_imei=device_imei, code=site_code, code_act=code_act, device_type=device_type)
            )
            if task.status:
                return JsonResult.success()
            if device.type == "2":  # 카메라는 작업 실패해도 상태만 갱신
                await _update_status()
                return JsonResult.success()
            return JsonResult.success({"code": 100, "msg": task.msg})

        if action_type == "1":
            await _update_status()
            return JsonResult.success()

        task = await task_op_service.create_task(
            db, TaskCreateForm(device_imei=device_imei, code=site_code, code_act=code_act, device_type=device_type)
        )
        if task.status:
            return JsonResult.success()
        return JsonResult.success({"code": 100, "msg": task.msg})

    async def edit_area_status(self, db: AsyncSession, form) -> JsonResult:
        """원본 editAreaStatus: 일괄 창고 입출고 처리(一键清满库) — 템플릿의 해당 구역 사이트들에 일괄 작업 생성.

        form: taskTemplateId, siteStatus, type(siteType).
        실행중 템플릿(run_status≠'1')만 허용. 각 사이트가 활성·비작업중이면 createTask.
        """
        from app.repositories.task import task_template_repository
        from app.services.task_op_service import TaskCreateForm, task_op_service

        template = await task_template_repository.select_by_pk(db, form.taskTemplateId)
        if template is None or template.run_status == "1":
            return JsonResult.fail("1", messages.get_msg("TaskService.editTaskTemp.noTaskTemp"))

        sites = await task_temp_site_repository.select_by_template_type_ordered(
            db, form.taskTemplateId, form.type
        )
        if not sites:
            return JsonResult.success()

        code_act = "1" if form.siteStatus == "0" else "2"
        for ts in sites:
            rows = await storage_repository.select(db, {"site_code": ts.site_code})
            if not rows:
                continue
            storage = rows[0]
            if storage.is_enable == "1" or storage.site_status in ("2", "3"):
                continue
            await task_op_service.create_task(
                db, TaskCreateForm(device_imei="0", device_type="0", code=ts.site_code, code_act=code_act)
            )
        return JsonResult.success()

    async def edit_scan_storage_status(self, db: AsyncSession, form) -> JsonResult:
        """원본 editScanStorageStatus: 스캐너로 보관위치 상태 토글.

        form: deviceImei, siteCode, deviceType, (siteStatus/actionType 내부 설정)
        """
        device = await device_repository.select_by_pk(db, form.deviceImei)
        if device is None or device.is_enable == "1":
            return JsonResult.fail("1", messages.get_msg("device.getDevice.noDevice"))
        action_type = device.action

        bound = await storage_device_relation_repo.select(
            db, {"device_imei": form.deviceImei, "site_code": form.siteCode}
        )
        if not bound:
            return JsonResult.fail("1", messages.get_msg("storageDevice.editScanStorageStatus.deviceIsBound"))

        rows = await storage_repository.select(db, {"site_code": form.siteCode})
        if not rows or rows[0].is_enable == "1":
            return JsonResult.fail("1", messages.get_msg("site.editStorageStatus.noStorage"))
        storage = rows[0]
        if storage.site_status in ("2", "3"):
            return JsonResult.fail("1", messages.get_msg("site.editStorageStatus.storageWork"))
        # 0 → 1, 그 외 → 0 토글
        site_status = "1" if storage.site_status == "0" else "0"
        return await self.edit_storage_status(
            db, form.deviceImei, form.deviceType, form.siteCode, site_status, action_type
        )


    async def get_storage_info(self, db: AsyncSession, site_codes: list[int] | None) -> JsonResult:
        """원본 getStorageInfo: siteCode 목록 기준 보관위치 물자·공만 정보 반환."""
        if not site_codes:
            return JsonResult.success([])
        storages = await storage_repository.select_ordered(db)
        site_map = {s.site_code: s for s in storages}
        result = []
        for code in site_codes:
            s = site_map.get(code)
            if s is None:
                continue
            result.append({
                "siteCode": s.site_code,
                "skuCode": s.sku_code,
                "siteStatus": s.site_status,
            })
        return JsonResult.success(result)

    async def set_storage_skus(self, db: AsyncSession, form) -> JsonResult:
        """원본 setStorageSkus: 보관위치(열) SKU 바인딩."""
        if not form.storageSkus:
            return JsonResult.fail("1", messages.get_msg("api.paramNotEmpty"))
        site_manages = await site_manage_repository.select(db, None)
        site_manage_ids = {sm.site_manage_id for sm in site_manages}
        for item in form.storageSkus:
            if item.siteCode is None:
                return JsonResult.fail("1", f"{messages.get_msg('api.paramNotEmpty')}:siteCode")
            if not item.skuCode or not item.skuCode.strip():
                return JsonResult.fail("1", f"{messages.get_msg('api.paramNotEmpty')}:skuCode")
            if item.siteCode not in site_manage_ids:
                return JsonResult.fail("1", f"{messages.get_msg('site.editStorage.noStorage')}{item.siteCode}")
        for item in form.storageSkus:
            await storage_repository.update_by_example(
                db, {"sku_code": item.skuCode}, {"site_code": item.siteCode}
            )
            await task_temp_site_repository.update_by_example(
                db, {"sku_code": item.skuCode}, {"site_code": item.siteCode}
            )
        await db.commit()
        return JsonResult.success()

    async def edit_storage_status_web(self, db: AsyncSession, site_code: int, site_status: str) -> JsonResult:
        """원본 SiteManageWebService.editStorageStatus: TaskTempSite 조회로 actionType 자동 결정."""
        rows = await task_temp_site_repository.select(db, {"site_code": site_code, "site_type": "2"})
        action_type = "1" if rows else "2"
        return await self.edit_storage_status(db, "0", "0", site_code, site_status, action_type)

    async def get_all_site(self, db: AsyncSession, customer_id: str | None) -> JsonResult:
        """원본 SiteManageWebService.getAllSite: 전체 사이트 조회(외부)."""
        rows = await site_manage_repository.select(db, {"customer_id": customer_id} if customer_id else None)
        return JsonResult.success([json_util.to_dict(r) for r in rows])

    async def get_site_manage_info(self, db: AsyncSession, site_code: int) -> JsonResult:
        """원본 SiteManageWebService.getSiteInfo: 현재 사이트 정보 조회(외부)."""
        rows = await site_manage_repository.select(db, {"site_code": site_code})
        if not rows:
            return JsonResult.fail("1", messages.get_msg("site.editStorageStatus.noStorage"))
        return JsonResult.success(json_util.to_dict(rows[0]))


class StorageDeviceRelationService:
    async def edit_storage_device(self, db: AsyncSession, form: StorageDeviceAddForm) -> JsonResult:
        """원본 editStorageDevice: 다른 장비에 바인딩된 위치가 있으면 실패, 아니면 재바인딩."""
        for info in form.storageInfos or []:
            # 같은 site_code 가 다른 deviceImei 에 이미 바인딩됐는지
            rows = await storage_device_relation_repo.select(db, {"site_code": info.siteCode})
            conflict = [r for r in rows if r.device_imei != form.deviceImei]
            if conflict:
                return JsonResult.fail(
                    "1",
                    f"【{info.siteCode}】{messages.get_msg('storageDevice.editStorageDevice.storageIsBound')}"
                    f"【{conflict[0].device_name}】",
                )

        # 기존 장비 바인딩 전체 삭제 후 재생성
        await storage_device_relation_repo.delete(db, {"device_imei": form.deviceImei})
        for info in form.storageInfos or []:
            exists = await storage_device_relation_repo.select(db, {"site_code": info.siteCode})
            if exists:
                continue
            rel = StorageDeviceRelation(
                storage_device_relation_id=int(next_id()),
                device_imei=form.deviceImei,
                device_name=form.deviceName,
                type=form.type,
                site_code=info.siteCode,
                site_name=info.siteName,
                site_type=info.siteType,
                order_no=info.orderNo,
                created_by=form.userName,
                created_date=datetime.now(),
            )
            await storage_device_relation_repo.insert(db, rel)
        await db.commit()
        return JsonResult.success()

    async def del_storage_device(self, db: AsyncSession, form: StorageDeviceDelForm) -> JsonResult:
        """원본 delStorageDevice: site_code 바인딩 삭제."""
        await storage_device_relation_repo.delete(db, {"site_code": form.siteCode})
        await db.commit()
        return JsonResult.success()


storage_service = StorageService()
storage_device_relation_service = StorageDeviceRelationService()
