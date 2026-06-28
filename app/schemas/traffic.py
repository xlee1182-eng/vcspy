"""Traffic 요청 폼 (Pydantic).

원본 webservice.web.form.traffic.* 이식.
- web 엔드포인트 폼: WebForm 상속 (인증 필드 없음)
"""
from __future__ import annotations

from app.schemas.base_form import WebForm


class TrafficSitePassForm(WebForm):
    """연합 교통관제 통행 가능 사이트 설정 (web/isSitePass)."""

    siteList: list[int] | None = None


class TrafficPointSetForm(WebForm):
    """교통관제 포인트 설정 (web/setTrafficPoint)."""

    siteList: list[int] | None = None
