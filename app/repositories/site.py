"""Site/Storage 리포지토리."""
from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tables import Site, SiteManage, Storage, StorageDeviceRelation
from app.repositories.base import BaseRepository


class StorageRepository(BaseRepository[Storage]):
    def __init__(self) -> None:
        super().__init__(Storage)

    async def select_ordered(self, db: AsyncSession) -> Sequence[Storage]:
        """원본 getSiteInfo: site_type asc, created_date asc 정렬 전체."""
        stmt = sa_select(Storage).order_by(Storage.site_type.asc(), Storage.created_date.asc())
        res = await db.execute(stmt)
        return res.scalars().all()


class SiteRepository(BaseRepository[Site]):
    def __init__(self) -> None:
        super().__init__(Site)


class SiteManageRepository(BaseRepository[SiteManage]):
    def __init__(self) -> None:
        super().__init__(SiteManage)


class StorageDeviceRelationRepo(BaseRepository[StorageDeviceRelation]):
    def __init__(self) -> None:
        super().__init__(StorageDeviceRelation)

    async def select_by_device_ordered(
        self, db: AsyncSession, device_imei: str
    ) -> Sequence[StorageDeviceRelation]:
        """deviceImei 로 조회, order_no asc 정렬 (원본 selectByCondition)."""
        stmt = (
            sa_select(StorageDeviceRelation)
            .where(StorageDeviceRelation.device_imei == device_imei)
            .order_by(StorageDeviceRelation.order_no.asc())
        )
        res = await db.execute(stmt)
        return res.scalars().all()


storage_repository = StorageRepository()
site_repository = SiteRepository()
site_manage_repository = SiteManageRepository()
storage_device_relation_repo = StorageDeviceRelationRepo()
