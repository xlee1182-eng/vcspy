"""Device 관련 리포지토리.

원본 DeviceEntity=yg_device, 그리고 삭제 연쇄로 쓰이는
StorageDeviceRelation=yg_storage_device_relation, TaskTempDevice=yg_task_temp_device.
"""
from __future__ import annotations

from app.models.tables import Device, StorageDeviceRelation, TaskTempDevice
from app.repositories.base import BaseRepository


class DeviceRepository(BaseRepository[Device]):
    def __init__(self) -> None:
        super().__init__(Device)


class StorageDeviceRelationRepository(BaseRepository[StorageDeviceRelation]):
    def __init__(self) -> None:
        super().__init__(StorageDeviceRelation)


class TaskTempDeviceRepository(BaseRepository[TaskTempDevice]):
    def __init__(self) -> None:
        super().__init__(TaskTempDevice)


device_repository = DeviceRepository()
storage_device_relation_repository = StorageDeviceRelationRepository()
task_temp_device_repository = TaskTempDeviceRepository()
