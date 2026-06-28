"""schema.sql(MySQL DDL)을 파싱하여 SQLAlchemy 2.0 모델을 생성한다.

- DB에 접속하지 않고 오직 schema.sql 텍스트만 읽는다.
- 컬럼 주석(중국어)은 모델에 comment 인자 + 한글 설명 주석으로 보존한다.
사용: python scripts/gen_models.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT.parent / "schema.sql"
OUT = ROOT / "app" / "models" / "tables.py"


def snake_to_camel(name: str) -> str:
    """yg_user_task -> UserTask (yg_ 접두어 제거 후 CamelCase)."""
    n = name
    if n.startswith("yg_"):
        n = n[3:]
    parts = re.split(r"[_]+", n)
    return "".join(p[:1].upper() + p[1:] for p in parts if p) or "Table"


def map_type(coltype: str):
    """MySQL 타입 문자열 -> (SQLAlchemy 타입식, 파이썬 타입힌트)."""
    t = coltype.strip().lower()
    base = re.match(r"([a-z]+)", t).group(1)
    # 길이/정밀도 추출
    m = re.search(r"\(([\d,\s]+)\)", t)
    args = m.group(1) if m else None

    if base in ("varchar", "char"):
        n = args.split(",")[0].strip() if args else "255"
        return f"String({n})", "str"
    if base in ("text", "tinytext", "mediumtext", "longtext"):
        return "Text", "str"
    if base in ("int", "integer", "mediumint", "smallint", "tinyint"):
        return "Integer", "int"
    if base == "bigint":
        return "BigInteger", "int"
    if base in ("float", "double", "real"):
        return "Float", "float"
    if base in ("decimal", "numeric"):
        if args:
            p, s = (x.strip() for x in (args.split(",") + ["0"])[:2])
            return f"Numeric({p}, {s})", "Decimal"
        return "Numeric", "Decimal"
    if base == "datetime" or base == "timestamp":
        return "DateTime", "datetime"
    if base == "date":
        return "Date", "date"
    if base == "time":
        return "Time", "time"
    if base in ("blob", "longblob", "mediumblob", "tinyblob", "binary", "varbinary"):
        return "LargeBinary", "bytes"
    # 알 수 없으면 문자열로
    return "String(255)", "str"


def parse_tables(sql: str):
    tables = []
    # CREATE TABLE `name` ( ... ) ENGINE=... ;
    pattern = re.compile(
        r"CREATE TABLE\s+`(?P<name>[^`]+)`\s*\((?P<body>.*?)\)\s*ENGINE=(?P<opts>[^;]*);",
        re.DOTALL | re.IGNORECASE,
    )
    for mt in pattern.finditer(sql):
        name = mt.group("name")
        body = mt.group("body")
        opts = mt.group("opts")
        tbl_comment = ""
        cm = re.search(r"COMMENT='([^']*)'", opts)
        if cm:
            tbl_comment = cm.group(1)

        columns = []
        pk = []
        for raw in body.split("\n"):
            line = raw.strip().rstrip(",")
            if not line:
                continue
            # PRIMARY KEY
            pkm = re.match(r"PRIMARY KEY\s*\(([^)]*)\)", line, re.IGNORECASE)
            if pkm:
                pk = [c.strip().strip("`") for c in pkm.group(1).split(",")]
                continue
            # KEY / UNIQUE KEY / CONSTRAINT 등은 건너뜀(모델 단순화)
            if re.match(r"(UNIQUE\s+KEY|KEY|CONSTRAINT|INDEX|FULLTEXT)", line, re.IGNORECASE):
                continue
            # 컬럼 정의: `col` type ...
            colm = re.match(r"`(?P<col>[^`]+)`\s+(?P<type>[A-Za-z]+(?:\([\d,\s]+\))?(?:\s+unsigned)?(?:\s+zerofill)?)\s*(?P<rest>.*)$", line)
            if not colm:
                continue
            col = colm.group("col")
            ctype = colm.group("type")
            rest = colm.group("rest")
            nullable = "NOT NULL" not in rest.upper()
            comment = ""
            ccm = re.search(r"COMMENT\s+'((?:[^'\\]|\\.)*)'", rest)
            if ccm:
                comment = ccm.group(1).replace("\\'", "'")
            columns.append({
                "col": col,
                "type": ctype,
                "nullable": nullable,
                "comment": comment,
            })
        tables.append({
            "name": name,
            "class": snake_to_camel(name),
            "comment": tbl_comment,
            "columns": columns,
            "pk": pk,
        })
    return tables


def attr_name(col: str) -> str:
    """컬럼명을 파이썬 속성명으로(소문자 유지, camelCase 컬럼은 그대로)."""
    return col.lower()


def render(tables):
    L = []
    L.append('"""schema.sql에서 자동 생성된 SQLAlchemy 2.0 모델.')
    L.append("")
    L.append("생성기: scripts/gen_models.py  (DB 미접속, schema.sql만 파싱)")
    L.append("원본 MySQL 컬럼 주석은 comment= 및 줄끝 주석으로 보존했다.")
    L.append("수기 수정 시 재생성으로 덮어쓰일 수 있으니 주의.")
    L.append('"""')
    L.append("from __future__ import annotations")
    L.append("")
    L.append("from datetime import date, datetime, time")
    L.append("from decimal import Decimal")
    L.append("")
    L.append("from sqlalchemy import (")
    L.append("    BigInteger, Date, DateTime, Float, Integer, LargeBinary,")
    L.append("    Numeric, String, Text, Time,")
    L.append(")")
    L.append("from sqlalchemy.orm import Mapped, mapped_column")
    L.append("")
    L.append("from app.core.database import Base")
    L.append("")
    L.append("")
    for t in tables:
        pkset = set(t["pk"])
        L.append(f"class {t['class']}(Base):")
        doc = f'"""{t["name"]}' + (f" — {t['comment']}" if t["comment"] else "") + '"""'
        L.append(f"    {doc}")
        L.append("")
        L.append(f'    __tablename__ = "{t["name"]}"')
        L.append("")
        for c in t["columns"]:
            sa_type, py_type = map_type(c["type"])
            attr = attr_name(c["col"])
            is_pk = c["col"] in pkset
            nullable = c["nullable"] and not is_pk
            opt_type = f"Mapped[{py_type}{' | None' if nullable else ''}]"
            kw = []
            if attr != c["col"]:
                kw.append(f'"{c["col"]}"')
            kw.append(sa_type)
            if is_pk:
                kw.append("primary_key=True")
            kw.append(f"nullable={nullable}")
            if c["comment"]:
                safe = c["comment"].replace('"', '\\"')
                kw.append(f'comment="{safe}"')
            line = f"    {attr}: {opt_type} = mapped_column({', '.join(kw)})"
            L.append(line)
        L.append("")
        L.append("")
    return "\n".join(L)


def main():
    if not SCHEMA.exists():
        print(f"schema.sql 없음: {SCHEMA}", file=sys.stderr)
        sys.exit(1)
    sql = SCHEMA.read_text(encoding="utf-8")
    tables = parse_tables(sql)
    OUT.write_text(render(tables), encoding="utf-8")
    print(f"생성 완료: {OUT}")
    print(f"테이블 {len(tables)}개:")
    for t in tables:
        print(f"  - {t['name']:<38} -> {t['class']:<24} ({len(t['columns'])} cols, pk={t['pk']})")


if __name__ == "__main__":
    main()
