"""Redis 접근 유틸.

원본 com.ygcloud.ygvcs.utils.redis.RedisUtil 의 대체.
원본은 RedisTemplate(String 직렬화)에 값으로 JSON 문자열을 저장한다.
여기서는 redis.asyncio + JSON 문자열로 동일한 저장 포맷을 유지한다(기존 데이터 호환).

연결은 지연 초기화한다. import 시점에 redis 패키지가 없어도 되게 한다.
"""
from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.core.redis_constants import SITE_STORAGE_PREX
from app.utils import json_util

DEFAULT_EXPIRES = 600

_client = None


def set_client(client) -> None:
    """클라이언트 주입(테스트에서 fakeredis 등 교체용)."""
    global _client
    _client = client


def _redis():
    global _client
    if _client is None:
        import redis.asyncio as aioredis  # 지연 import

        _client = aioredis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            socket_timeout=settings.redis_timeout,
            decode_responses=True,  # 원본 StringRedisSerializer 대응
            protocol=2,
        )
    return _client


class RedisUtil:
    async def set_to_str(self, key: str, value: Any) -> bool:
        """원본 setToStr(key, object|json): 객체면 JSON 직렬화하여 저장."""
        try:
            payload = value if isinstance(value, str) else json_util.to_json(value)
            await _redis().set(key, payload)
            return True
        except Exception:
            return False

    async def set_storage(self, customer_id: str, site_code: int, value: Any) -> bool:
        try:
            await _redis().set(f"{SITE_STORAGE_PREX}{customer_id}:{site_code}", json_util.to_json(value))
            return True
        except Exception:
            return False

    async def set_to_json(self, key: str, value: Any, expires: int = DEFAULT_EXPIRES) -> bool:
        try:
            if expires <= 0:
                expires = DEFAULT_EXPIRES
            await _redis().set(key, json_util.to_json(value), ex=expires)
            return True
        except Exception:
            return False

    async def expires_key(self, key: str, expires: int = DEFAULT_EXPIRES) -> bool:
        if expires <= 0:
            expires = DEFAULT_EXPIRES
        await _redis().expire(key, expires)
        return True

    async def get_str_to_object(self, key: str, cls: type | None = None) -> Any:
        """원본 getStrToObject(key, Class).

        cls 가 str 이면 원시 문자열 반환, Pydantic 이면 모델, 그 외엔 dict.
        """
        try:
            json_str = await _redis().get(key) # Redis에서 키 값을 문자열로 읽어옴

            # cls 가 str 이면 원시 문자열 반환 
            # getattr(cls, "__name__", "").lower() == "string" 부분은 
            # 원본 Java의 String.class를 넘기던 패턴을 방어적으로 처리한 흔적인데, Python에서는 사실상 쓸 일 없는 코드입니다
            if cls is str or (cls is not None and getattr(cls, "__name__", "").lower() == "string"):
                return json_str
            
            # cls가 Pydantic 모델이면 → JSON 문자열을 파싱해서 모델 인스턴스로 변환
            return json_util.to_object(json_str, cls if cls and hasattr(cls, "model_validate") else None)
        
        except Exception:
            return None # 키가 없으면 None

    async def wildcard_key(self, pattern: str) -> set[str]:
        """원본 wildcardKey: KEYS 패턴."""
        return set(await _redis().keys(pattern))

    async def exists_key(self, key: str) -> bool:
        return bool(await _redis().exists(key))

    async def hset(self, key: str, field: str, value: Any) -> None:
        payload = value if isinstance(value, str) else json_util.to_json(value)
        await _redis().hset(key, field, payload)

    async def hget(self, key: str, field: str, cls: type | None = None) -> Any:
        try:
            json_str = await _redis().hget(key, field)
            return json_util.to_object(json_str, cls if cls and hasattr(cls, "model_validate") else None)
        except Exception:
            return None

    async def hmget_all(self, key: str, cls: type | None = None) -> list:
        try:
            values = await _redis().hvals(key)
            return [json_util.to_object(v, cls if cls and hasattr(cls, "model_validate") else None) for v in values]
        except Exception:
            return []

    async def hdel(self, key: str, field: str) -> None:
        await _redis().hdel(key, field)

    async def get_list(self, key: str, cls: type | None = None) -> list | None:
        try:
            json_str = await _redis().get(key)
            if not json_str:
                return None
            return json_util.to_list(json_str, cls if cls and hasattr(cls, "model_validate") else None)
        except Exception:
            return None

    async def get_line_int(self, key: str) -> list[int] | None:
        try:
            return json_util.to_list_int(await _redis().get(key))
        except Exception:
            return None

    async def delete_by_key(self, key: str) -> bool:
        await _redis().delete(key)
        return True

    async def clear_by_keys(self, keys_prefix: str) -> bool:
        keys = await _redis().keys(keys_prefix)
        if keys:
            await _redis().delete(*keys)
        return True

    async def get_hash_to_key(self, key: str) -> dict:
        try:
            return await _redis().hgetall(key)
        except Exception:
            return {}


redis_util = RedisUtil()
