"""ProcessWarpWebService 서비스.

원본 ProcessServiceImpl.importSqlInfo 이식.
학습 데이터(SiteManage + ForkliftLine)를 DB/Redis에 일괄 교체한다.
"""
from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core import redis_constants as rc
from app.core.jsonresult import JsonResult
from app.models.tables import ForkliftLine, SiteManage, Storage
from app.repositories.forklift_line import forklift_line_repository
from app.repositories.site import site_manage_repository, storage_repository
from app.schemas.process import ExportSqlInfoDto, ForkliftLineDto, ImportSqlForm, SiteManageDto
from app.services.storage import storage_service
from app.utils import json_util
from app.utils.redis_util import redis_util


def _to_site_manage(dto: SiteManageDto) -> SiteManage:
    return SiteManage(
        manage_id=dto.manageId,
        site_manage_id=dto.siteManageId,
        site_manage_name=dto.siteManageName,
        site_id=dto.siteId,
        device_imei=dto.deviceImei,
        site_code=dto.siteCode,
        site_name=dto.siteName,
        site_type=dto.siteType,
        site_attr=dto.siteAttr,
        created_by=dto.createdBy,
        created_date=dto.createdDate,
        updated_by=dto.updatedBy,
        updated_date=dto.updatedDate,
        site_x=dto.siteX,
        site_y=dto.siteY,
        site_flag=dto.siteFlag,
        customer_id=dto.customerId,
        area_id=dto.areaId,
    )


def _to_forklift_line(dto: ForkliftLineDto) -> ForkliftLine:
    return ForkliftLine(
        forklift_line_id=dto.forkliftLineId,
        line_name=dto.lineName,
        start_site_id=dto.startSiteId,
        start_site_name=dto.startSiteName,
        start_site_code=dto.startSiteCode,
        end_site_id=dto.endSiteId,
        end_site_name=dto.endSiteName,
        end_site_code=dto.endSiteCode,
        device_imei=dto.deviceImei,
        step_number=dto.stepNumber,
        is_backing_up=dto.isBackingUp,
        created_by=dto.createdBy,
        created_date=dto.createdDate,
        updated_by=dto.updatedBy,
        updated_date=dto.updatedDate,
        parent_line_id=dto.parentLineId,
        start_site_x=dto.startSiteX,
        start_site_y=dto.startSiteY,
        end_site_x=dto.endSiteX,
        end_site_y=dto.endSiteY,
        line_attr=dto.lineAttr,
        return_line_id=dto.returnLineId,
        return_parent_id=dto.returnParentId,
        area_id=dto.areaId,
        is_radar=dto.isRadar,
        line_item=dto.lineItem,
        is_corrects_line=dto.isCorrectsLine,
        customer_id=dto.customerId,
        floor=dto.floor,
    )


class ProcessService:
    async def import_sql_info(self, db: AsyncSession, form: ImportSqlForm) -> JsonResult:
        """원본 importSqlInfo: 학습 데이터를 DB/Redis에 일괄 교체.

        1. data 파싱 → siteManageList 필수
        2. siteAttr 9/11 인 항목 → Storage 생성
        3. Redis site_{id}, site_all 갱신
        4. SiteManage/Storage/ForkliftLine 전체 교체
        5. Redis forklift_all 갱신
        """
        if not form.data or not form.data.strip():
            return JsonResult.fail("1", messages.get_msg("process.importSqlInfo.SiteListNotNull"))

        try:
            dto = ExportSqlInfoDto.model_validate(json.loads(form.data))
        except Exception:
            return JsonResult.fail("1", messages.get_msg("process.importSqlInfo.DataIsFail"))

        if dto is None or not dto.siteManageList:
            return JsonResult.fail("1", messages.get_msg("process.importSqlInfo.DataIsFail"))

        # SiteManage ORM 엔티티 변환 및 Storage 구성
        site_manage_entities: list[SiteManage] = []
        storage_entities: list[Storage] = []
        for sm_dto in dto.siteManageList:
            sm = _to_site_manage(sm_dto)
            site_manage_entities.append(sm)
            await redis_util.set_to_str(f"{rc.SITE_PREXFIX}{sm_dto.siteManageId}", sm_dto.model_dump())
            if sm_dto.siteAttr in ("9", "11"):
                storage_entities.append(storage_service.append_storage(sm))

        # Redis site_all 갱신
        await redis_util.set_to_str(rc.SITE_ALL, [d.model_dump() for d in dto.siteManageList])

        # SiteManage 전체 교체
        await site_manage_repository.delete(db, {})
        if site_manage_entities:
            db.add_all(site_manage_entities)
            await db.flush()

        # Storage 전체 교체
        await storage_repository.delete(db, {})
        if storage_entities:
            db.add_all(storage_entities)
            await db.flush()

        # ForkliftLine 전체 교체
        await forklift_line_repository.delete(db, {})
        fork_line_entities: list[ForkliftLine] = []
        fork_line_dicts: list[dict] = []
        for fl_dto in dto.forkliftLineList or []:
            fork_line_entities.append(_to_forklift_line(fl_dto))
            fork_line_dicts.append(fl_dto.model_dump())
        if fork_line_entities:
            db.add_all(fork_line_entities)
            await db.flush()

        # Redis forklift_all 갱신
        await redis_util.set_to_str(rc.FORKLIFT_ALL, fork_line_dicts)

        await db.commit()
        return JsonResult.success()


    async def clear_all_data(self, db: AsyncSession) -> JsonResult:
        """원본 clearAllData: 전체 테이블 데이터 삭제."""
        from sqlalchemy import text

        tables = [
            "yg_call_box_info",
            "yg_device",
            "yg_forklift_line",
            "yg_site",
            "yg_site_area",
            "yg_site_col",
            "yg_site_col_info",
            "yg_site_init_point",
            "yg_site_manage",
            "yg_storage",
            "yg_storage_device_relation",
            "yg_task_temp_device",
            "yg_task_temp_site",
            "yg_task_temp_spare_site",
            "yg_task_template",
            "yg_user_task",
            "yg_user_task_pro",
        ]
        for tbl in tables:
            try:
                await db.execute(text(f"DELETE FROM {tbl}"))
            except Exception:
                pass
        await db.commit()
        return JsonResult.success()


process_service = ProcessService()
