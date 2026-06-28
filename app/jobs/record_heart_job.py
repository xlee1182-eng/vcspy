"""하트비트/운영 플래그 갱신 작업.

원본 com.ygcloud.ygvcs.job.RecordHeartJob 이식.
주기적으로 Redis 의 운영 플래그를 읽어 전역 상태에 반영한다.
"""
from __future__ import annotations

from app.utils.redis_util import redis_util


class RecordHeart:
    """원본 RecordHeartJob 의 정적 플래그 묶음."""

    record_heart: bool = False
    turn_on_station: bool = False
    server_is_ready: bool = False
    open_traffic: bool = False
    storage_not_turn_round: bool = False


async def execute() -> None:
    """원본 execute(): Redis 플래그 → 전역 상태."""
    s = await redis_util.get_str_to_object("record.heart", str)
    RecordHeart.record_heart = (not s) or (s != "off")
    RecordHeart.turn_on_station = (await redis_util.get_str_to_object("turn.ontransfer.station", str)) == "on"
    RecordHeart.server_is_ready = (await redis_util.get_str_to_object("serverIsReady", str)) == "yes"
    RecordHeart.open_traffic = (await redis_util.get_str_to_object("is.open.traffic", str)) == "on"
    RecordHeart.storage_not_turn_round = (await redis_util.get_str_to_object("stotage.is.turn.round", str)) == "on"

    # print("스케줄러(record_heart 5s) 갱신: record_heart=%s, turn_on_station=%s, server_is_ready=%s, open_traffic=%s, storage_not_turn_round=%s" % (
    #     RecordHeart.record_heart,
    #     RecordHeart.turn_on_station,
    #     RecordHeart.server_is_ready,
    #     RecordHeart.open_traffic,
    #     RecordHeart.storage_not_turn_round,
    # ))
