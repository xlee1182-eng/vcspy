"""SendTask 서비스 (차량으로 작업/명령 프레임 송신).

원본 com.ygcloud.ygvcs.service.task.impl.SendTask 이식 — 현재 terminnateTask 부터.
전체(작업 송신/취소/반복 등)는 UserTask 실작업 milestone에서 확장한다.
"""
from __future__ import annotations

import random

from app.core import messages
from app.core.jsonresult import JsonResult
from app.tcp import byte_process as bp
from app.tcp import constants
from app.tcp.tcp_client import TaskModel, send_tcp_msg


class SendTaskService:
    def __init__(self) -> None:
        self._dispatch_busy: set = set()

    # ---------- 자동 디스패치 (원본 SendTask.execute) ----------
    # 유휴 하트비트 판정에 쓰이는 flag 집합
    IDLE_FLAGS = ("10", "82", "83", "8E", "8F", "95", "E5")

    @classmethod
    def should_dispatch(cls, table: dict) -> bool:
        """원본 saveOrUpdateDevice 말미의 디스패치 조건."""
        return (
            table.get("taskFlag", 0) == 0
            and table.get("forkStatus", 0) == 0
            and table.get("flag") in cls.IDLE_FLAGS
            and table.get("startSiteCode", 0) != 0
        )

    async def dispatch_task(self, db, table: dict) -> bool:
        """원본 SendTask.execute: 유휴 장비에 다음 작업을 픽업·송신.

        serverIsReady 확인 → editAndGetAnTask → (미잠금 시 taskLock 선행) →
        프레임 송신/응답파싱 → 성공 시 send_flag='2'. 송신했으면 True.
        """
        from app.core import redis_constants as rc
        from app.repositories.task import user_task_repository
        from app.services.task_op_service import task_op_service
        from app.tcp.response_parser import is_0xff_or_0x00
        from app.utils import json_util
        from app.utils.redis_util import redis_util

        imei = table["deviceImei"]
        if imei in self._dispatch_busy:
            return False
        self._dispatch_busy.add(imei)
        try:
            ready = await redis_util.get_str_to_object("serverIsReady", str)
            if ready != "yes":
                return False
            ut = await task_op_service.edit_and_get_an_task(db, imei)
            if ut is None:
                return False  # TODO: toPoint(대기점 복귀) 미이식
            way_points = json_util.to_list(ut.way_points) if ut.way_points else []
            frames = self.append_task(ut, imei, way_points)
            if table.get("lockState", 0) == 0:
                frames.insert(0, self.task_lock(imei, 1))  # 키보드 먼저 잠금

            task = TaskModel()
            for frame in frames:
                task.requestMsg = frame
                result = await send_tcp_msg(task)
                if not result.status:
                    return False
                task.funCode = result.msg[24:26]
                task.responseMsg = result.msg
                if not is_0xff_or_0x00(task).status:
                    return False

            ut.device_imei = imei
            ut.send_flag = "2"
            await user_task_repository.update_by_pk(db, ut)
            await redis_util.set_to_json(f"{rc.DEVICE_NOT_TASK_TIME}{imei}", imei, 15)
            await db.commit()
            return True
        finally:
            self._dispatch_busy.discard(imei)

    # ---------- 프레임 빌더 (원본 SendTask) ----------
    def append_way_points_task_msg(self, way_points: list | None) -> str:
        """원본 appendWayPointsTaskMsg: 경유점들을 siteCode(4)+0+handel+height(2) 로."""
        if not way_points:
            return ""
        out = []
        for wp in way_points:
            out.append(bp.print_hex_string(bp.int_to_bytes(int(wp["siteCode"]), 4)))
            out.append("0" + str(wp.get("siteHandel", "0")))
            out.append(bp.print_hex_string(bp.int_to_bytes(int(wp.get("storageHeight") or 0), 2)))
        return "".join(out)

    def append_task_msg(self, ut, device_imei: int, way_points: list | None = None) -> str:
        """원본 appendTaskMsg: B2(작업) 프레임 구성."""
        way = self.append_way_points_task_msg(way_points)
        way_len = 0 if not way else len(way.replace(" ", "")) // 2
        parts = ["40BF807F"]
        parts.append(bp.print_hex_string(bp.int_to_bytes(int(ut.user_task_id), 4)))
        parts.append(bp.print_hex_string(bp.int_to_bytes(int(device_imei), 4)))
        parts.append(constants.FUN_CODES[93])  # B2
        parts.append(bp.print_hex_string(bp.int_to_bytes(14 + way_len, 2)))
        parts.append(bp.print_hex_string(bp.int_to_bytes(int(ut.start_site_code), 4)))
        parts.append("0" + str(ut.start_handel))
        parts.append(bp.print_hex_string(bp.int_to_bytes(int(ut.start_storage_height or 0), 2)))
        parts.append(bp.print_hex_string(bp.int_to_bytes(int(ut.end_site_code or 0), 4)))
        parts.append("0" + (str(ut.end_handel) if ut.end_handel else "0"))
        parts.append(bp.print_hex_string(bp.int_to_bytes(int(ut.end_storage_height or 0), 2)))
        parts.append(way)
        return bp.get_crc_to_send("".join(parts), "123456789")

    def start_task_cmd(self, device_imei: int, state: str) -> str:
        """원본 startTaskCmd: 작업 시작 명령(FUN_CODES[7])."""
        parts = ["40BF807F"]
        parts.append(bp.print_hex_string(bp.int_to_bytes(random.randint(1, 999999), 4)))
        parts.append(bp.print_hex_string(bp.int_to_bytes(int(device_imei), 4)))
        parts.append(constants.FUN_CODES[7])
        parts.append(bp.print_hex_string(bp.int_to_bytes(1, 1)))
        parts.append(state)
        return bp.get_crc_to_send("".join(parts), "123456789")

    def task_lock(self, device_imei: int, state: int) -> str:
        """원본 taskLock: 키보드 잠금(FUN_CODES[94])."""
        parts = ["40BF807F"]
        parts.append(bp.print_hex_string(bp.int_to_bytes(random.randint(1, 999999), 4)))
        parts.append(bp.print_hex_string(bp.int_to_bytes(int(device_imei), 4)))
        parts.append(constants.FUN_CODES[94])
        parts.append(bp.print_hex_string(bp.int_to_bytes(1, 2)))
        parts.append(bp.print_hex_string(bp.int_to_bytes(int(state), 1)))
        return bp.get_crc_to_send("".join(parts), "123456789")

    def append_task(self, ut, device_imei: int, way_points: list | None = None) -> list[str]:
        """원본 appendTask: [작업프레임, 시작명령(FF)]."""
        return [self.append_task_msg(ut, device_imei, way_points), self.start_task_cmd(device_imei, "FF")]

    async def start_or_pause_task(self, device_imei: int, start: str) -> JsonResult:
        """원본 startOrPauseTask: 시작('1'->00) / 일시정지(else->FF) 명령(FUN_CODES[7])."""
        parts = ["40BF807F"]
        parts.append(bp.print_hex_string(bp.int_to_bytes(random.randint(1, 999999), 4)))
        parts.append(bp.print_hex_string(bp.int_to_bytes(int(device_imei), 4)))
        parts.append(constants.FUN_CODES[7])
        parts.append(constants.FUN_LENTHS[7])
        parts.append("00" if start == "1" else "FF")

        task = TaskModel()
        task.funCode = constants.FUN_CODES[7]
        task.requestMsg = bp.get_crc_to_send("".join(parts), "123456789")
        result = await send_tcp_msg(task)
        if result is not None and not result.status:
            return JsonResult.fail("1", messages.get_msg("TaskService.sendTask.TaskIsFail"))
        return JsonResult.success()

    async def terminate_task(self, device_imei: int) -> JsonResult:
        """원본 terminnateTask: 종료 명령(FUN_CODES[16]) 프레임 송신.

        원본은 sendTcpMsg 결과가 null 일 때만 실패로 보고하므로 사실상 항상 성공 반환.
        """
        parts = ["40BF807F"]
        parts.append(bp.print_hex_string(bp.int_to_bytes(random.randint(1, 999999), 4)))
        parts.append(bp.print_hex_string(bp.int_to_bytes(device_imei, 4)))
        parts.append(constants.FUN_CODES[16])
        parts.append(constants.FUN_LENTHS[16])
        parts.append("FFFFFFFF")

        task = TaskModel()
        task.funCode = constants.FUN_CODES[16]
        task.requestMsg = bp.get_crc_to_send("".join(parts), "123456789")
        result = await send_tcp_msg(task)
        if result is None:
            return JsonResult.fail("1", messages.get_msg("TaskService.sendTask.TaskIsFail"))
        return JsonResult.success()


send_task_service = SendTaskService()
