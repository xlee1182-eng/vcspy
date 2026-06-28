"""JSON 직렬화 헬퍼.

원본 com.ygcloud.ygvcs.utils.JsonUtil 의 대체.
SQLAlchemy 모델/Pydantic/dataclass/dict 등을 JSON 문자열로 변환하고 복원한다.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import DeclarativeBase


def _default(o: Any):
    if isinstance(o, (datetime, date)):
        return o.strftime("%Y-%m-%d %H:%M:%S") if isinstance(o, datetime) else o.isoformat()
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, DeclarativeBase):
        return to_dict(o)
    if hasattr(o, "model_dump"):  # pydantic v2
        return o.model_dump()
    raise TypeError(f"직렬화 불가 타입: {type(o)}")


def to_dict(entity: Any) -> dict:
    """SQLAlchemy 모델 -> 컬럼 dict (camelCase 매핑 없이 속성명 그대로)."""
    if isinstance(entity, DeclarativeBase):
        cols = sa_inspect(entity).mapper.column_attrs
        return {attr.key: getattr(entity, attr.key) for attr in cols}
    if hasattr(entity, "model_dump"):
        return entity.model_dump()
    if isinstance(entity, dict):
        return entity
    return dict(entity)


def to_json(obj: Any) -> str:
    if obj is None:
        return None  # type: ignore[return-value]
    if isinstance(obj, str):
        return obj
    return json.dumps(obj, default=_default, ensure_ascii=False)


def to_object(json_str: str | None, cls: type | None = None) -> Any:
    """JSON 문자열 -> dict/list. cls 가 Pydantic 이면 모델 인스턴스로 변환."""
    if not json_str:
        return None
    data = json.loads(json_str)
    if cls is not None and hasattr(cls, "model_validate"):
        return cls.model_validate(data)
    return data


def to_list(json_str: str | None, cls: type | None = None) -> list:
    if not json_str:
        return []
    data = json.loads(json_str)
    if cls is not None and hasattr(cls, "model_validate"):
        return [cls.model_validate(x) for x in data]
    return list(data)


def to_list_int(json_str: str | None) -> list[int]:
    if not json_str:
        return []
    return [int(x) for x in json.loads(json_str)]
