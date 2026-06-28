"""Snowflake ID 생성기.

원본 com.ygcloud.ygvcs.utils.SnowFlakeIds / IdUtils 이식.
파라미터 원본 동일: twepoch=1633881600000, workerId=1, datacenterId=1,
sequence 12bit, worker 5bit, datacenter 5bit. 결과는 기존 ID 체계와 호환.
"""
from __future__ import annotations

import threading
import time


class SnowFlakeIds:
    TWEPOCH = 1633881600000
    WORKER_ID_BITS = 5
    DATACENTER_ID_BITS = 5
    SEQUENCE_BITS = 12
    WORKER_ID_SHIFT = 12
    DATACENTER_ID_SHIFT = 17
    TIMESTAMP_LEFT_SHIFT = 22
    SEQUENCE_MASK = 0xFFF  # 4095

    def __init__(self, worker_id: int = 1, datacenter_id: int = 1):
        if worker_id > 31 or worker_id < 0:
            raise ValueError("worker Id can't be greater than 31 or less than 0")
        if datacenter_id > 31 or datacenter_id < 0:
            raise ValueError("datacenter Id can't be greater than 31 or less than 0")
        self.worker_id = worker_id
        self.datacenter_id = datacenter_id
        self.sequence = 0
        self.last_timestamp = -1
        self._lock = threading.Lock()

    @staticmethod
    def _time_gen() -> int:
        return int(time.time() * 1000)

    def _til_next_millis(self, last_timestamp: int) -> int:
        ts = self._time_gen()
        while ts <= last_timestamp:
            ts = self._time_gen()
        return ts

    def next_id(self) -> int:
        with self._lock:
            timestamp = self._time_gen()
            if self.last_timestamp == timestamp:
                self.sequence = (self.sequence + 1) & self.SEQUENCE_MASK
                if self.sequence == 0:
                    timestamp = self._til_next_millis(self.last_timestamp)
            else:
                self.sequence = 0
            self.last_timestamp = timestamp
            return (
                ((timestamp - self.TWEPOCH) << self.TIMESTAMP_LEFT_SHIFT)
                | (self.datacenter_id << self.DATACENTER_ID_SHIFT)
                | (self.worker_id << self.WORKER_ID_SHIFT)
                | self.sequence
            )

    def next_id_str(self) -> str:
        return str(self.next_id())


# 원본 SnowFlakeIds.INSTANCE = new SnowFlakeIds(1L, 1L)
_INSTANCE = SnowFlakeIds(1, 1)


def next_id() -> str:
    """원본 IdUtils.nextId(): 문자열 ID."""
    return _INSTANCE.next_id_str()


def next_id_long() -> int:
    return _INSTANCE.next_id()
