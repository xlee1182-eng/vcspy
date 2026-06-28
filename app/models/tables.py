"""schema.sql에서 자동 생성된 SQLAlchemy 2.0 모델.

생성기: scripts/gen_models.py  (DB 미접속, schema.sql만 파싱)
원본 MySQL 컬럼 주석은 comment= 및 줄끝 주석으로 보존했다.
수기 수정 시 재생성으로 덮어쓰일 수 있으니 주의.
"""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Date, DateTime, Float, Integer, LargeBinary,
    Numeric, String, Text, Time,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Sequence(Base):
    """sequence"""

    __tablename__ = "sequence"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False, comment="시퀀스 코드")
    name: Mapped[str] = mapped_column(String(32), nullable=False, comment="시퀀스 이름")
    current_value: Mapped[int] = mapped_column(Integer, nullable=False)
    increment: Mapped[int] = mapped_column(Integer, nullable=False)
    remark: Mapped[str] = mapped_column(String(255), nullable=False, comment="비고")


class SysUser(Base):
    """sys_user — 사용자 테이블"""

    __tablename__ = "sys_user"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False, comment="사용자 ID")
    resource_id: Mapped[str | None] = mapped_column(String(13), nullable=True, comment="리소스 ID: x-x-xxxx-xxxx, 국가1자리-제조사1자리-대리점4자리-회사4자리")
    user_type: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="사용자 유형: 1 VCS 슈퍼관리자, 2 제조사 사용자, 3 대리점 사용자, 4 기업 사용자")
    role_type: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="역할 유형: 1: 관리자, 2: 일반 사용자")
    client_type: Mapped[str] = mapped_column(String(2), nullable=False, comment="클라이언트 유형(1: 모바일, 2: 패드, 3: PC)")
    user_name: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="사용자명")
    password: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="비밀번호")
    sex: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="성별")
    age: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="나이")
    phone: Mapped[str | None] = mapped_column(String(18), nullable=True, comment="전화번호")
    address: Mapped[str | None] = mapped_column(String(400), nullable=True, comment="주소")
    post_code: Mapped[str | None] = mapped_column(String(6), nullable=True, comment="우편번호")
    email: Mapped[str | None] = mapped_column("EMAIL", String(32), nullable=True, comment="이메일")
    delete_flag: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="유효 여부: 0 무효, 1 유효")
    created_date: Mapped[datetime | None] = mapped_column("CREATED_DATE", DateTime, nullable=True, comment="생성 시간")
    created_by: Mapped[int | None] = mapped_column("CREATED_BY", BigInteger, nullable=True, comment="생성자")
    updated_date: Mapped[datetime | None] = mapped_column("UPDATED_DATE", DateTime, nullable=True, comment="수정 시간")
    updated_by: Mapped[int | None] = mapped_column("UPDATED_BY", BigInteger, nullable=True, comment="수정자")
    is_online: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="0: 오프라인, 1: 온라인")


class CallBoxInfo(Base):
    """yg_call_box_info"""

    __tablename__ = "yg_call_box_info"

    call_box_info_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False, comment="호출박스 바인딩 정보 ID")
    resource_id: Mapped[str | None] = mapped_column(String(13), nullable=True, comment="리소스 ID")
    call_box_imei: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="호출박스 IMEI")
    number: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="버튼 번호")
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class CamInfConfig(Base):
    """yg_cam_inf_config"""

    __tablename__ = "yg_cam_inf_config"

    cam_inf_config_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False, comment="카메라 기본 설정 ID")
    prove: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="prove = pro 이면 운영 환경, 그 외는 테스트 환경")
    online: Mapped[str | None] = mapped_column(String(255), nullable=True)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True, comment="임계값")
    feature_points_threshold: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="유사점 임계값")
    noise_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    totlapic: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="총 촬영 이미지 수")
    repeattimes: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="간격 시간(ms)")
    holdpic: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="정확한 이미지로 판단하는 동일 이미지 장 수")


class CamStoragePicParams(Base):
    """yg_cam_storage_pic_params"""

    __tablename__ = "yg_cam_storage_pic_params"

    cam_storage_pic_params_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False, comment="카메라 보관위치 이미지 파라미터")
    ip_str: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="카메라 IP")
    device_imei: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="카메라 IMEI")
    upcox: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="X 좌표")
    upcoy: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="Y 좌표")
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    index_no: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="보관위치 인덱스, 0부터 시작")
    site_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="보관위치 코드")
    site_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="보관위치 이름")
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Device(Base):
    """yg_device — 장치 정보 메모리 테이블"""

    __tablename__ = "yg_device"

    device_imei: Mapped[str] = mapped_column(String(32), primary_key=True, nullable=False, comment="imei")
    ip_str: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="카메라 IP")
    device_name: Mapped[str | None] = mapped_column(String(1024), nullable=True, comment="name")
    type: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="장치 유형: 1 AGV, 2 카메라, 3 호출박스, 4 스캐너")
    flag: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="장치 상태 - 호출박스(00 대기 상태, 01 작업 중)")
    code_act: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="스테이션 동작: 1: 호출(창고 비우기), 2: 입고(창고 채우기)")
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_enable: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="활성화 여부: 0 활성, 1 비활성")
    action: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="장치 역할: 1 보관위치 모니터링(바인딩), 2 보관위치 모니터링 및 작업 생성(차량 호출)")
    call_type: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="스캔 차량 호출 유형: 0 임의 위치 실행 가능, 1 대기점 실행")


class Device20250421(Base):
    """yg_device_20250421"""

    __tablename__ = "yg_device_20250421"

    device_imei: Mapped[str] = mapped_column(String(32), primary_key=True, nullable=False, comment="imei")
    device_name: Mapped[str | None] = mapped_column(String(1024), nullable=True, comment="name")
    type: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="장치 유형: 1 AGV, 2 카메라, 3 호출박스, 4 스캐너")
    flag: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="장치 상태 - 호출박스(00 대기 상태, 01 작업 중)")
    code_act: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="스테이션 동작: 1: 호출, 2: 입고")
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_enable: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="활성화 여부: 0 활성, 1 비활성")
    action: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="장치 역할: 1 보관위치 모니터링, 2 보관위치 모니터링 및 작업 생성")


class DeviceMemoryTable(Base):
    """yg_device_memory_table — 장치 정보 메모리 테이블"""

    __tablename__ = "yg_device_memory_table"

    device_imei: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, comment="imei")
    device_name: Mapped[str | None] = mapped_column(String(1024), nullable=True, comment="name")
    model: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="모드: 0: 대기, 1: 학습, 2: 작업, 3: 설정")
    flag: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="장치 상태: 0x00: 대기, 0x41: 학습 대기, 0x42: 학습 중, 0x80: 위치 스위치 경보, 0x83: 작업 없이 실행, 0x84: 작업 있이 실행, 0x85: 실행 중, 0x86: 차체 계산 경보, 0x87: 실행 일시정지, 0x88: 데이터 파일 경보, 0x89: 초음파 경보, 0x8A: 안전 접촉 경보, 0x8B: 수동/자동 스위치 경보, 0x8C: 긴급 정지 중, 0x8D: 레이더 경보, 0x8E: 충전 중, 0x8F: 충전 완료, 0xC3: 설정 모드 작업 없음, 0xC4: 설정 모드 작업 있음, 0xC5: 설정 모드 실행 중, 0xC6: 설정 모드 차체 경보, 0xC7: 설정 모드 작업 있음 일시정지, 0xFF: 오프라인")
    battery_level: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="배터리 잔량")
    task_number: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="현재 작업 번호")
    user_task_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="메시지 번호")
    end_site_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="종료점 ID")
    start_site_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="시작점 ID")
    fork_status: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="화물 적재 상태: 0: 없음, 1: 있음")
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    running_loop: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="0: 비순환 작업, 1: 순환 작업 중")
    last_update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="마지막 수정 시간")
    is_valid: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="차량 유효 여부: 0 유효, 1 무효")
    customer_id: Mapped[str | None] = mapped_column(String(4), nullable=True, comment="기업 ID")
    steps: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="이동 단계 수")
    crc_false: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="차량 CRC 상태: 0 유효, 1 오류, 2 무효")


class DeviceMemoryTable20250421(Base):
    """yg_device_memory_table_20250421"""

    __tablename__ = "yg_device_memory_table_20250421"

    device_imei: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, comment="imei")
    device_name: Mapped[str | None] = mapped_column(String(1024), nullable=True, comment="name")
    model: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="모드: 0: 대기, 1: 학습, 2: 작업, 3: 설정")
    flag: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="장치 상태: 0x00: 대기, 0x41: 학습 대기, 0x42: 학습 중, 0x80: 위치 스위치 경보, 0x83: 작업 없이 실행, 0x84: 작업 있이 실행, 0x85: 실행 중, 0x86: 차체 계산 경보, 0x87: 실행 일시정지, 0x88: 데이터 파일 경보, 0x89: 초음파 경보, 0x8A: 안전 접촉 경보, 0x8B: 수동/자동 스위치 경보, 0x8C: 긴급 정지 중, 0x8D: 레이더 경보, 0x8E: 충전 중, 0x8F: 충전 완료, 0xC3: 설정 모드 작업 없음, 0xC4: 설정 모드 작업 있음, 0xC5: 설정 모드 실행 중, 0xC6: 설정 모드 차체 경보, 0xC7: 설정 모드 작업 있음 일시정지, 0xFF: 오프라인")
    battery_level: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="배터리 잔량")
    task_number: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="현재 작업 번호")
    user_task_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="메시지 번호")
    end_site_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="종료점 ID")
    start_site_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="시작점 ID")
    fork_status: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="화물 적재 상태: 0: 없음, 1: 있음")
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    running_loop: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="0: 비순환 작업, 1: 순환 작업 중")
    last_update_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="마지막 수정 시간")
    is_valid: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="차량 유효 여부: 0 유효, 1 무효")
    customer_id: Mapped[str | None] = mapped_column(String(4), nullable=True, comment="기업 ID")
    steps: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="이동 단계 수")
    crc_false: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="차량 CRC 상태: 0 유효, 1 오류, 2 무효")


class ForkliftLine(Base):
    """yg_forklift_line — 지게차 노선 테이블"""

    __tablename__ = "yg_forklift_line"

    forklift_line_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, comment="ID")
    line_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="노선 이름")
    start_site_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="시작 스테이션 ID")
    start_site_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="시작 스테이션 이름")
    start_site_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="시작 스테이션 코드")
    end_site_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="종료 스테이션 ID")
    end_site_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="종료 스테이션 이름")
    end_site_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="종료 스테이션 코드")
    device_imei: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="지게차 IMEI")
    step_number: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="이동 단계 수")
    is_backing_up: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="0: 정방향 단방향, 1: 후진 단방향, 2: 양방향, 3: 경로 계획에 사용 안 함")
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    parent_line_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="주선 ID")
    start_site_x: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="시작점 X 좌표")
    start_site_y: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="시작점 Y 좌표")
    end_site_x: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="종료점 X 좌표")
    end_site_y: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="종료점 Y 좌표")
    line_attr: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="노선 속성: 0: 주선, 1: 주선 따라 학습한 지선, 2: 후진 지선, 3: 정방향 출고 지선, 4: 수동 학습 지선")
    return_line_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="차체 복귀 주선 ID")
    return_parent_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="차체 복귀 주선 ID (상위 ID)")
    area_id: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="소속 작업장")
    is_radar: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="레이더 구성 여부: 0: 아니오, 1: 예")
    line_item: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="노선 유형: 0: 실내 노선, 1: 실외 노선, 2: 실내 관성 항법")
    is_corrects_line: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="직선 노선 보정 여부: 0: 아니오, 1: 예")
    customer_id: Mapped[str | None] = mapped_column(String(4), nullable=True, comment="기업 ID")
    floor: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="소속 층")


class ForkliftLineRadarConfig(Base):
    """yg_forklift_line_radar_config"""

    __tablename__ = "yg_forklift_line_radar_config"

    forklift_line_radar_config_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False)
    start_site_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="시작 스테이션 코드")
    start_site_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="시작 스테이션 이름")
    end_site_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="종료 스테이션 코드")
    end_site_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="종료 스테이션 이름")
    device_imei: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="지게차 IMEI")
    customer_id: Mapped[str | None] = mapped_column(String(4), nullable=True, comment="기업 ID")
    forklift_line_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="노선 ID")
    step_number: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="이동 단계 수")
    state: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="상태 0: 열림, 1: 닫힘")
    return_line_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="차체 복귀 주선 ID")
    message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="그룹 메시지 번호")
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ForkliftLineRadarSet(Base):
    """yg_forklift_line_radar_set"""

    __tablename__ = "yg_forklift_line_radar_set"

    forklift_line_radar_set_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False, comment="노선 레이더 파라미터 설정 ID")
    customer_id: Mapped[str | None] = mapped_column(String(4), nullable=True, comment="기업 ID")
    device_imei: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="장치 IMEI")
    forklift_line_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="노선 ID")
    return_line_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="차체 복귀 주선 ID")
    radar_up_w: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="상방 레이더 너비 800~3000")
    radar_up_l: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="상방 레이더 길이 100~5000")
    radar_back_w: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="후방 레이더 너비 800~3000")
    radar_back_l: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="후방 레이더 길이 100~5000")
    radar_down_w: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="하방 레이더 너비 800~3000")
    radar_down_l: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="하방 레이더 길이 100~5000")
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ForklineQuietModeConfig(Base):
    """yg_forkline_quiet_mode_config"""

    __tablename__ = "yg_forkline_quiet_mode_config"

    forkline_quiet_mode_config_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False, comment="노선 정숙 모드 설정 ID")
    customer_id: Mapped[str | None] = mapped_column(String(4), nullable=True, comment="기업 ID")
    device_imei: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="장치 IMEI")
    forklift_line_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="노선 ID")
    start_site_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="시작점 코드")
    end_site_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="종료점 코드")
    steps: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="이동 단계 수")
    state: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="상태 0: 닫힘, 1: 열림")
    quiet_mode_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="정숙 모드 번호")
    camera_interval: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="촬영 간격")
    group_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="그룹 ID (하나의 설정 그룹 식별)")
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class LineCompensation(Base):
    """yg_line_compensation"""

    __tablename__ = "yg_line_compensation"

    compensation_id: Mapped[str] = mapped_column(String(32), primary_key=True, nullable=False, comment="보정 ID")
    forklift_line_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="노선 ID")
    device_imei: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="차체 IMEI")
    start_site_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="시작점 코드")
    end_site_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="종료점 코드")
    start_site_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="시작점 이름")
    end_site_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="종료점 이름")
    compensation_x: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="X 보정값")
    compensation_y: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="Y 보정값")
    compensation_angle: Mapped[float | None] = mapped_column(Float, nullable=True, comment="각도 보정값")
    offset_x: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="노선 시작점 오프셋")
    offset_end_x: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="노선 종료점 오프셋")
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    updated_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    left_or_right_offset: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="좌우 오프셋")
    left_or_right_offset_end: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="종료점 좌우 오프셋")
    customer_id: Mapped[str | None] = mapped_column(String(4), nullable=True, comment="기업 ID")


class LineParameter(Base):
    """yg_line_parameter — 노선 파라미터 테이블"""

    __tablename__ = "yg_line_parameter"

    line_parameter_id: Mapped[str] = mapped_column(String(64), primary_key=True, nullable=False, comment="ID")
    forklift_line_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="노선 ID")
    speed: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="속도")
    steps: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="이동 단계 수")
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    device_imei: Mapped[int | None] = mapped_column(Integer, nullable=True)


class MapInfo(Base):
    """yg_map_info"""

    __tablename__ = "yg_map_info"

    map_info_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False, comment="지도 정보 기본키 ID")
    customer_id: Mapped[str | None] = mapped_column(String(4), nullable=True, comment="기업 ID")
    device_imei: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="장치 IMEI")
    forklift_line_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="노선 ID")
    return_line_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="주선 ID")
    site_x: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="X축 위치")
    site_y: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="Y축 위치")
    site_a: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="호도(라디안)")
    floor: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="소속 층")
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class NanoServerParam(Base):
    """yg_nano_server_param"""

    __tablename__ = "yg_nano_server_param"

    nano_server_param_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False, comment="Nano 서버 조회 파라미터 ID")
    url: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Nano 서버 주소")
    getcar_info: Mapped[int | None] = mapped_column(Integer, nullable=True)
    device_imei: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="조회할 IMEI")
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class OpencvTb(Base):
    """yg_opencv_tb"""

    __tablename__ = "yg_opencv_tb"

    opencv_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False)
    low_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    high_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    feature_points_threshold: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="색상 차이 임계값 (colorDifferenceThreshold, 기본값 30)")
    feature_points_param: Mapped[float | None] = mapped_column(Float, nullable=True, comment="coefficient_A 대체값")
    orb1_param1: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="모드 (mode, 기본값 2)")
    orb2_param1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    nfeatures: Mapped[int | None] = mapped_column(Integer, nullable=True)


class PathConfig(Base):
    """yg_path_config"""

    __tablename__ = "yg_path_config"

    path_config_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False)
    customer_id: Mapped[str | None] = mapped_column(String(4), nullable=True)
    storage_turn_around: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="1: 보관위치에서 유턴 불가")
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Site(Base):
    """yg_site — 스테이션 관리 테이블"""

    __tablename__ = "yg_site"

    site_id: Mapped[str] = mapped_column(String(64), primary_key=True, nullable=False, comment="기본키 ID")
    device_imei: Mapped[int | None] = mapped_column(Integer, nullable=True)
    site_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="스테이션 번호")
    site_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="이름")
    site_type: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="스테이션 유형: 1: 작업장, 2: 구역, 3: 스테이션")
    site_attr: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="스테이션 속성: 1: 정박점(하역점), 2: 대기점(P), 3: 충전점, 4: 일반점, 5: 개방루프점, 6: 계단제어점, 7: 엘리베이터점\r\n8: 대기점, 9: 보관위치, 10: 통로문, 11: 보관위치 열, 12: 실외점")
    parent_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="상위 ID")
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="생성자")
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="생성 시간")
    updated_by: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="수정자")
    updated_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="수정 시간")
    site_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    site_y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    site_flag: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="초기화 가능 여부: 0: 불가, 1: 가능")
    customer_id: Mapped[str | None] = mapped_column(String(4), nullable=True, comment="기업 ID")
    area_id: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="구역 ID")


class SiteArea(Base):
    """yg_site_area"""

    __tablename__ = "yg_site_area"

    site_area_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False)
    site_area_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="생성자")
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="생성 시간")
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="수정자")
    updated_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="수정 시간")
    customer_id: Mapped[str | None] = mapped_column(String(4), nullable=True, comment="기업 ID")
    task_template_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="작업 템플릿 ID")


class SiteCol(Base):
    """yg_site_col — 스테이션 열"""

    __tablename__ = "yg_site_col"

    site_col_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False, comment="기본키 ID")
    clo_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="열 이름")
    status: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="열 상태: 0: 대기, 1: 점유")
    sku_code: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="SKU 번호")
    site_area_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="구역 ID")
    device_imei: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="장치 번호")
    task_template_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="작업 템플릿 ID")
    agv_task_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="작업 ID")
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="생성자")
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="생성 시간")
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="수정자")
    updated_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="수정 시간")
    order_no: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="정렬")
    customer_id: Mapped[str | None] = mapped_column(String(4), nullable=True, comment="기업 ID")


class SiteColInfo(Base):
    """yg_site_col_info"""

    __tablename__ = "yg_site_col_info"

    site_area_info_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False, comment="구역 상세 ID")
    site_area_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="구역 ID")
    site_col_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="스테이션 목록 ID")
    site_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="스테이션 코드")
    order_no: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="정렬")
    task_temp_type: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="작업 템플릿 유형: 1: 이동식 창고, 2: 풀 방식, 3: 푸시 방식")
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="생성자")
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="생성 시간")
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="수정자")
    updated_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="수정 시간")
    customer_id: Mapped[str | None] = mapped_column(String(4), nullable=True, comment="기업 ID")
    site_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="스테이션 이름")
    task_template_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="작업 템플릿 ID")


class SiteInitPoint(Base):
    """yg_site_init_point"""

    __tablename__ = "yg_site_init_point"

    site_init_point_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False, comment="기본키")
    customer_id: Mapped[str | None] = mapped_column(String(4), nullable=True, comment="기업 ID")
    device_imei: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="imei")
    site_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="스테이션 코드")
    site_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="스테이션 이름")
    site_role: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="스테이션 역할: 1 초기화점, 2 구역 하역 후 복귀점, 3 포장점, 4 주차점")
    is_stop: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="정차 여부: 0 정차 안 함, 1 정차")
    fork_action: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="포크 동작: 0 정지, 2 자동 하역")
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SiteManage(Base):
    """yg_site_manage — 스테이션 관리 테이블"""

    __tablename__ = "yg_site_manage"

    manage_id: Mapped[str] = mapped_column(String(64), primary_key=True, nullable=False, comment="기본키")
    site_manage_id: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="실제 스테이션")
    site_manage_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="이름")
    site_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="외래키 ID")
    device_imei: Mapped[int | None] = mapped_column(Integer, nullable=True)
    site_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="스테이션 번호")
    site_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="이름")
    site_type: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="스테이션 유형: 1: 작업장, 2: 구역, 3: 스테이션")
    site_attr: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="스테이션 속성: 1: 정박점(하역점), 2: 대기점(P), 3: 충전점, 4: 일반점, 5: 개방루프점, 6: 계단제어점, 7: 엘리베이터점\r\n8: 대기점, 9: 보관위치, 10: 통로문, 11: 보관위치 열, 12: 실외점")
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="생성자")
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="생성 시간")
    updated_by: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="수정자")
    updated_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="수정 시간")
    site_x: Mapped[int | None] = mapped_column(Integer, nullable=True)
    site_y: Mapped[int | None] = mapped_column(Integer, nullable=True)
    site_flag: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="초기화 가능 여부: 0: 불가, 1: 가능")
    customer_id: Mapped[str | None] = mapped_column(String(4), nullable=True, comment="기업 ID")
    area_id: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="구역 ID")
    site_floor: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="소속 층")


class Storage(Base):
    """yg_storage — 보관위치 테이블"""

    __tablename__ = "yg_storage"

    storage_id: Mapped[str] = mapped_column(String(64), primary_key=True, nullable=False, comment="기본키")
    storage_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="보관위치 이름")
    storage_hight: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="보관위치 높이")
    site_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="스테이션 이름")
    site_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="스테이션 코드")
    site_status: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="보관위치 상태: 0: 비어있음, 1: 화물 있음, 2: 출고 중, 3: 입고 중")
    site_type: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="보관위치 유형: 1 보관위치, 2 보관위치 열")
    customer_id: Mapped[str | None] = mapped_column(String(4), nullable=True)
    area_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    area_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="생성자")
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="생성 시간")
    updated_by: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="수정자")
    updated_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="수정 시간")
    is_enable: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="활성화 여부: 0 활성, 1 비활성")
    sku_code: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="물자 번호(SKU)")


class StorageDeviceRelation(Base):
    """yg_storage_device_relation"""

    __tablename__ = "yg_storage_device_relation"

    storage_device_relation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False, comment="보관위치 장치 바인딩 테이블")
    device_imei: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="imei")
    device_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="장치 이름")
    type: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="장치 유형: 1 AGV, 2 카메라, 3 호출박스, 4 스캐너")
    site_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="스테이션 코드")
    site_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="스테이션 이름")
    site_type: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="보관위치 유형: 1 보관위치, 2 보관위치 열")
    order_no: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="정렬")
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TaskTempDevice(Base):
    """yg_task_temp_device"""

    __tablename__ = "yg_task_temp_device"

    task_temp_device_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False)
    device_imei: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priority: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="우선순위, 1부터 시작하며 클수록 우선순위 높음")
    task_template_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TaskTempSite(Base):
    """yg_task_temp_site"""

    __tablename__ = "yg_task_temp_site"

    task_temp_site_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False, comment="기본키")
    site_type: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="유형: 1: 시작점, 2: 종료점")
    site_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    site_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(13), nullable=True)
    task_template_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    customer_id: Mapped[str | None] = mapped_column(String(4), nullable=True)
    order_index: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="정렬")
    sku_code: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="물자 번호(SKU)")
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    updated_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TaskTempSpareSite(Base):
    """yg_task_temp_spare_site"""

    __tablename__ = "yg_task_temp_spare_site"

    task_temp_spare_site_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False, comment="예비 스테이션 ID")
    task_template_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="작업 템플릿 ID")
    site_type: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="유형: 1: 시작점, 2: 종료점")
    main_site_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="상위 스테이션")
    main_site_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="상위 스테이션 이름")
    site_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="예비 스테이션")
    site_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="예비 스테이션 이름")
    order_index: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="정렬")
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class TaskTemplate(Base):
    """yg_task_template — 작업 템플릿 시작/종료점 정보"""

    __tablename__ = "yg_task_template"

    task_template_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False, comment="작업 템플릿 ID")
    template_name: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="작업 템플릿 이름")
    task_temp_type: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="작업 템플릿 유형: 1: 이동식 창고, 2: 풀 방식, 3: 푸시 방식")
    resource_id: Mapped[str | None] = mapped_column(String(13), nullable=True, comment="리소스 ID: x-x-xxxx-xxxx, 국가1자리-제조사1자리-대리점4자리-회사4자리")
    customer_id: Mapped[str | None] = mapped_column(String(4), nullable=True, comment="기업 ID")
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="생성자")
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="생성 시간")
    updated_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="수정자")
    updated_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="수정 시간")
    run_status: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="실행 상태: 0: 활성, 1: 비활성")


class UserTask(Base):
    """yg_user_task — 작업 큐 테이블"""

    __tablename__ = "yg_user_task"

    user_task_id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, comment="작업 ID")
    device_imei: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="장치 IMEI 번호")
    send_flag: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="전송 플래그: 1: 신규 생성, 2: 실행 중, 3: 완료, 4: 실행 실패, 5: 전송됨, 6: 전송 실패, 7: 취소됨")
    fun_code: Mapped[str | None] = mapped_column(String(10), nullable=True, comment="기능 코드")
    start_site_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="사용자 선택 시작점 ID")
    end_site_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="사용자 선택 종료점 ID")
    start_storage_height: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="시작점 보관위치 높이")
    end_storage_height: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="종료점 보관위치 높이")
    real_start_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="작업 시작점")
    start_handel: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="시작점 동작")
    end_handel: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="종료점 동작")
    real_end_code: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="작업 종료점")
    is_loop: Mapped[str | None] = mapped_column(String(1), nullable=True, comment="0: 비순환, 1: 순환")
    created_by: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="생성자")
    created_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="작업 생성 시간")
    executed_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="작업 실행 시간")
    finished_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="작업 종료 시간")
    updated_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    task_type: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="작업 유형: 1: 지정 차량, 2: 미지정 차량, 3: 다중 차량 지정, 4: 장치 호출")
    lift_height: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="리프트 높이")
    task_group_id: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="작업 그룹 ID")
    start_site_name: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="시작 스테이션 이름")
    end_site_name: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="종료 스테이션 이름")
    task_group_name: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="작업 그룹 이름")
    customer_id: Mapped[str | None] = mapped_column(String(4), nullable=True, comment="기업 ID")
    message_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="상위 작업 메시지 ID")
    pick_place_state: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="화물 취급 상태: 0: 무동작, 1: 취화 완료, 2: 방화 완료")
    task_is_cancel: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="작업 상태: 0: 취소 불가, 1: 취소 가능")
    task_template_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="작업 템플릿 ID")
    device_type: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="장치 유형: 0: 수동 작업, 1 AGV, 2 카메라, 3 호출박스, 4 스캐너")
    created_imei: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="작업 생성 장치 IMEI")
    way_points: Mapped[str | None] = mapped_column(Text, nullable=True, comment="경유점")
    call_type: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="스캔 차량 호출 유형: 0 임의 위치 실행 가능, 1 대기점 실행")
    execute_type: Mapped[str | None] = mapped_column(String(2), nullable=True, comment="실행 유형: 0 대기 중 실행 가능, 1 근거리 차량 호출")
    task_priority: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="작업 우선순위 0-10, 숫자 클수록 높음")


class UserTaskPro(Base):
    """yg_user_task_pro — 선행 작업"""

    __tablename__ = "yg_user_task_pro"

    user_task_pro_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, nullable=False)
    device_imei: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_task_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
