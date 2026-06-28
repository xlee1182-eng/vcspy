"""전체 테스트 러너.

tests/test_*.py 를 모두 실행하고 결과를 집계한다.
운영 인프라(MySQL/Redis)에 접속하지 않는다 — 인메모리 SQLite + fakeredis + loopback.
사용: python run_tests.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TESTS = sorted((ROOT / "tests").glob("test_*.py"))

total = 0
failed = 0
env = {"PYTHONPATH": str(ROOT), "PYTHONUTF8": "1"}

import os

run_env = {**os.environ, **env}
for t in TESTS:
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", str(t)],
        capture_output=True, text=True, env=run_env, encoding="utf-8",
    )
    line = ""
    for ln in proc.stdout.splitlines():
        if "passed" in ln:
            line = ln.strip()
    passed = int(line.split()[1]) if line else 0
    fail = int(line.split()[3]) if line and len(line.split()) > 3 else 0
    if proc.returncode != 0 and fail == 0:
        fail = 1  # 크래시
    total += passed
    failed += fail
    status = "OK " if proc.returncode == 0 else "FAIL"
    print(f"  [{status}] {t.name:<34} {line or proc.stderr.strip().splitlines()[-1:]}")

print(f"\n=== 파일 {len(TESTS)}개 / 통과 {total} / 실패 {failed} ===")
sys.exit(1 if failed else 0)
