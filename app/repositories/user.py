"""User 리포지토리.

원본 UserEntity 는 sys_user 테이블에 매핑된다(UserMapper.xml 기준).
"""
from __future__ import annotations

from app.models.tables import SysUser
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[SysUser]):
    def __init__(self) -> None:
        super().__init__(SysUser)


user_repository = UserRepository()
