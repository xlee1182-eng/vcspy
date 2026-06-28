"""하트비트 → 장비 메모리테이블 파서.

원본 DeviceMemoryTableServiceImpl.saveOrUpdateDevice(byte[]) 이식.
AGV 하트비트(fun=00) 프레임을 바이트 오프셋으로 디코딩해 Redis 에 저장한다.
이 데이터를 addTask/initLocation/setTask 등이 DEVICE_TASK_TABLE 로 읽는다.

원본은 다수의 텔레메트리(레이더/엔코더/위치/오차)도 파싱하나, 다른 서비스가
실제 소비하는 핵심 필드 위주로 이식한다(오프셋은 원본과 동일).
"""
from __future__ import annotations

import logging

from app.core import redis_constants as rc
from app.tcp import byte_process as bp
from app.utils.redis_util import redis_util

LOGGER = logging.getLogger('app')


def parse_memory_table(reb: bytes) -> dict:
    """하트비트 프레임 → 메모리테이블 dict (원본 바이트 오프셋)."""
    imei = bp.bytes_to_int(bp.split_byte(reb, 8, 12), 4)
    user_task_id = bp.bytes_to_int(bp.split_byte(reb, 4, 8), 4)
    flag = bp.print_hex_string(bp.split_byte(reb, 14, 15))
    flag_byte = bp.bytes_to_int(bp.hex_string_to_bytes(flag), 1)
    model = flag_byte >> 6
    start_site_code = bp.bytes_to_int(bp.split_byte(reb, 15, 18), 3)
    end_site_code = bp.bytes_to_int(bp.split_byte(reb, 18, 21), 3)
    steps = bp.bytes_to_int(bp.split_byte(reb, 21, 24), 3)
    fork_height = bp.bytes_to_int(bp.split_byte(reb, 25, 27), 2)
    task_number = bp.bytes_to_int(bp.split_byte(reb, 27, 29), 2)
    battery_level = bp.bytes_to_int(bp.split_byte(reb, 29, 30), 1)
    fork_status = bp.bytes_to_int(bp.split_byte(reb, 30, 31), 1) & 3
    task_flag = (bp.bytes_to_int(bp.split_byte(reb, 31, 32), 1) >> 4) & 0xFF
    x_position = bp.bytes_to_int(bp.split_byte(reb, 104, 108), 4)
    y_position = bp.bytes_to_int(bp.split_byte(reb, 108, 112), 4)
    o_position = bp.bytes_to_int(bp.split_byte(reb, 112, 116), 4)
    self_consistent = bp.bytes_to_int(bp.split_byte(reb, 120, 121), 1)
    storage_row_flag = (self_consistent >> 1) & 2   # Java storageRowFlag (库位列状态)
    lock_state = (self_consistent >> 3) & 1
    traffic_area_id = bp.bytes_to_int(bp.split_byte(reb, 125, 127), 2)
    button_number = bp.bytes_to_int(bp.split_byte(reb, 127, 129), 2)
    return_line_id = bp.bytes_to_int(bp.split_byte(reb, 132, 136), 4)
    task_source = bp.bytes_to_int(bp.split_byte(reb, 137, 138), 1)  # Java taskSource (任务来源)
    wifi_strength = bp.bytes_to_int(bp.split_byte(reb, 148, 149), 1)
    floor = bp.bytes_to_int(bp.split_byte(reb, 151, 152), 1)
    device_no = bp.bytes_to_int(bp.split_byte(reb, 152, 153), 1)
    control_status = bp.bytes_to_int(bp.split_byte(reb, 153, 154), 1)
    control_device_no = bp.bytes_to_int(bp.split_byte(reb, 154, 155), 1)

    return {
        "deviceImei": imei,
        "userTaskId": user_task_id,
        "flag": flag,
        "model": model,
        "startSiteCode": start_site_code,
        "endSiteCode": end_site_code,
        "steps": steps,
        "forkHeight": fork_height,
        "taskNumber": task_number,
        "batteryLevel": battery_level,
        "forkStatus": fork_status,
        "taskFlag": task_flag,
        "taskSource": task_source,
        "storageRowFlag": storage_row_flag,
        "xPosition": x_position,
        "yPosition": y_position,
        "oPosition": o_position,
        "trafficAreaId": traffic_area_id,
        "returnLineId": return_line_id,
        "lockState": lock_state,
        "buttonNumber": button_number,
        "wifiStrength": wifi_strength,
        "floor": floor,
        "deviceNo": device_no,
        "controlStatus": control_status,
        "controlDeviceNo": control_device_no,
    }


def send_heartbeat(imei: int, user_task_id: int, length: int) -> None:
    """원본 sendHeartbeat: 하트비트 수신 응답 프레임 AGV 로 송신 (fire-and-forget).

    Frame: 40BF807F + userTaskId(4) + imei(4) + "00" + ("00"|"0000") + CRC
    length <= 137 이면 1바이트 페이로드, 초과면 2바이트.
    """
    from app.tcp.tcp_client import TaskModel, send_task_queen

    parts = ["40BF807F"]
    parts.append(bp.print_hex_string(bp.int_to_bytes(user_task_id, 4)))
    parts.append(bp.print_hex_string(bp.int_to_bytes(imei, 4)))
    parts.append("00")
    parts.append("00" if length <= 137 else "0000")
    task = TaskModel()
    task.requestMsg = bp.get_crc_to_send("".join(parts), "123456789")
    send_task_queen(task)


async def get_all_device_traffic_info(device_imei: int, floor: int) -> str:
    """원본 getAllDeviceTrafficInfo: 같은 층의 다른 AGV 위치 정보를 HEX 프레임으로 반환.

    Frame: day(1)+hour(1)+min(1)+sec(1)+ms(2)+count(1)+[deviceNo(1)+returnLineId(4)+
           xPos(4)+yPos(4)+oPos(4)+trafficAreaId(2)+floor(1)+controlStatus(1)+controlDeviceNo(1)] × N
    """
    from datetime import datetime

    keys = await redis_util.wildcard_key(f"{rc.DEVICE_TABLE_PREXFIX}*")
    if not keys:
        return ""

    now = datetime.now()
    header = [
        bp.print_hex_string(bp.int_to_bytes(now.day, 1)),
        bp.print_hex_string(bp.int_to_bytes(now.hour, 1)),
        bp.print_hex_string(bp.int_to_bytes(now.minute, 1)),
        bp.print_hex_string(bp.int_to_bytes(now.second, 1)),
        bp.print_hex_string(bp.int_to_bytes(now.microsecond // 1000, 2)),
    ]
    device_number = 0
    device_parts: list[str] = []
    for key in keys:
        t = await redis_util.get_str_to_object(key)
        if t is None:
            continue
        if t.get("floor") != floor or t.get("deviceImei") == device_imei:
            continue
        device_number += 1
        device_parts.append(bp.print_hex_string(bp.int_to_bytes(t.get("deviceNo") or 0, 1)))
        device_parts.append(bp.print_hex_string(bp.int_to_bytes(t.get("returnLineId") or 0, 4)))
        device_parts.append(bp.print_hex_string(bp.int_to_bytes(t.get("xPosition") or 0, 4)))
        device_parts.append(bp.print_hex_string(bp.int_to_bytes(t.get("yPosition") or 0, 4)))
        device_parts.append(bp.print_hex_string(bp.int_to_bytes(t.get("oPosition") or 0, 4)))
        device_parts.append(bp.print_hex_string(bp.int_to_bytes(t.get("trafficAreaId") or 0, 2)))
        device_parts.append(bp.print_hex_string(bp.int_to_bytes(t.get("floor") or 0, 1)))
        device_parts.append(bp.print_hex_string(bp.int_to_bytes(t.get("controlStatus") or 0, 1)))
        device_parts.append(bp.print_hex_string(bp.int_to_bytes(t.get("controlDeviceNo") or 0, 1)))

    return "".join(header) + bp.print_hex_string(bp.int_to_bytes(device_number, 1)) + "".join(device_parts)


async def restart_device_wifi(imei: int, wifi_strength: int) -> None:
    """원본 restartDeviceWifi: wifi 강도가 임계값 이상(신호 약)이면 재시작 명령 송신.

    10초 TTL 중복 방지 키(WIFI_RESTART_TIME)로 연속 실행을 막는다.
    FUN_CODES[37] = '54' (wifi 재시작 명령), payload: 01 01
    """
    import random

    from app.tcp import constants
    from app.tcp.tcp_client import TaskModel, send_tcp_msg

    restart_time = await redis_util.get_str_to_object(f"{rc.WIFI_RESTART_TIME}{imei}")
    if restart_time is not None:
        return

    restart_value = await redis_util.get_str_to_object(f"{rc.WIFI_RESTART_VALUE}{imei}")
    if restart_value is None:
        return
    try:
        threshold = int(str(restart_value).strip('"'))
    except (ValueError, TypeError):
        return
    if wifi_strength < threshold:
        return

    parts = ["40BF807F"]
    parts.append(bp.print_hex_string(bp.int_to_bytes(random.randint(1, 999999), 4)))
    parts.append(bp.print_hex_string(bp.int_to_bytes(imei, 4)))
    parts.append(constants.FUN_CODES[37])
    parts.append("01")
    parts.append("01")
    task = TaskModel()
    task.funCode = constants.FUN_CODES[37]
    task.requestMsg = bp.get_crc_to_send("".join(parts), "123456789")
    result = await send_tcp_msg(task)
    if result.status:
        await redis_util.set_to_json(f"{rc.WIFI_RESTART_TIME}{imei}", imei, 10)
    else:
        LOGGER.warning("wifi 재시작【%s】명령 응답 실패! %s", imei, result.msg)


async def save_or_update_device(reb: bytes) -> dict:
    """원본 saveOrUpdateDevice: 파싱 후 Redis 저장 + 하트비트 응답 송신.

    저장:
      - DEVICE_HEART_BEAT+imei = 원본 HEX (3초 TTL)
      - deviceTable_suc_+imei = 메모리테이블
      - DEVICE_TASK_TABLE+imei = 메모리테이블 (소비처가 읽는 키)
    """
    table = parse_memory_table(reb)
    imei = table["deviceImei"]
    # LOGGER.warning(
    #     "imei【%s】,userTaskId=【%s】，任务状态为【%s】，任务来源【%s】，键盘锁状态为【%s】，货叉状态为【%s】，库位列状态为【%s】",
    #     imei,
    #     table["userTaskId"],
    #     table["taskFlag"],
    #     table["taskSource"],
    #     table["lockState"],
    #     table["forkStatus"],
    #     table["storageRowFlag"],
    # )
    LOGGER.warning(
        "imei[%s] userTaskId[%s] 작업상태[%s] 작업출처[%s] 키락[%s] 포크상태[%s] 컬럼포인트상태[%s]",
        imei,
        table["userTaskId"],
        table["taskFlag"],
        table["taskSource"],
        table["lockState"],
        table["forkStatus"],
        table["storageRowFlag"],
    )
    await redis_util.set_to_json(f"{rc.DEVICE_HEART_BEAT}{imei}", bp.print_hex_string(reb), 3)
    await redis_util.set_to_str(f"{rc.DEVICE_TABLE_PREXFIX}{imei}", table)
    await redis_util.set_to_str(f"{rc.DEVICE_TASK_TABLE}{imei}", table)
    length = bp.bytes_to_int(bp.split_byte(reb, 13, 14), 1)
    send_heartbeat(imei, table["userTaskId"], length)
    return table
