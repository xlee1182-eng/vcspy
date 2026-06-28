"""User 서비스.

원본 UserServiceImpl 의 로직을 그대로 이식.
주의(원본 동작 보존): 비밀번호는 평문 비교한다(원본에 해시 없음).
                     실제 운영 이관 시 해시 도입을 별도 검토해야 함.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.jsonresult import JsonResult
from app.repositories.user import user_repository
from app.schemas.user import UserEditForm, UserLoginForm


def _to_dict(user) -> dict:
    """엔티티를 JSON 직렬화 가능한 dict 로 (비밀번호 제외)."""
    return {
        "userId": user.user_id,
        "resourceId": user.resource_id,
        "userType": user.user_type,
        "roleType": user.role_type,
        "clientType": user.client_type,
        "userName": user.user_name,
        "sex": user.sex,
        "age": user.age,
        "phone": user.phone,
        "address": user.address,
        "postCode": user.post_code,
        "email": user.email,
        "deleteFlag": user.delete_flag,
        "isOnline": user.is_online,
    }


class UserService:
    async def user_login(self, db: AsyncSession, form: UserLoginForm) -> JsonResult:
        """원본 UserServiceImpl.userLogin 이식.

        user_name 으로 조회 → 없으면 USER_NAME_ERR, 비밀번호 불일치면 USER_PWD_ERR.
        """
        user = await user_repository.select_one(db, {"user_name": form.userName})
        if user is None:
            return JsonResult.fail("1", messages.get_msg("USER_NAME_ERR"))
        if form.password != user.password:
            return JsonResult.fail("1", messages.get_msg("USER_PWD_ERR"))
        return JsonResult.success(_to_dict(user))

    async def edit_password(self, db: AsyncSession, form: UserEditForm) -> JsonResult:
        """원본 UserServiceImpl.editPassword 이식.

        user_name + 기존 password 로 조회 → 없으면 NAME_PWD_ERR,
        있으면 새 비밀번호로 갱신.
        """
        user = await user_repository.select_one(
            db, {"user_name": form.userName, "password": form.password}
        )
        if user is None:
            return JsonResult.fail("1", messages.get_msg("NAME_PWD_ERR"))
        user.password = form.newPassword
        await user_repository.update_by_pk(db, user)
        await db.commit()
        return JsonResult.success()


user_service = UserService()
