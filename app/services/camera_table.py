"""카메라 점유상태 처리 (비전).

원본 com.ygcloud.ygvcs.service.device.impl.CameraTableServiceImpl 이식.
이 빌드에는 OpenCV 이미지 처리가 없다 — 카메라가 온디바이스로 점유를 판단해
TCP 프레임으로 '점유 비트'를 보고하고, 여기서 파싱·디바운스 후 보관위치 상태를 갱신한다.

흐름: saveCameraStorageStates(프레임) → analyzingStorageState(비트 분해)
      → isUpdateStorage(슬롯별 디바운스 5회 → editScanStorageStatus).
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import redis_constants as rc
from app.repositories.device import device_repository
from app.repositories.site import storage_device_relation_repo, storage_repository
from app.tcp import byte_process as bp
from app.utils.redis_util import redis_util

LOGGER = logging.getLogger('app')


class CameraTableService:
    async def save_camera_storage_states(self, db: AsyncSession, msg: bytes) -> None:
        """원본 saveCameraStorageStates: 카메라 프레임 → 슬롯별 점유 분석."""
        if len(bp.print_hex_string(msg) or "") < 68:
            return
        camera_imei = bp.bytes_to_int(bp.split_byte(msg, 8, 12), 4)
        storage_count = bp.bytes_to_int(bp.split_byte(msg, 23, 24), 1)
        storage_state = bp.split_byte(msg, 24, 28)
        LOGGER.warning("카메라 점유상태 수량【%s】, 상태【%s】", storage_count, bp.print_hex_string(storage_state))
        await self.analyzing_storage_state(db, camera_imei, storage_count, storage_state)

    async def analyzing_storage_state(
        self, db: AsyncSession, camera_imei: int, storage_count: int, storage_state: bytes
    ) -> None:
        """원본 analyzingStorageState: 점유 비트를 슬롯별로 분해(LSB=슬롯1)."""
        if storage_count < 1:
            return
        all_state = bp.bytes_to_binary(storage_state)
        # 원본: substring(len-count). 선행 0 손실 방지 위해 count 길이로 좌측 0패딩.
        all_state = all_state.zfill(storage_count)[-storage_count:]
        index = 1
        for i in range(len(all_state), 0, -1):
            await self.is_update_storage(db, camera_imei, index, all_state[i - 1:i])
            index += 1

    async def get_camera_storage_info(self, db: AsyncSession, camera_imei: int, number: int):
        """원본 getCameraStorageInfo: 카메라+슬롯(order_no)에 바인딩된 보관위치 관계."""
        rows = await storage_device_relation_repo.select(
            db, {"device_imei": str(camera_imei), "order_no": number}
        )
        return rows[0] if rows else None

    async def is_update_storage(self, db: AsyncSession, camera_imei: int, number: int, state: str) -> None:
        """원본 isUpdateStorage: 디바운스 후 보관위치 상태 갱신."""
        device = await device_repository.select_by_pk(db, str(camera_imei))
        if device is None or device.is_enable == "1":
            return

        old_key = f"{rc.OLD_CAMERA_STATE}{camera_imei}{number}"
        old_state = await redis_util.get_str_to_object(old_key, str)
        if old_state and state == old_state:
            return

        rel = await self.get_camera_storage_info(db, camera_imei, number)
        if rel is None:
            return
        rows = await storage_repository.select(db, {"site_code": rel.site_code})
        if not rows or rows[0].is_enable == "1":
            return
        storage = rows[0]

        cam_key = f"{rc.CAMERA_STATES}{camera_imei}{number}"
        cam = await redis_util.get_str_to_object(cam_key)
        if not isinstance(cam, dict):
            await redis_util.set_to_json(cam_key, {"state": state, "number": 1}, 60)
            return
        if cam.get("state") != state:
            cam = {"number": 1, "state": state}
            await redis_util.set_to_json(cam_key, cam, 20)

        # 디바운스: DB상태와 일치하며 안정되었거나 5회 이상 관측되어야 적용
        stable = (state == storage.site_status and state == cam.get("state")) or cam.get("number", 0) >= 5
        if not stable:
            cam["number"] = cam.get("number", 0) + 1
            cam["state"] = state
            await redis_util.set_to_json(cam_key, cam, 20)
            return

        # 작업이 최근(10초) 상태를 바꿨으면 보류
        is_state = await redis_util.get_str_to_object(f"{rc.STORAGE_STATE}{rel.site_code}", str)
        if is_state:
            return

        # 카메라 상태가 DB와 다르고, 작업중(2/3)이 아니면 → 상태 반영(작업 생성 가능)
        if not (state == storage.site_status or storage.site_status in ("2", "3")):
            from app.schemas.site import StorageStatusScanEditForm
            from app.services.storage import storage_service

            form = StorageStatusScanEditForm(
                deviceImei=str(camera_imei),
                siteCode=storage.site_code,
                siteStatus=state,
                deviceType="2",
                actionType=device.action,
            )
            await storage_service.edit_scan_storage_status(db, form)
            await redis_util.set_to_json(old_key, state, 240)
            await redis_util.delete_by_key(cam_key)


camera_table_service = CameraTableService()
