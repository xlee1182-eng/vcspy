"""i18n 메시지 파서.

원본 com.ygcloud.ygi18n.i18n.MessagesParse 의 대체.
원본 basename: i18n/messages (application.yml spring.messages.basename).
Java .properties 형식(ISO-8859-1 + \\uXXXX 이스케이프)을 그대로 읽는다.
"""
from __future__ import annotations

import re
from pathlib import Path

_I18N_DIR = Path(__file__).resolve().parent.parent / "i18n"
_UNICODE_RE = re.compile(r"\\u([0-9a-fA-F]{4})")


def _decode(value: str) -> str:
    return _UNICODE_RE.sub(lambda m: chr(int(m.group(1), 16)), value)


def _load(filename: str) -> dict[str, str]:
    path = _I18N_DIR / filename
    result: dict[str, str] = {}
    if not path.exists():
        return result
    # Java properties 는 latin-1 기반(비ASCII는 \\uXXXX). latin-1로 읽어 안전.
    for raw in path.read_text(encoding="latin-1").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "!")):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        result[key.strip()] = _decode(val.strip())
    return result


# locale -> 메시지 dict
_BUNDLES: dict[str, dict[str, str]] = {
    "en_US": _load("messages_en_US.properties"),
    "zh_CN": _load("messages_zh_CN.properties"),
    "": _load("messages.properties"),
}

DEFAULT_LOCALE = "en_US"


def get_msg(key: str, locale: str = DEFAULT_LOCALE) -> str:
    """메시지 키 조회. 없으면 키 자체를 반환(원본 동작과 동일하게 관대)."""
    bundle = _BUNDLES.get(locale) or _BUNDLES[DEFAULT_LOCALE]
    if key in bundle:
        return bundle[key]
    # 폴백: 기본 로케일 → 빈 번들
    return _BUNDLES[DEFAULT_LOCALE].get(key) or _BUNDLES[""].get(key) or key
