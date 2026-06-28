# 실행 가이드 (venv)

Windows 11 / PowerShell / Python 3.14 기준. 프로젝트 위치: `D:\Projects\vcsPython\ygvcs_py`

---

## 1. 가상환경(venv) 생성 — 최초 1회

```powershell
cd D:\Projects\vcsPython\ygvcs_py
python -m venv .venv
```

## 2. venv 활성화

```powershell
.\.venv\Scripts\Activate.ps1
```
- 활성화되면 프롬프트 앞에 `(.venv)` 가 붙습니다.
- 만약 "이 시스템에서 스크립트 실행이 사용하지 않도록 설정" 오류가 나면(실행 정책):
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
  ```
  그 후 다시 `.\.venv\Scripts\Activate.ps1`
- 활성화 없이 직접 실행하려면 `python` 대신 `.\.venv\Scripts\python.exe` 를 쓰면 됩니다.

## 3. 패키지 설치 — 최초 1회

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```
> 참고: 비동기 MySQL 드라이버는 **aiomysql**(순수 파이썬)을 사용합니다. (C 빌드가 필요한 asyncmy 는 Windows/py3.14 에서 빌드 이슈가 있어 제외했습니다.)

## 4. 환경설정(.env) 준비

```powershell
Copy-Item .env.example .env
notepad .env   # DB 비밀번호 등 실제 값 입력
```
- 모든 설정은 `YGVCS_` 접두어 환경변수입니다. `.env` 미작성 시 `app/core/config.py` 기본값을 씁니다.

## 5. 실행

### (A) 테스트만 실행 — 운영 인프라(MySQL/Redis) 불필요
인메모리 SQLite + fakeredis + loopback 으로만 동작합니다.
```powershell
$env:PYTHONPATH = "."
python run_tests.py
# → 파일 20개 / 통과 217 / 실패 0
```

### (B) 앱 서버 실행 — 운영 MySQL/Redis 필요
```powershell
# TCP 서버/스케줄러 없이 웹 API만 먼저 띄워 확인하려면:
$env:YGVCS_PRIMARY_SERVER_ENABLED = "false"
$env:YGVCS_SCHEDULER_ENABLED = "false"

uvicorn app.main:app --host 0.0.0.0 --port 8188
```
- Swagger UI: **http://localhost:8188/ygvcs/docs**
- 헬스체크: **http://localhost:8188/ygvcs/health**
- 차량 TCP 서버까지 함께 기동하려면 위 두 환경변수를 `true`(기본값)로 두세요.
  (단, 실제 MySQL/Redis 연결이 되어야 정상 동작합니다.)

### (C) 개발 모드(코드 변경 자동 반영)
```powershell
uvicorn app.main:app --reload --port 8188
```

## 6. venv 비활성화
```powershell
deactivate
```

---

## 자주 겪는 문제

| 증상 | 해결 |
|---|---|
| `Activate.ps1` 실행 정책 오류 | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `ModuleNotFoundError: app` | 프로젝트 루트에서 실행 + `$env:PYTHONPATH = "."` |
| 한글/중국어 콘솔 깨짐 | `$env:PYTHONUTF8 = "1"` 설정 후 실행 |
| DB 접속 실패 | `.env` 의 `YGVCS_DB_*` 값과 MySQL 기동 여부 확인 |
| Redis 접속 실패 | `.env` 의 `YGVCS_REDIS_*` 확인. 웹 API만 볼 땐 TCP서버/스케줄러 끄기 |

## 한 줄 요약 (활성화 후)
```powershell
pip install -r requirements.txt          # 최초 1회
Copy-Item .env.example .env              # 최초 1회, 값 수정
python run_tests.py                      # 테스트(인프라 불필요)
uvicorn app.main:app --port 8188         # 서버 기동(MySQL/Redis 필요)
```
