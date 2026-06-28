# yg-vcs (Python 이식)

원본 Java(Spring Boot 2.3.5) **AGV/지게차 창고 관제 시스템**의 Python 이식 프로젝트.
원본 분석은 상위 폴더 `../분석보고서.md`, 디컴파일 소스는 `../decompiled/`, 실제 DB 스키마는 `../schema.sql` 참조.

## 기술 스택
| 영역 | 채택 | 원본 |
|---|---|---|
| 웹 | FastAPI + Uvicorn | Spring Boot Web |
| ORM | SQLAlchemy 2.0 (async) | MyBatis + Druid |
| DB | MySQL `yg_vcs_cloud` (스키마 변경 없음) | 동일 |
| 캐시 | redis-py | Lettuce |
| TCP | asyncio | Netty 4.1 |
| 비전 | opencv-python (+PyAV) | OpenCV/JavaCV |
| 스케줄 | APScheduler | ScheduledPool |

## 구조
```
app/
├─ core/
│  ├─ config.py      설정 (원본 application.yml 이식)
│  ├─ database.py    SQLAlchemy async 엔진/세션 (지연 초기화)
│  └─ constants.py   도메인 코드값 Enum (send_flag 등, DDL 주석 근거)
├─ models/tables.py  ORM 모델 33개 (schema.sql 자동 생성)
├─ schemas/          Pydantic (원본 dto/form) — 예정
├─ repositories/     쿼리 계층 (원본 mapper) — 예정
├─ services/         비즈니스 로직 (원본 service) — 예정
├─ routers/          REST API (원본 controller/webservice) — 예정
├─ tcp/              차량/카메라/콜박스 TCP 서버 (원본 *NettyServer) — 예정
├─ ws/               WebSocket (원본 wsServer) — 예정
├─ vision/           영상 처리 (원본 camServer) — 예정
├─ jobs/             스케줄러 (원본 job) — 예정
└─ main.py           앱 진입점 (원본 YgVcsApplication)
scripts/gen_models.py  schema.sql -> 모델 생성기 (DB 미접속)
```

## ⚠️ 원칙
- **DB 스키마를 변경하지 않는다.** 테이블 생성/삭제/수정(DDL) 금지, `create_all` 호출 금지.
  기존 운영 테이블을 읽고 쓰기만 한다.

## 진행 현황
- [x] 프로젝트 골격
- [x] 설정/DB/상수 코어
- [x] ORM 모델 33개 자동 생성 (428개 컬럼, 검증 완료)
- [x] FastAPI 앱 기동 (`/health`)
- [x] 공통 인프라: `JsonResult`(응답 래퍼), `messages`(i18n), `BaseRepository`(query-by-example)
- [x] **User 도메인** (원본 UserWarpWebService/UserServiceImpl 이식, 테스트 7/7 통과)
  - `POST /service/warp/user/userLogin`, `POST /service/warp/user/editPassword`
- [x] **프로토콜 토대** (TCP 통신 전반의 핵심):
  - `app/tcp/constants.py` (TcpConstants: FRAME/FUN_CODES/MODEL)
  - `app/tcp/crc.py` (CRC-16/CCITT-FALSE — 표준벡터 0x29B1 검증)
  - `app/tcp/byte_process.py` (hex/int/byte 변환, 프레임 생성·CRC 검증, 테스트 14/14 통과)
  - `app/core/redis_constants.py`, `app/utils/redis_util.py`, `app/utils/json_util.py`
- [x] **Device 도메인** (CRUD 완전 이식, 테스트 13/13 통과)
  - `getDeviceInfo`, `addDevice`, `editDevice`, `delDevice`, `getAgvHeartList`
  - initLocation/terminateTask 는 라이브 TCP 의존 → TCP 서버 milestone에서 완성(스텁)
- [x] **Site/Storage 도메인** (CRUD/조회/바인딩 이식, 테스트 14/14)
  - site: `getSiteInfo`, `getSiteByDevice`, `editStorage`
  - storageDevice: `editStorageDevice`, `delStorageDevice`
  - 작업생성 의존(editStorageStatus/editAreaStatus/editScanStorageStatus)은 Task 이후 완성(스텁)
  - 부수 이식: Snowflake ID 생성기(`utils/id_utils.py`)
- [x] **Task 템플릿 도메인** (TaskService 완전 이식, 테스트 15/15)
  - `addTaskTemp/editTaskTemp/editTaskTempInfo/delTaskTemp/clearTaskTemp/selectTaskTempList/selectTaskTempInfo`
  - 실행상태 전환 시 사이트 충돌 검사(selectRunTaskTempBySite) 포함
  - UserTask 실작업(addTask/sendTask/callDeviceTask 등)은 TCP 송신 의존 → TCP 서버 이후
- [x] **ForkliftLine 도메인** (이식 완료, 테스트 6/6)
  - `getAllForkliftLine`(Redis), addForkLineList(일괄), getLineToInit/2(회차라인 SQL)
- [x] **차량(AGV) TCP 서버 — Netty→asyncio 이식** (테스트 12/12)
  - `tcp/frame_codec.py`(델리미터 50AFA05FA0 프레임 분리)
  - `tcp/future_manager.py`(imei+fun+msgNo 요청/응답 상관, 10s 타임아웃)
  - `tcp/channel_manager.py`(imei→연결, sendMsg/sendMsgSync/receiveMsg)
  - `tcp/primary_server.py`(asyncio 서버, 읽기루프+중복방지), `tcp/tcp_client.py`(sendTcpMsg)
  - FastAPI lifespan 에서 서버 기동, loopback 통합 검증
- [x] **Device.initLocation / terminateTask 완성** (TCP 연결, 테스트 6/6)
  - `/service/web/device/initLocation`, `/terminateTask`, `services/send_task.py`(terminnateTask)
- [x] **UserTask 조회/취소/초기화** (DB 기반, 테스트 12/12)
  - `/service/web/userTask/`: getTaskResult, getPickPlaceState, cancelTask, clearTask
  - getTaskInfo: Redis(task_state) 캐시 우선 → DB 조회 → 10초 캐시
  - cancelTask: 해당 장비의 미실행(send_flag=1)만 취소(7)로
- [x] **TaskOpService.createTask** (작업 생성 상태머신, 테스트 12/12)
  - 사이트 진행중 검사 → 템플릿/보관위치 매칭 → UserTask(send_flag=1) 생성 → 보관위치 상태 2/3 갱신
  - 시퀀스 채번(nextval 에뮬), findSiteTask/findStorage 커스텀 SQL
- [x] **Storage 상태변경 연결** (editStorageStatus/editScanStorageStatus, 테스트 +3)
  - `/service/warp/site/editStorageStatus`, `/editScanStorageStatus`
- [x] **UserTask 송신부 sendTask/addTask** (프레임 구성→TCP 송신→응답파싱, 테스트 15/15)
  - `SendTask` 프레임 빌더(appendTaskMsg B2 / startTaskCmd / taskLock / wayPoints)
  - `response_parser.is_0xff_or_0x00`(FF=성공, 27개 FLAG 배열 자동추출)
  - `/service/web/userTask/sendTask`: 장비상태검증→폼검증→UserTask구성→2프레임 송신→send_flag=2
- [x] **작업 제어 명령 setKeyboardLock/setTask/sendRepeatTask** (테스트 9/9)
  - setTask: 시작('1')/일시정지('2')/종료('3') — startOrPauseTask·terminnateTask·DB취소 분기
- [x] **TCP 서버 일반화 + cam/callBox/ws** (테스트 9/9)
  - `tcp/frame_server.py` 제네릭 서버로 일반화(primary/cam/callBox 재사용)
  - `ws/ws_server.py` 실시간 푸시 서버(WsChannelManager.send_msg: imei별/브로드캐스트)
  - 원본대로 cam/callBox/ws 는 기본 비활성(primary 만 자동기동), 설정으로 활성화 가능
- [x] **스케줄러 + 작업 픽업** (테스트 10/10)
  - `jobs/scheduler.py`(APScheduler) + `RecordHeartJob`(운영플래그 5초 갱신)
  - `editAndGetAnTask`: 하트비트 시 장비가 수행할 다음 작업 선택(지정→다중차→호출→미지정 우선순위)
- [x] **하트비트 프레임 파싱** (PrimaryMsgProcessor/saveOrUpdateDevice, 테스트 20/20)
  - 메모리테이블 바이트 오프셋 디코딩(flag/model/사이트/taskFlag/lockState/배터리 등)
  - Redis 저장(DEVICE_TASK_TABLE/deviceTable_suc/DEVICE_HEART_BEAT) → 소비처 연결
  - primary 서버 message_handler 로 연결(fun=00 자동 처리)
- [x] **자동 디스패치 연결 (무인 운영 루프 완성)** (테스트 11/11)
  - 유휴 하트비트 → editAndGetAnTask → (미잠금 시 taskLock) → 송신 → send_flag=2
  - serverIsReady 확인, should_dispatch 판정(taskFlag/forkStatus/flag/startSite)
- [x] **비전(카메라 점유) 처리** (테스트 8/8)
  - 이 빌드에 OpenCV 없음 — 카메라가 점유 비트를 TCP로 보고, 서버가 파싱·디바운스
  - `CameraTableService`: 점유비트 분해 → 슬롯별 디바운스(5회) → editScanStorageStatus
- [x] **callDeviceTask/sendPointsTask** (테스트 7/7)
  - callDeviceTask: 호출작업(taskType=4) 생성 + 중복검사 / sendPointsTask: 점대점 직접 송신
- [x] **전체 통합 점검** (TestClient HTTP, 테스트 9/9)
  - 앱 기동(health 200) / OpenAPI·Swagger(/docs 200) / 34개 엔드포인트
  - 실제 HTTP 요청 → 라우터 → 서비스 → DB 관통 검증(get_db→SQLite, redis→fakeredis)
- [ ] toPoint(대기점 복귀) — 잔여 부가 기능(소규모)

## 이식 현황 (정확본)
원본 yg-vcs 핵심·부가 기능 대부분 이식. **누적 테스트 217/217 통과 (20개 파일)**, 등록 API 35개.

### 미이식 엔드포인트 (점검 결과, 대부분 소규모 DB/Redis)
- **ProcessWarpWebService** `/service/warp/process`: importSqlInfo, clearAllData(데이터 초기화), isSyncTaskSource/get, toPointSwitch get/set, toPointTime get/set, getServerVersion — 대부분 단순 Redis 플래그 get/set
- **userTask warp** `/service/warp/userTask`: getUserTaskInfo, getCallDeviceTask, cancelCallDeviceTask, delUserTask, getCountTask — 소규모 DB 조회/삭제/통계
- **web/device** `/service/web/device`: getDeviceList, getDeviceInfo, setWifiRestartValue, setDeviceParams
- **web/siteManage** `/service/web/siteManage`: getAllSite, getSiteInfo
- camConfig/appLogfile: 원본에 엔드포인트 없음(빈 컨트롤러) — 이식 불필요
- 내부 CRUD 컨트롤러(UserController 등 /add /edit /delete /query): 원본이 빈 스텁 — 이식 불필요
- `toPoint`(작업 없을 때 대기점 복귀), 하트비트 상세 텔레메트리(레이더/엔코더/위치)

## 진행률 개요
원본 yg-vcs 252개 클래스 기준.
| 영역 | 상태 |
|---|---|
| 공통 인프라/프로토콜 토대 | ✅ |
| User / Device / Site·Storage / Task템플릿 / ForkliftLine | ✅ (CRUD) |
| **차량 TCP 서버 + 요청/응답 상관** | ✅ (테스트 12+6) |
| Device 라이브(initLocation/terminate) | ✅ |
| UserTask 조회/취소/초기화 | ✅ (테스트 12) |
| TaskOpService.createTask + Storage 상태변경 | ✅ (테스트 12 + 3) |
| UserTask 송신 sendTask/addTask (프레임+응답파싱) | ✅ (테스트 15) |
| 작업제어 setKeyboardLock/setTask/sendRepeatTask | ✅ (테스트 9) |
| TCP 서버 일반화 + cam/callBox/ws | ✅ (테스트 9) |
| 스케줄러 + 작업픽업(editAndGetAnTask) | ✅ (테스트 10) |
| 하트비트 프레임 파싱(메모리테이블) | ✅ (테스트 20) |
| **자동 디스패치 (무인 운영 루프)** | ✅ (테스트 11) |
| 비전(카메라 점유) 처리 | ✅ (테스트 8) |
| callDeviceTask/sendPointsTask | ✅ (테스트 7) |

## 누적 테스트: 203 passed (+ taskwarp 7), 등록 API 34개

## 무인 운영 루프 (완성)
```
AGV 하트비트(fun=00) → 메모리테이블 파싱 → Redis 저장
                              ↓ (유휴 판정 시)
              editAndGetAnTask(작업 픽업) → SendTask(프레임 송신)
                              ↓                      ↓
                  send_flag='1'→'2'        요청/응답 상관(응답 FF=성공)
외부 API(sendTask/createTask) → 작업 생성(send_flag='1') ──┘
```

## 테스트
모든 테스트는 운영 DB/Redis 에 접속하지 않는다(인메모리 SQLite + fakeredis + loopback).
```bash
cd ygvcs_py
PYTHONPATH=. python run_tests.py          # 전체 실행 (212 tests)
PYTHONPATH=. python tests/test_user_service.py   # 개별 실행
```

## 실행
```bash
pip install -r requirements.txt
# .env 에 YGVCS_DB_PASSWORD 등 설정 후
uvicorn app.main:app --host 0.0.0.0 --port 8188
```

## 모델 재생성
```bash
python scripts/gen_models.py   # ../schema.sql 기준, DB 접속 안 함
```
