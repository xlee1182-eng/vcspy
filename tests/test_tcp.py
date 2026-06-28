"""TCP 계층 검증: 프레임 분리 + 요청/응답 상관 + 서버 통합(loopback).

실제 차량 없이, 인메모리/loopback 으로 코덱·상관·서버 읽기루프를 검증한다.
실행: python tests/test_tcp.py
"""
from __future__ import annotations

import asyncio

from app.tcp import byte_process as bp
from app.tcp.channel_manager import channel_manager
from app.tcp.frame_codec import DELIMITER, FrameBuffer
from app.tcp.future_manager import future_manager
from app.tcp.json_msg import JsonMsg
from app.tcp.primary_server import PrimaryServer
from app.tcp.tcp_client import TaskModel, send_tcp_msg

ok = 0
fail = 0


def check(name: str, cond: bool) -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS {name}")
    else:
        fail += 1
        print(f"  FAIL {name}")


def build_frame(imei: int, fun: str, msg_no_hex: str = "00000002", data: str = "0000") -> bytes:
    """유효 프레임(>=16B, 50AFA05F 종단) 생성."""
    body = "40BF807F" + msg_no_hex + bp.int_to_hex(imei, 4) + fun + data
    frame_hex = bp.get_crc_to_send(body, "123456789")
    return bp.hex_string_to_bytes(frame_hex)


def stream_of(*frames: bytes) -> bytes:
    """프레임들을 구분자(50AFA05FA0)로 이어붙인 바이트스트림 구성.
    각 프레임은 ...50AFA05F 로 끝나므로 뒤에 A0 한 바이트를 붙이면 구분자가 된다."""
    out = bytearray()
    for f in frames:
        out.extend(f)
        out.append(0xA0)
    return bytes(out)


# ---------- A. FrameBuffer ----------
def test_frame_buffer():
    f1 = build_frame(1001, "00")
    f2 = build_frame(1001, "71")
    stream = stream_of(f1, f2)
    fb = FrameBuffer()
    frames = fb.feed(stream)
    check("FrameBuffer 2프레임 분리", len(frames) == 2)
    check("프레임1 imei=1001", channel_manager.imei_of(frames[0]) == 1001)
    check("프레임1 종단 50AFA05F", frames[0][-4:] == bytes([0x50, 0xAF, 0xA0, 0x5F]))
    check("프레임2 fun=71", channel_manager.fun_of(frames[1]) == "71")

    # 부분 수신: 절반씩 나눠 feed 해도 누적 후 분리되어야 함
    fb2 = FrameBuffer()
    mid = len(stream) // 2
    r1 = fb2.feed(stream[:mid])
    r2 = fb2.feed(stream[mid:])
    check("부분수신 누적분리", len(r1) + len(r2) == 2)


# ---------- B. 요청/응답 상관 ----------
class FakeWriter:
    def __init__(self):
        self.sent = bytearray()

    def write(self, data):
        self.sent.extend(data)


async def test_correlation():
    imei = 2002
    fw = FakeWriter()
    channel_manager._channels[imei] = fw  # 채널 직접 등록(IP 검사 우회)

    # 요청 송신(fun=71, msgNo=00000005)
    req = build_frame(imei, "71", msg_no_hex="00000005")
    fut = channel_manager.send_msg_sync(req)
    check("send_msg_sync 프레임 송신됨", len(fw.sent) == len(req))

    # 응답 수신(같은 imei/fun/msgNo) → future 완료
    resp = build_frame(imei, "71", msg_no_hex="00000005", data="FF00")
    channel_manager.receive_msg(resp, ip="10.0.0.5")
    msg = await future_manager.wait(fut, timeout=2)
    check("응답 상관 완료(status)", msg.status is True)
    check("응답 otherData=응답바이트", msg.otherData == resp)

    # 타임아웃 경로
    req2 = build_frame(imei, "72", msg_no_hex="00000006")
    fut2 = channel_manager.send_msg_sync(req2)
    msg2 = await future_manager.wait(fut2, timeout=0.3)
    check("미응답 -> 타임아웃 실패", msg2.status is False)

    # send_tcp_msg 통합: 송신 후 응답 오면 HEX 반환
    task = TaskModel()
    task.requestMsg = bp.print_hex_string(build_frame(imei, "73", msg_no_hex="00000007"))
    async def reply_later():
        await asyncio.sleep(0.05)
        r = build_frame(imei, "73", msg_no_hex="00000007", data="FF11")
        channel_manager.receive_msg(r, ip="10.0.0.5")
    asyncio.create_task(reply_later())
    res = await send_tcp_msg(task)
    check("send_tcp_msg 성공 HEX 반환", res.status and isinstance(res.msg, str) and res.msg.endswith("50AFA05F"))

    channel_manager._channels.pop(imei, None)


# ---------- C. 서버 통합 (loopback) ----------
async def test_server_loopback():
    received: list[bytes] = []
    server = PrimaryServer(0)
    server.message_handler = lambda w, frame: received.append(frame)
    # 임의 포트 바인딩
    srv = await asyncio.start_server(server._handle, host="127.0.0.1", port=0)
    port = srv.sockets[0].getsockname()[1]

    reader, writer = await asyncio.open_connection("127.0.0.1", port)
    f1 = build_frame(3003, "00")
    f2 = build_frame(3003, "71")
    writer.write(stream_of(f1, f2))
    await writer.drain()
    await asyncio.sleep(0.1)
    writer.close()
    srv.close()
    await srv.wait_closed()

    check("서버 2프레임 수신", len(received) == 2)
    check("서버 프레임 imei 파싱", received and channel_manager.imei_of(received[0]) == 3003)


async def main():
    test_frame_buffer()
    await test_correlation()
    await test_server_loopback()
    print(f"\n결과: {ok} passed, {fail} failed")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
