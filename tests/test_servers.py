"""cam/callBox 제네릭 서버 + WS 푸시 서버 검증 (loopback).

실행: python tests/test_servers.py
"""
from __future__ import annotations

import asyncio

from app.tcp import byte_process as bp
from app.tcp import constants
from app.tcp.cam_server import CamServer
from app.tcp.callbox_server import CallBoxServer
from app.tcp.channel_manager import channel_manager
from app.ws.ws_server import WsChannelManager, WsConnection, WsServer

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


def build_frame(imei: int, fun: str, msg_no="00000002", data="0000") -> bytes:
    body = "40BF807F" + msg_no + bp.int_to_hex(imei, 4) + fun + data
    return bp.hex_string_to_bytes(bp.get_crc_to_send(body, "123456789"))


def stream_of(*frames):
    out = bytearray()
    for f in frames:
        out.extend(f)
        out.append(0xA0)
    return bytes(out)


async def _run_frame_server(server_cls, imei):
    received = []
    srv_obj = server_cls(0)
    srv_obj.message_handler = lambda w, frame: received.append(frame)
    srv = await asyncio.start_server(srv_obj._handle, host="127.0.0.1", port=0)
    port = srv.sockets[0].getsockname()[1]
    _, writer = await asyncio.open_connection("127.0.0.1", port)
    writer.write(stream_of(build_frame(imei, "00"), build_frame(imei, "71")))
    await writer.drain()
    await asyncio.sleep(0.1)
    writer.close()
    srv.close()
    await srv.wait_closed()
    return received


async def test_cam_callbox():
    rec = await _run_frame_server(CamServer, 4001)
    check("CamServer 2프레임 수신", len(rec) == 2)
    check("CamServer imei 파싱", rec and channel_manager.imei_of(rec[0]) == 4001)

    rec = await _run_frame_server(CallBoxServer, 4002)
    check("CallBoxServer 2프레임 수신", len(rec) == 2)
    check("CallBoxServer imei 파싱", rec and channel_manager.imei_of(rec[0]) == 4002)


def test_ws_push():
    cm = WsChannelManager()

    class W:
        def __init__(self):
            self.buf = bytearray()

        def write(self, d):
            self.buf.extend(d)

    c1 = WsConnection(W(), "10.0.0.1", "5000")
    c2 = WsConnection(W(), "10.0.0.2", "5001")
    cm.add(c1)
    cm.add(c2)
    # 등록: imei 설정 (frame[8:12])
    cm.handle_message(c1, build_frame(7001, "00"))
    cm.handle_message(c2, build_frame(7002, "00"))
    check("WS imei 등록", c1.imei == 7001 and c2.imei == 7002)

    # 특정 imei 푸시
    resp = build_frame(7001, "B2", data="FF00")
    n = cm.send_msg(resp, is_all=False)
    check("WS 특정 imei 푸시 1건", n == 1 and len(c1.writer.buf) > 0 and len(c2.writer.buf) == 0)

    # 전체 브로드캐스트
    c1.writer.buf.clear()
    n = cm.send_msg(resp, is_all=True)
    check("WS 브로드캐스트 2건", n == 2 and len(c1.writer.buf) > 0 and len(c2.writer.buf) > 0)

    # 길이4 로그인 핑은 imei 변경 안 함
    cm.handle_message(c1, bytes([0x0F, 0x0F, 0x0F, 0x0F]))
    check("WS 로그인핑 imei 불변", c1.imei == 7001)


async def test_ws_server_loopback():
    server = WsServer(0)
    srv = await asyncio.start_server(server._handle, host="127.0.0.1", port=0)
    port = srv.sockets[0].getsockname()[1]
    from app.ws.ws_server import ws_channel_manager
    before = len(ws_channel_manager._conns)
    _, writer = await asyncio.open_connection("127.0.0.1", port)
    await asyncio.sleep(0.05)
    frame = build_frame(7003, "00")
    writer.write(frame + b"\n")
    await writer.drain()
    await asyncio.sleep(0.1)
    check("WS 서버 연결 등록", len(ws_channel_manager._conns) > before)
    writer.close()
    srv.close()
    await srv.wait_closed()


async def main():
    await test_cam_callbox()
    test_ws_push()
    await test_ws_server_loopback()
    print(f"\n결과: {ok} passed, {fail} failed")
    if fail:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
