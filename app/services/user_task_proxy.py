"""UserTaskProxyService 이식.

원본: com.ygcloud.ygvcs.service.task.impl.UserTaskProxyService
하트비트(fun=00) 수신 시 taskFlag/forkStatus 처리,
스토리지 상태 갱신, 잠금/응답 프레임 송신.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from app.tcp import byte_process as bp
from app.tcp import constants
from app.tcp.tcp_client import TaskModel, send_task_queen

LOGGER = logging.getLogger('app')


@dataclass
class _TaskInfo:
    user_task_id: int
    flag: str
    device_imei: int
    task_flag: int


class UserTaskProxyService:
    def __init__(self) -> None:
        # imei → _TaskInfo : 동일 imei+taskId+taskFlag 중복 DB 쓰기 방지 (원본 flagMap)
        self._flag_map: dict[int, _TaskInfo] = {}

    # ------------------------------------------------------------------ #
    # 내부 헬퍼                                                            #
    # ------------------------------------------------------------------ #

    def _is_update_db(self, task: _TaskInfo) -> bool:
        """원본 isUpdateDb: 같은 imei + taskId + taskFlag 조합이면 False."""
        old = self._flag_map.get(task.device_imei)
        if (
            old is not None
            and old.user_task_id == task.user_task_id
            and old.task_flag == task.task_flag
        ):
            return False
        self._flag_map[task.device_imei] = task
        return True

    async def _get_fork_state(self, frame: bytes) -> int:
        """원본 getForkState: 이미 처리된 forkStatus 면 재응답 후 -1 반환."""
        from app.core import redis_constants as rc
        from app.utils.redis_util import redis_util

        imei = bp.bytes_to_int(bp.split_byte(frame, 8, 12), 4)
        user_task_id = bp.bytes_to_int(bp.split_byte(frame, 4, 8), 4)
        fork_status = bp.bytes_to_int(bp.split_byte(frame, 30, 31), 1) & 3
        if fork_status == 0:
            return -1
        fork_action = await redis_util.get_str_to_object(
            f"{rc.DEVICE_FORK_STATUS}{imei}_{user_task_id}", int
        )
        if fork_action is not None and fork_action == fork_status:
            self.reply_fork_state(imei, user_task_id, fork_status)
            return -1
        return fork_status

    # ------------------------------------------------------------------ #
    # 송신 헬퍼                                                            #
    # ------------------------------------------------------------------ #

    async def send_unlock(self, imei: int, lock_state: int) -> bool:
        """원본 sendUnlock: lockState != 0 이면 키보드 잠금 해제 명령 송신·응답 대기."""
        if lock_state == 0:
            return True
        from app.services.send_task import send_task_service
        from app.tcp.tcp_client import send_tcp_msg

        task = TaskModel()
        task.requestMsg = send_task_service.task_lock(imei, 0)
        result = await send_tcp_msg(task)
        if not result.status:
            LOGGER.warning("잠금 해제【%s】 명령 응답 실패! %s", imei, result.msg)
            return False
        return True

    def reply_state(self, task: _TaskInfo) -> None:
        """원본 replyState: taskFlag 응답 프레임(FUN_CODES[40]='58') 송신."""
        try:
            parts = ["40BF807F"]
            parts.append(bp.print_hex_string(bp.int_to_bytes(task.user_task_id, 4)))
            parts.append(bp.print_hex_string(bp.int_to_bytes(task.device_imei, 4)))
            parts.append(constants.FUN_CODES[40])   # "58"
            parts.append(constants.FUN_LENTHS[40])  # "01"
            parts.append(bp.print_hex_string(bp.int_to_bytes(task.task_flag, 1)))
            t = TaskModel()
            t.funCode = constants.FUN_CODES[40]
            t.requestMsg = bp.get_crc_to_send("".join(parts), "123456789")
            send_task_queen(t)
        except Exception:
            LOGGER.exception("replyState 오류!")

    def reply_fork_state(self, imei: int, user_task_id: int, fork_status: int) -> None:
        """원본 replyForkState: 포크 상태 응답 프레임(fun=9D) 송신."""
        try:
            LOGGER.error("장비【%s】 포크 상태【%s】 처리!", imei, fork_status)
            parts = ["40BF807F"]
            parts.append(bp.print_hex_string(bp.int_to_bytes(user_task_id, 4)))
            parts.append(bp.print_hex_string(bp.int_to_bytes(imei, 4)))
            parts.append("9D")
            parts.append("0001")
            parts.append(bp.print_hex_string(bp.int_to_bytes(fork_status, 1)))
            t = TaskModel()
            t.funCode = "9D"
            t.requestMsg = bp.get_crc_to_send("".join(parts), "123456789")
            send_task_queen(t)
        except Exception:
            LOGGER.exception("replyForkState 오류!")

    # ------------------------------------------------------------------ #
    # 주요 비즈니스 로직                                                   #
    # ------------------------------------------------------------------ #

    async def update_task(self, db, frame: bytes) -> None:
        """원본 updateTask: taskFlag(bits7-4 of byte31) 에 따른 작업 상태 DB 갱신."""
        from datetime import datetime

        from app.core import redis_constants as rc
        from app.repositories.site import storage_repository
        from app.repositories.task import user_task_repository
        from app.utils.redis_util import redis_util

        imei = bp.bytes_to_int(bp.split_byte(frame, 8, 12), 4)
        user_task_id = bp.bytes_to_int(bp.split_byte(frame, 4, 8), 4)
        flag = bp.print_hex_string(bp.split_byte(frame, 14, 15))
        self_consistent_flag = bp.bytes_to_int(bp.split_byte(frame, 120, 121), 1)
        lock_state = (self_consistent_flag >> 3) & 1
        task_flag = (bp.bytes_to_int(bp.split_byte(frame, 31, 32), 1) >> 4) & 0xFF

        if task_flag == 0:
            return

        wait_time = await redis_util.get_str_to_object(rc.DEVICE_NOT_TASK_TO_WAIT_POINT_TIME, int)
        if wait_time is None:
            wait_time = 15

        task = _TaskInfo(
            user_task_id=user_task_id,
            flag=flag,
            device_imei=imei,
            task_flag=task_flag,
        )

        try:
            if task_flag == 1:
                LOGGER.warning("update to 3, taskId:%s, taskFlag:%s", user_task_id, task_flag)
                if not await self.send_unlock(imei, lock_state):
                    LOGGER.warning("imei【%s】 키보드 잠금해제 실패!", imei)
                    return
                if self._is_update_db(task):
                    await user_task_repository.update_by_example(
                        db, {"send_flag": "3"}, {"user_task_id": user_task_id}
                    )
                    ut = await user_task_repository.select_by_pk(db, user_task_id)
                    if ut and ut.end_site_code and ut.end_handel == "2":
                        rows = await storage_repository.select(db, {"site_code": ut.end_site_code})
                        if rows:
                            s = rows[0]
                            if s.site_type == "1":
                                s.site_status = "1"
                                s.updated_date = datetime.now()
                                await storage_repository.update_by_pk(db, s)
                                await redis_util.set_to_json(
                                    f"{rc.STORAGE_STATE}{ut.end_site_code}", "1", 10
                                )
                            elif s.site_type == "2" and s.site_status == "3":
                                s.site_status = "0"
                                s.updated_date = datetime.now()
                                await storage_repository.update_by_pk(db, s)
                self.reply_state(task)
                await redis_util.set_to_json(f"{rc.DEVICE_NOT_TASK_TIME}{imei}", imei, wait_time)
                LOGGER.warning("imei:%s, taskId:%s, 상태3 변경 성공!", imei, user_task_id)

            elif task_flag == 2:
                if self._is_update_db(task):
                    await user_task_repository.update_by_example(
                        db, {"send_flag": "2"}, {"user_task_id": user_task_id}
                    )
                    LOGGER.warning("imei:%s, taskId:%s, 상태2 변경 성공!", imei, user_task_id)
                self.reply_state(task)

            elif task_flag == 3:
                LOGGER.warning("update to 4, taskId:%s, taskFlag:%s", user_task_id, task_flag)
                if not await self.send_unlock(imei, lock_state):
                    LOGGER.warning("imei【%s】 키보드 잠금해제 실패!", imei)
                    return
                if self._is_update_db(task):
                    await user_task_repository.update_by_example(
                        db, {"send_flag": "4"}, {"user_task_id": user_task_id}
                    )
                self.reply_state(task)
                await redis_util.set_to_json(f"{rc.DEVICE_NOT_TASK_TIME}{imei}", imei, wait_time)
                LOGGER.warning("imei:%s, taskId:%s, 상태4 변경 성공!", imei, user_task_id)

            elif task_flag == 4:
                LOGGER.warning("update to 7, taskId:%s, taskFlag:%s", user_task_id, task_flag)
                if not await self.send_unlock(imei, lock_state):
                    LOGGER.warning("imei【%s】 키보드 잠금해제 실패!", imei)
                    return
                if self._is_update_db(task):
                    await user_task_repository.update_by_example(
                        db, {"send_flag": "7"}, {"user_task_id": user_task_id}
                    )
                self.reply_state(task)
                await redis_util.set_to_json(f"{rc.DEVICE_NOT_TASK_TIME}{imei}", imei, wait_time)
                LOGGER.warning("imei:%s, taskId:%s, 상태7 변경 성공!", imei, user_task_id)

            else:
                self._is_update_db(task)

        except Exception:
            LOGGER.exception("update_task 오류!")

    async def update_storage_state(self, db, frame: bytes) -> None:
        """원본 updateStorageState: storageRowFlag/forkState 에 따른 창고 슬롯 상태 갱신."""
        from datetime import datetime

        from app.core import redis_constants as rc
        from app.repositories.site import storage_repository
        from app.repositories.task import user_task_repository
        from app.utils.redis_util import redis_util

        try:
            imei = bp.bytes_to_int(bp.split_byte(frame, 8, 12), 4)
            user_task_id = bp.bytes_to_int(bp.split_byte(frame, 4, 8), 4)
            start_id = bp.bytes_to_int(bp.split_byte(frame, 15, 18), 3)
            end_id = bp.bytes_to_int(bp.split_byte(frame, 18, 21), 3)
            self_consistent_flag = bp.bytes_to_int(bp.split_byte(frame, 120, 121), 1)
            storage_row_flag = (self_consistent_flag >> 1) & 2

            # 창고 열 상태 갱신 (storageRowFlag == 1 or 2)
            if storage_row_flag in (1, 2):
                site_status = "0" if storage_row_flag == 1 else "1"
                for site_code in (start_id, end_id):
                    rows = await storage_repository.select(db, {"site_code": site_code})
                    if rows and rows[0].site_type == "2":
                        rows[0].site_status = site_status
                        rows[0].updated_date = datetime.now()
                        await storage_repository.update_by_pk(db, rows[0])
                    else:
                        LOGGER.warning(
                            "창고 열 상태 변경 시 위치【%s】가 창고 열이 아닙니다!", site_code
                        )
                self.reply_fork_state(imei, user_task_id, storage_row_flag + 2)

            # 포크 상태 갱신 (forkState == 1: 취화완료, 2: 방화완료)
            fork_state = await self._get_fork_state(frame)
            if fork_state <= 0:
                return

            task_by_id = await user_task_repository.select_by_pk(db, user_task_id)
            if task_by_id is None:
                return

            if fork_state == 1:
                task_by_id.pick_place_state = "1"
                await user_task_repository.update_by_pk(db, task_by_id)
                msg_id = task_by_id.message_id or str(user_task_id)
                LOGGER.warning("messageId:%s 취화 완료!", msg_id)
                if task_by_id.start_site_code:
                    rows = await storage_repository.select(db, {"site_code": task_by_id.start_site_code})
                    if rows and rows[0].site_type == "1":
                        rows[0].site_status = "0"
                        rows[0].updated_date = datetime.now()
                        await storage_repository.update_by_pk(db, rows[0])
                if task_by_id.message_id:
                    await redis_util.set_to_json(
                        f"{rc.TASK_STATE}_{task_by_id.message_id}", task_by_id, 10
                    )
                await redis_util.set_to_json(
                    f"{rc.DEVICE_FORK_STATUS}{imei}_{user_task_id}", fork_state, 86400
                )
                self.reply_fork_state(imei, user_task_id, fork_state)

            elif fork_state == 2:
                task_by_id.pick_place_state = "2"
                await user_task_repository.update_by_pk(db, task_by_id)
                msg_id = task_by_id.message_id or str(user_task_id)
                LOGGER.warning("messageId:%s 방화 완료!", msg_id)
                if task_by_id.end_site_code:
                    rows = await storage_repository.select(db, {"site_code": task_by_id.end_site_code})
                    if rows and rows[0].site_type == "1":
                        rows[0].site_status = "1"
                        rows[0].updated_date = datetime.now()
                        await storage_repository.update_by_pk(db, rows[0])
                if task_by_id.message_id:
                    await redis_util.set_to_json(
                        f"{rc.TASK_STATE}_{task_by_id.message_id}", task_by_id, 10
                    )
                await redis_util.set_to_json(
                    f"{rc.DEVICE_FORK_STATUS}{imei}_{user_task_id}", fork_state, 86400
                )
                self.reply_fork_state(imei, user_task_id, fork_state)

        except Exception:
            LOGGER.exception("update_storage_state 오류!")


user_task_proxy_service = UserTaskProxyService()
