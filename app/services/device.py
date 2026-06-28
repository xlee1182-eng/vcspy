"""Device 서비스.

원본 DeviceServiceImpl 이식.
- CRUD(addDevice/editDevice/delDevice/getDeviceInfo) + getAgvHeartList: 완전 이식.
- initLocation/terminateTask: 라이브 TCP 송신 의존 → TCP 서버 milestone에서 완성(스텁).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core import redis_constants as rc
from app.core.jsonresult import JsonResult
from app.repositories.device import (
    device_repository,
    storage_device_relation_repository,
    task_temp_device_repository,
)
from app.schemas.device import (
    DeviceAddForm,
    DeviceDelForm,
    DeviceEditForm,
    DeviceHeartBeat,
    DeviceInfoDto,
    DeviceInfoForm,
)
from app.tcp import byte_process as bp
from app.tcp import constants
from app.utils import json_util
from app.utils.redis_util import redis_util

# Java DeviceWebService.normalStateMap / errorStateMap (flag → 상태 구분용)
_NORMAL_FLAGS = frozenset({
    "00", "01", "04", "05", "13", "14", "18", "19",
    "20", "21", "22", "23", "24", "25", "26", "27", "28",
    "40", "41", "42", "43", "44", "45", "46", "47",
    "50", "51",
    "63", "64", "65", "66", "67", "68", "70",
    "77", "78", "79", "80", "81", "83", "84", "85", "87",
    "89", "8B", "8D", "8E", "8F", "90", "92",
    "9E", "A2", "AA", "AC",
    "B2", "B5", "B7", "B9", "BB", "BD", "BE", "BF",
    "C0", "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "CA", "CB", "CC", "CD", "CE",
    "D2", "D3", "D4", "D9", "DA", "DB", "DC", "DD", "DE",
    "E1", "E2", "E4", "E6", "E7", "EF",
    "F2", "F3", "F5", "F9", "FA", "FF",
    "100", "101", "102", "103", "104", "105", "106", "107", "108", "109", "10A",
    "10B", "10C", "10D", "10E", "10F", "110", "112", "116", "118",
})
_ERROR_FLAGS = frozenset({
    "02", "03", "10", "11", "12", "15", "16", "17", "29",
    "48", "49", "53", "54", "55", "56", "57", "58", "59",
    "60", "61", "62", "69", "71", "72", "73", "74", "75", "76",
    "82", "86", "88", "8A", "8C", "91", "93", "94", "95", "96", "97", "98", "99",
    "9A", "9B", "9C", "9D", "9F",
    "A0", "A1", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "AB", "AD", "AE", "AF",
    "B0", "B1", "B3", "B4", "B6", "B8", "BA", "BC",
    "CF", "D1", "D5", "D6", "D7", "D8", "DF",
    "E3", "E5", "ED", "EE", "F1", "F4", "F6", "F7", "F8", "FB",
    "111", "113", "114", "115", "117",
})


def _device_dict(d) -> dict:
    """yg_device 엔티티 -> camelCase 응답 dict (원본 DeviceEntity JSON 포맷 일치)."""
    return {
        "deviceImei": d.device_imei,
        "deviceName": d.device_name,
        "type": d.type,
        "flag": d.flag,
        "codeAct": d.code_act,
        "ipStr": d.ip_str,
        "action": d.action,
        "isEnable": d.is_enable,
        "callType": d.call_type,
        "createdBy": d.created_by,
        "createdDate": d.created_date,
        "updatedBy": d.updated_by,
        "updatedDate": d.updated_date,
        "deviceHeartBeat": None,
    }


class DeviceService:
    async def get_device_info(self, db: AsyncSession, form: DeviceInfoForm) -> JsonResult:
        """원본 getDeviceInfo: 전체 장비를 type별로 묶고 Redis 상태를 합성."""
        devices = await device_repository.select_all(db)
        if not devices:
            return JsonResult.success()

        prod: dict[str, list[dict]] = {}
        for d in devices:
            prod.setdefault(d.type, []).append(_device_dict(d))

        dto = DeviceInfoDto()

        # type "1": AGV — 메모리테이블 flag + 하트비트
        agv = prod.get("1")
        if agv is not None:
            for item in agv:
                imei = item["deviceImei"]
                mem = await redis_util.get_str_to_object(f"{rc.DEVICE_TABLE_PREXFIX}{imei}")
                item["flag"] = "FF" if mem is None else mem.get("flag")
                hb = await redis_util.get_str_to_object(f"{rc.DEVICE_HEART_BEAT}{imei}", str)
                item["deviceHeartBeat"] = hb.replace('"', "") if hb else None
            dto.deviceAGV = agv

        # type "3": 호출박스
        call = prod.get("3")
        if call is not None:
            for item in call:
                imei = item["deviceImei"]
                val = await redis_util.get_str_to_object(f"{rc.CALL_BOX_TABLE}{imei}", str)
                item["flag"] = "FF" if val is None else val
            dto.deviceCall = call

        dto.deviceCamera = prod.get("2")
        dto.deviceScan = prod.get("4")
        return JsonResult.success(dto.model_dump())

    async def add_device(self, db: AsyncSession, form: DeviceAddForm) -> JsonResult:
        """원본 addDevice."""
        exists = await device_repository.select_by_pk(db, form.deviceImei)
        if exists is not None:
            return JsonResult.fail("1", messages.get_msg("device.addDevice.imeiExists"))

        dup = await device_repository.select(db, {"device_name": form.deviceName})
        if dup:
            return JsonResult.fail("1", messages.get_msg("device.addDevice.nameExists"))

        if form.type == "2" and not (form.action and form.action.strip()):
            return JsonResult.fail("1", messages.get_msg("device.addDevice.actionNotNull"))

        from app.models.tables import Device

        entity = Device(
            device_imei=form.deviceImei,
            device_name=form.deviceName,
            type=form.type,
            is_enable=form.isEnable,
            code_act=form.codeAct,
            action=form.action if (form.action and form.action.strip()) else "2",
            created_by=form.userName,
            created_date=datetime.now(),
        )
        await device_repository.insert(db, entity)
        await db.commit()
        await redis_util.set_to_str(f"{rc.DEVICE_}{entity.device_imei}", json_util.to_dict(entity))
        return JsonResult.success()

    async def edit_device(self, db: AsyncSession, form: DeviceEditForm) -> JsonResult:
        """원본 editDevice."""
        entity = await device_repository.select_by_pk(db, form.deviceImei)
        if entity is None:
            return JsonResult.fail("1", messages.get_msg("device.editDevice.noDevice"))

        entity.code_act = form.codeAct
        if form.deviceName and form.deviceName.strip():
            dup = await device_repository.select(db, {"device_name": form.deviceName})
            if dup:
                return JsonResult.fail("1", messages.get_msg("device.addDevice.nameExists"))
            entity.device_name = form.deviceName
            # 연결된 보관위치 관계의 장비명도 갱신 (updateByConditionSelective)
            await storage_device_relation_repository.update_by_example(
                db, {"device_name": form.deviceName}, {"device_imei": entity.device_imei}
            )
        if form.isEnable and form.isEnable.strip():
            entity.is_enable = form.isEnable
        if form.action and form.action.strip():
            entity.action = form.action
        entity.updated_by = form.userName
        entity.updated_date = datetime.now()
        await device_repository.update_by_pk(db, entity)
        await db.commit()
        await redis_util.set_to_str(f"{rc.DEVICE_}{entity.device_imei}", json_util.to_dict(entity))
        return JsonResult.success()

    async def del_device(self, db: AsyncSession, form: DeviceDelForm) -> JsonResult:
        """원본 delDevice: 장비 + 관계 + 임시작업장비 삭제, Redis 정리."""
        await device_repository.delete_by_pk(db, form.deviceImei)
        await redis_util.delete_by_key(f"{rc.DEVICE_}{form.deviceImei}")
        await storage_device_relation_repository.delete(db, {"device_imei": form.deviceImei})
        if form.deviceImei is not None and form.deviceImei.lstrip("-").isdigit():
            await task_temp_device_repository.delete(db, {"device_imei": int(form.deviceImei)})
        await db.commit()
        await redis_util.delete_by_key(f"{rc.DEVICE_}{form.deviceImei}")
        return JsonResult.success()

    async def get_agv_heart_list(self, form: DeviceInfoForm) -> JsonResult:
        """원본 DeviceWarpWebService.getAgvHeartList: 하트비트 키들에서 imei/command 추출."""
        msg = JsonResult.success()
        keys = await redis_util.wildcard_key(f"{rc.DEVICE_HEART_BEAT}*")
        result: list[dict] = []
        for key in keys or []:
            redis_table = await redis_util.get_str_to_object(key, str)
            if not redis_table or not redis_table.strip():
                continue
            hb = DeviceHeartBeat(
                deviceImei=bp.bytes_to_int(bp.hex_string_to_bytes(redis_table[17:25]), 4),
                command=redis_table.replace('"', ""),
            )
            result.append(hb.model_dump())
        msg.data = result
        return msg

    async def init_location(self, db: AsyncSession, form) -> JsonResult:
        """원본 initLocation: 장비 상태 확인 → 회차라인 조회 → 위치초기화 프레임 송신.

        form: deviceImei(int), siteCode(int).
        """
        import random

        from app.services.forklift_line import forklift_line_service
        from app.tcp import constants
        from app.tcp.tcp_client import TaskModel, send_tcp_msg

        # 1) 장비 메모리테이블 상태 확인
        exit_mem = await redis_util.get_str_to_object(
            f"{rc.DEVICE_TASK_TABLE}{form.deviceImei}"
        )
        flag = exit_mem.get("flag") if isinstance(exit_mem, dict) else None
        if exit_mem is None or flag == "FF":
            return JsonResult.fail("1", messages.get_msg("device.notConnected"))
        # 유휴 상태(77/78/83/79)만 허용
        if flag not in ("77", "78", "83", "79"):
            return JsonResult.fail("1", messages.get_msg("device.notIdle"))

        # 2) 회차 라인(학습 데이터) 조회
        lines = await forklift_line_service.get_line_to_init(
            db, form.deviceImei, site_code=form.siteCode
        )
        if not lines:
            return JsonResult.fail("1", messages.get_msg("site.initLocation.siteCodeLineNotLearn"))

        # 3) 위치초기화 프레임 구성 (원본 contant)
        mem_imei = exit_mem.get("deviceImei", form.deviceImei)
        parts = ["40BF807F"]
        parts.append(bp.print_hex_string(bp.int_to_bytes(random.randint(1, 999999), 4)))
        parts.append(bp.print_hex_string(bp.int_to_bytes(int(mem_imei), 4)))
        parts.append(constants.FUN_CODES[71])
        parts.append("0007")
        parts.append(bp.print_hex_string(bp.int_to_bytes(form.siteCode, 3)))
        first = lines[0]
        if first.get("returnLineId"):
            parts.append("00")
            parts.append(bp.print_hex_string(bp.int_to_bytes(int(first["returnLineId"]), 3)))
        elif first.get("returnParentId"):
            parts.append("00")
            parts.append(bp.print_hex_string(bp.int_to_bytes(int(first["returnParentId"]), 3)))
        else:
            parts.append("00")
            parts.append(bp.print_hex_string(bp.int_to_bytes(0, 3)))

        task = TaskModel()
        task.requestMsg = bp.get_crc_to_send("".join(parts), "123456789")
        result = await send_tcp_msg(task)
        if not result.status:
            return JsonResult.fail("1", messages.get_msg("TaskService.sendTask.TaskIsFail"))
        return JsonResult.success()

    async def terminate_task(self, db: AsyncSession, form) -> JsonResult:
        """원본 terminateTask: 장비 연결 확인 후 종료 작업 송신(SendTask)."""
        from app.services.send_task import send_task_service

        exit_mem = await redis_util.get_str_to_object(
            f"{rc.DEVICE_TASK_TABLE}{form.deviceImei}"
        )
        flag = exit_mem.get("flag") if isinstance(exit_mem, dict) else None
        if exit_mem is None or flag == "FF":
            return JsonResult.fail("1", messages.get_msg("device.notConnected"))
        return await send_task_service.terminate_task(form.deviceImei)

    async def set_wifi_restart_value(self, form) -> JsonResult:
        """원본 setWifiRestartValue: wifi 재시작 임계값을 Redis에 저장."""
        if form.wifiRestartValue is None:
            return JsonResult.fail("1", messages.get_msg("device.setWifiRestartValue.wifiRestartValueNotNull"))
        await redis_util.set_to_str(f"{rc.WIFI_RESTART_VALUE}{form.deviceImei}", form.wifiRestartValue)
        return JsonResult.success()

    async def get_web_device_info(self, device_imei: int) -> JsonResult:
        """원본 DeviceWebService.getDeviceInfo: 장치 상태 조회(외부)."""
        mem = await redis_util.get_str_to_object(f"{rc.DEVICE_TASK_TABLE}{device_imei}")
        if mem is None:
            return JsonResult.fail("1", messages.get_msg("device.getDevice.noDevice"))
        return JsonResult.success(mem)

    async def get_web_device_list(self, db: AsyncSession) -> JsonResult:
        """원본 DeviceWebService.getDeviceList: 장치 목록 조회(외부)."""
        devices = await device_repository.select_all(db)
        return JsonResult.success([_device_dict(d) for d in devices])

    async def set_device_params(self, form) -> JsonResult:
        """원본 setDeviceParams: 포크리프트 파라미터 프레임 TCP 송신 (FUN_CODES[30]='51').

        palletWidth(tableNo=12,idx=13), noCargoHeight(11,35), liftHeight(11,52), haveCargoHeight(11,43)
        """
        import random
        import struct

        from app.tcp import constants
        from app.tcp.response_parser import is_0xff_or_0x00
        from app.tcp.tcp_client import TaskModel, send_tcp_msg

        exit_mem = await redis_util.get_str_to_object(f"{rc.DEVICE_TASK_TABLE}{form.deviceImei}")
        flag = exit_mem.get("flag") if isinstance(exit_mem, dict) else None
        if exit_mem is None or flag == "FF":
            return JsonResult.fail("1", messages.get_msg("device.notConnected"))

        async def _send_param(table_no: int, index: int, value: float) -> JsonResult:
            parts = ["40BF807F"]
            msg_no = random.randint(1, 999999)
            parts.append(bp.print_hex_string(bp.int_to_bytes(msg_no, 4)))
            parts.append(bp.print_hex_string(bp.int_to_bytes(form.deviceImei, 4)))
            parts.append(constants.FUN_CODES[30])   # "51"
            parts.append(bp.print_hex_string(bp.int_to_bytes(7, 2)))
            parts.append(bp.print_hex_string(bp.int_to_bytes(table_no, 1)))
            parts.append(bp.print_hex_string(bp.int_to_bytes(index, 2)))
            parts.append(bp.print_hex_string(struct.pack("<f", value)))  # little-endian float
            task = TaskModel()
            task.funCode = constants.FUN_CODES[30]
            task.requestMsg = bp.get_crc_to_send("".join(parts), "123456789")
            result = await send_tcp_msg(task)
            if not result.status:
                return JsonResult.fail("1", messages.get_msg("TaskService.sendTask.TaskIsFail"))
            return JsonResult.success()

        if form.palletWidth and form.palletWidth > 0:
            value = max(800.0, min(3000.0, form.palletWidth))
            r = await _send_param(12, 13, value)
            if not r.is_success():
                return r
        if form.noCargoHeight and form.noCargoHeight > 0:
            r = await _send_param(11, 35, form.noCargoHeight)
            if not r.is_success():
                return r
        if form.liftHeight and form.liftHeight > 0:
            r = await _send_param(11, 52, form.liftHeight)
            if not r.is_success():
                return r
        if form.haveCargoHeight and form.haveCargoHeight > 0:
            r = await _send_param(11, 43, form.haveCargoHeight)
            if not r.is_success():
                return r
        return JsonResult.success()


    async def set_init_points(self, db: AsyncSession, form) -> JsonResult:
        """원본 setInitPoints: 다중 시작점 초기화 프레임 송신."""
        import random

        from app.repositories.site import site_manage_repository
        from app.services.forklift_line import forklift_line_service
        from app.tcp.tcp_client import TaskModel, send_tcp_msg

        for site_code in (form.sites or []):
            rows = await site_manage_repository.select(db, {"site_manage_id": site_code})
            if not rows:
                return JsonResult.fail(
                    "1",
                    messages.get_msg("TaskService.sendTask.CodeNotExit") + f"【{site_code}】",
                )

        exit_mem = await redis_util.get_str_to_object(f"{rc.DEVICE_TASK_TABLE}{form.deviceImei}")
        flag = exit_mem.get("flag") if isinstance(exit_mem, dict) else None
        if exit_mem is None or flag == "FF":
            return JsonResult.fail("1", messages.get_msg("device.notConnected"))
        if flag not in ("77", "78", "83", "79"):
            return JsonResult.fail("1", messages.get_msg("device.notIdle"))

        sites = form.sites or []
        parts = ["40BF807F"]
        parts.append(bp.print_hex_string(bp.int_to_bytes(random.randint(1, 999999), 4)))
        parts.append(bp.print_hex_string(bp.int_to_bytes(form.deviceImei, 4)))
        parts.append(constants.FUN_CODES[71])
        parts.append(bp.print_hex_string(bp.int_to_bytes(len(sites) * 7, 2)))
        for site_code in sites:
            lines = await forklift_line_service.get_line_to_init(
                db, form.deviceImei, site_code=site_code
            )
            if not lines:
                return JsonResult.fail("1", messages.get_msg("site.initLocation.siteCodeLineNotLearn"))
            parts.append(bp.print_hex_string(bp.int_to_bytes(site_code, 3)))
            first = lines[0]
            if first.get("returnLineId") and int(first["returnLineId"]) != 0:
                parts.append("00")
                parts.append(bp.print_hex_string(bp.int_to_bytes(int(first["returnLineId"]), 3)))
            elif first.get("returnParentId") and int(first["returnParentId"]) != 0:
                parts.append("00")
                parts.append(bp.print_hex_string(bp.int_to_bytes(int(first["returnParentId"]), 3)))
            else:
                parts.append("00")
                parts.append(bp.print_hex_string(bp.int_to_bytes(0, 3)))

        task = TaskModel()
        task.requestMsg = bp.get_crc_to_send("".join(parts), "123456789")
        result = await send_tcp_msg(task)
        if not result.status:
            return JsonResult.fail("1", messages.get_msg("TaskService.sendTask.TaskIsFail"))
        return JsonResult.success()

    async def get_wifi_strength(self, form) -> JsonResult:
        """원본 getWifiStrength: WiFi 신호 강도 조회 (최대 30초 폴링)."""
        import asyncio
        import random
        import time

        from app.tcp.tcp_client import TaskModel, send_task_queen

        exit_mem = await redis_util.get_str_to_object(f"{rc.DEVICE_TASK_TABLE}{form.deviceImei}")
        flag = exit_mem.get("flag") if isinstance(exit_mem, dict) else None
        if exit_mem is None or flag == "FF":
            return JsonResult.fail("1", messages.get_msg("device.notConnected"))
        if flag not in ("77", "78", "83", "79"):
            return JsonResult.fail("1", messages.get_msg("device.notIdle"))

        parts = ["40BF807F"]
        parts.append(bp.print_hex_string(bp.int_to_bytes(random.randint(1, 999999), 4)))
        parts.append(bp.print_hex_string(bp.int_to_bytes(form.deviceImei, 4)))
        parts.append(constants.FUN_CODES[95])           # "B5"
        parts.append(bp.print_hex_string(bp.int_to_bytes(1, 2)))
        parts.append(bp.print_hex_string(bp.int_to_bytes(27, 1)))
        task = TaskModel()
        task.requestMsg = bp.get_crc_to_send("".join(parts), "123456789")
        send_task_queen(task)

        start = time.monotonic()
        while True:
            await asyncio.sleep(1)
            if time.monotonic() - start > 30:
                return JsonResult.success()
            mem = await redis_util.get_str_to_object(f"{rc.DEVICE_TASK_TABLE}{form.deviceImei}")
            wifi = mem.get("wifiStrength") if isinstance(mem, dict) else None
            if wifi is not None and wifi != 0:
                return JsonResult.success(wifi)

    async def set_pause_and_start(self, device_imei: int, status: str) -> JsonResult:
        """원본 setPauseAndStart: 일시정지(1=pause/00) 또는 재시작(2=start/FF) 명령."""
        from app.services.send_task import send_task_service

        exit_mem = await redis_util.get_str_to_object(f"{rc.DEVICE_TASK_TABLE}{device_imei}")
        if exit_mem is None:
            return JsonResult.fail("1", messages.get_msg("device.notConnected"))
        return await send_task_service.start_or_pause_task(device_imei, status)

    async def get_device_treat_info(self, device_imei: int) -> JsonResult:
        """원본 getDeviceTreatInfo: 구분 상태 장치 정보 조회."""
        mem = await redis_util.get_str_to_object(f"{rc.DEVICE_TASK_TABLE}{device_imei}")
        if mem is None:
            return JsonResult.success()
        flag = mem.get("flag") if isinstance(mem, dict) else None
        flag_status = 2 if (flag and flag not in _NORMAL_FLAGS and flag in _ERROR_FLAGS) else 1
        return JsonResult.success({"deviceFlagStatus": flag_status, "deviceTable": mem})

    async def get_time_and_data(self, form) -> JsonResult:
        """원본 getTimeAndData: 장치 총 주행 거리 조회 (warp)."""
        import random
        from datetime import datetime

        from app.tcp.response_parser import is_0xff_or_0x00
        from app.tcp.tcp_client import TaskModel, send_tcp_msg

        exit_mem = await redis_util.get_str_to_object(f"{rc.DEVICE_TASK_TABLE}{form.deviceImei}")
        flag = exit_mem.get("flag") if isinstance(exit_mem, dict) else None
        if exit_mem is None or flag == "FF":
            return JsonResult.fail("1", messages.get_msg("device.notConnected"))
        if flag not in ("77", "78", "79", "83", "8F"):
            return JsonResult.fail("1", messages.get_msg("device.notIdle"))

        now = datetime.now()
        parts = ["40BF807F"]
        parts.append(bp.print_hex_string(bp.int_to_bytes(random.randint(1, 999999), 4)))
        parts.append(bp.print_hex_string(bp.int_to_bytes(form.deviceImei, 4)))
        parts.append(constants.FUN_CODES[96])           # "9E"
        parts.append(bp.print_hex_string(bp.int_to_bytes(10, 2)))
        parts.append(bp.print_hex_string(bp.int_to_bytes(1, 1)))
        parts.append(bp.print_hex_string(bp.int_to_bytes(now.year, 2)))
        parts.append(bp.print_hex_string(bp.int_to_bytes(now.month, 1)))
        parts.append(bp.print_hex_string(bp.int_to_bytes(now.day, 1)))
        parts.append(bp.print_hex_string(bp.int_to_bytes(now.hour, 1)))
        parts.append(bp.print_hex_string(bp.int_to_bytes(now.minute, 1)))
        parts.append(bp.print_hex_string(bp.int_to_bytes(now.second, 1)))
        parts.append(bp.print_hex_string(bp.int_to_bytes(now.microsecond // 1000, 2)))

        task = TaskModel()
        task.funCode = constants.FUN_CODES[96]
        task.requestMsg = bp.get_crc_to_send("".join(parts), "123456789")
        result = await send_tcp_msg(task)
        if not result.status:
            return JsonResult.fail("1", messages.get_msg("TaskService.sendTask.TaskIsFail"))
        task.responseMsg = result.msg
        parsed = is_0xff_or_0x00(task)
        if not parsed.status:
            return JsonResult.fail("1", messages.get_msg("TaskService.sendTask.TaskIsFail"))
        data = parsed.otherData or ""
        total_mileage = 0
        if isinstance(data, str) and len(data) >= 40:
            total_mileage = bp.bytes_to_int(bp.hex_string_to_bytes(data[32:40]), 4)
        return JsonResult.success({"totalMileage": total_mileage})


device_service = DeviceService()
