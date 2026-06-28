"""차량 메시지 프로세서 (원본 PrimaryMsgProcessor).

primary 서버의 message_handler 로 주입한다. 하트비트(fun=00)면 메모리테이블을
파싱·저장한다(비동기 작업으로 스케줄). 응답(fun!=00)은 채널매니저가 상관 처리한다.
"""
from __future__ import annotations

import asyncio
import logging

from app.tcp import byte_process as bp

LOGGER = logging.getLogger('app')


def message_handler(writer, frame: bytes) -> None:
    """원본 PrimaryMsgProcessor.messageHandler 진입점(동기). fun=00 이면 비동기 저장."""
    try:
        if len(frame) == 4:
            # 원본 channelActive 에서 0F0F0F0F 로 호출하는 초기 접속 처리.
            # 채널을 logined 상태로 마킹하고 로그만 남긴다(클라이언트로 전송 없음).
            peer = writer.get_extra_info("peername") if writer else None
            peer_str = f"{peer[0]}:{peer[1]}" if peer else "unknown"
            LOGGER.info("this client has logined system [%s]", peer_str)
            return
        if len(frame) <= 12:
            return
        fun = bp.print_hex_string(bp.split_byte(frame, 12, 13))
        if fun == "00":
            asyncio.create_task(_process_heartbeat(frame))
    except Exception:
        LOGGER.exception("heartbeat 처리 오류")


async def _process_heartbeat(frame: bytes) -> None:
    from datetime import datetime

    from app.core.database import get_sessionmaker
    from app.repositories.device import device_repository
    from app.services.device_memory_table import save_or_update_device
    from app.services.send_task import send_task_service
    from app.services.user_task_proxy import user_task_proxy_service

    table = await save_or_update_device(frame)
    imei = table.get("deviceImei")

    # 장치 자동 등록: DB에 없으면 최초 하트비트에서 자동 생성
    # isEnable="0" = 활성(원본 Java와 동일), "1" = 비활성화
    if imei:
        async with get_sessionmaker()() as db:
            existing = await device_repository.select_by_pk(db, str(imei))
            if existing is None:
                from app.models.tables import Device
                entity = Device(
                    device_imei=str(imei),
                    device_name=str(imei),
                    type="1",
                    is_enable="0",
                    created_by="system",
                    created_date=datetime.now(),
                )
                await device_repository.insert(db, entity)
                await db.commit()
                LOGGER.info("장치 자동 등록: imei=%s", imei)

    async with get_sessionmaker()() as db:
        await user_task_proxy_service.update_task(db, frame)
        await user_task_proxy_service.update_storage_state(db, frame)
        await db.commit()

    # wifi 재시작 체크 (fire-and-forget, 원본 ThreadPool.restartWifi)
    if imei:
        from app.services.device_memory_table import restart_device_wifi
        wifi_strength = table.get("wifiStrength") or 0
        asyncio.create_task(restart_device_wifi(imei, wifi_strength))

    # 유휴 상태면 다음 작업을 픽업해 자동 송신 (자동화 루프 마감)
    if send_task_service.should_dispatch(table):
        async with get_sessionmaker()() as db:
            await send_task_service.dispatch_task(db, table)
