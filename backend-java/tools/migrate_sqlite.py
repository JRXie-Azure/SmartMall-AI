#!/usr/bin/env python3
"""
SQLite -> MySQL / H2 数据搬运脚本。

设计取舍：
  * 只搬数据，不建表。表结构由 Flyway 的 V1__init_schema.sql 负责，
    避免"脚本建的表"和"Flyway 建的表"两份真相。
  * 原样保留主键 ID —— 订单号、外键、前端书签都依赖它，重新编号会炸。
  * 输出纯 SQL 文件而不是直连数据库：零第三方依赖（不需要 pymysql / JayDeBeApi），
    H2 用官方 RunScript 工具灌，MySQL 用 mysql 客户端灌，两边都不用改脚本。

用法：
    python migrate_sqlite.py                      # 两种方言各出一份
    python migrate_sqlite.py --dialect mysql      # 只出 MySQL
    python migrate_sqlite.py --src ../../backend/smartmall.db --out ./dist

灌库：
    H2:    java -cp h2-*.jar org.h2.tools.RunScript \
               -url "jdbc:h2:file:./data/smartmall;MODE=MySQL" -user sa \
               -script data_h2.sql -showResults
    MySQL: mysql -u root -p smartmall < data_mysql.sql
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import sqlite3
import sys

# 迁移顺序 = 外键依赖顺序。虽然脚本里会关掉外键检查，
# 但按依赖序插入能让失败时的报错更好读。
TABLES = [
    "users",
    "categories",
    "addresses",
    "products",
    "cart_items",
    "orders",
    "order_items",
    "reviews",
    "product_views",
    "favorites",
    "chat_sessions",
    "chat_messages",
    "search_histories",
]

# Alembic 的版本表由 Flyway 接管，不搬
SKIP_TABLES = {"alembic_version", "flyway_schema_history"}

# 各方言下需要转义的标识符（metadata 是 MySQL 保留字）
RESERVED = {"metadata", "status", "order", "key", "rank", "groups"}

DATETIME_COLUMNS_HINT = re.compile(r"(_at|_time)$")

BATCH_SIZE = 200


def quote_ident(name: str, dialect: str) -> str:
    if dialect == "mysql":
        return f"`{name}`"
    # H2 在 MODE=MySQL 下同样接受反引号，统一用反引号少一套分支
    return f"`{name}`"


def quote_table(name: str, dialect: str) -> str:
    return quote_ident(name, dialect)


def escape_string(value: str, dialect: str) -> str:
    """
    转义规则差异（这块搞错会静默写坏数据，不会报错）：
      * MySQL 默认把反斜杠当转义符，必须翻倍；
      * H2 按 SQL 标准，反斜杠是普通字符，翻倍反而会多出一个。
    products.tags / images 存的是 json.dumps 出来的 ASCII 转义串（\\u8dd1\\u6b65），
    正好踩这个坑，所以两种方言必须分开处理。
    """
    if dialect == "mysql":
        s = value.replace("\\", "\\\\").replace("'", "''")
    else:
        s = value.replace("'", "''")
    return f"'{s}'"


def normalize_datetime(raw: str) -> str:
    """SQLite 的时间是字符串，统一成 'YYYY-MM-DD HH:MM:SS.ffffff'"""
    text = raw.strip().replace("T", " ")
    if text.endswith("Z"):
        text = text[:-1]
    # 去掉时区偏移，两套后端都按 Asia/Shanghai 处理裸时间
    text = re.sub(r"([+-]\d{2}:?\d{2})$", "", text).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(text, fmt).strftime("%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            continue
    return text  # 认不出来就原样交给数据库，让它报错而不是悄悄写错


def render_value(value, column: str, dialect: str) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return "NULL"
        return repr(value)
    if isinstance(value, (bytes, bytearray)):
        return "X'" + value.hex() + "'"
    text = str(value)
    if DATETIME_COLUMNS_HINT.search(column):
        text = normalize_datetime(text)
    return escape_string(text, dialect)


def table_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    return [r[1] for r in conn.execute(f'PRAGMA table_info("{table}")')]


def existing_tables(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {r[0] for r in rows}


def build_script(conn: sqlite3.Connection, dialect: str) -> tuple[str, dict[str, int]]:
    out: list[str] = []
    stats: dict[str, int] = {}

    out.append(f"-- SmartMall-AI 数据导入脚本 ({dialect})")
    out.append(f"-- 由 tools/migrate_sqlite.py 生成于 {dt.datetime.now():%Y-%m-%d %H:%M:%S}")
    out.append("-- 前置条件: Flyway V1__init_schema.sql 已执行，表已存在且为空")
    out.append("")

    if dialect == "mysql":
        out.append("SET NAMES utf8mb4;")
        out.append("SET FOREIGN_KEY_CHECKS = 0;")
        out.append("SET UNIQUE_CHECKS = 0;")
        # 关键: MySQL 默认反斜杠是转义符，脚本正是按这个规则生成的
        out.append("SET SESSION sql_mode = '';")
    else:
        out.append("SET REFERENTIAL_INTEGRITY FALSE;")
    out.append("")

    present = existing_tables(conn)

    for table in TABLES:
        if table in SKIP_TABLES:
            continue
        if table not in present:
            print(f"  [skip] {table}: 源库中不存在", file=sys.stderr)
            continue

        cols = table_columns(conn, table)
        rows = conn.execute(f'SELECT * FROM "{table}"').fetchall()
        stats[table] = len(rows)

        out.append(f"-- ===== {table} ({len(rows)} 行) =====")
        out.append(f"DELETE FROM {quote_table(table, dialect)};")
        if not rows:
            out.append("")
            continue

        col_list = ", ".join(quote_ident(c, dialect) for c in cols)
        for start in range(0, len(rows), BATCH_SIZE):
            chunk = rows[start:start + BATCH_SIZE]
            values = []
            for row in chunk:
                rendered = [render_value(row[i], cols[i], dialect) for i in range(len(cols))]
                values.append("(" + ", ".join(rendered) + ")")
            out.append(
                f"INSERT INTO {quote_table(table, dialect)} ({col_list}) VALUES\n"
                + ",\n".join(values)
                + ";"
            )
        out.append("")

    # 自增序列复位：不做的话新建记录会撞已有主键
    out.append("-- ===== 复位自增序列 =====")
    for table, count in stats.items():
        if count == 0:
            continue
        if "id" not in table_columns(conn, table):
            continue
        max_id = conn.execute(f'SELECT MAX(id) FROM "{table}"').fetchone()[0] or 0
        next_id = max_id + 1
        if dialect == "mysql":
            out.append(f"ALTER TABLE {quote_table(table, dialect)} AUTO_INCREMENT = {next_id};")
        else:
            out.append(
                f"ALTER TABLE {quote_table(table, dialect)} "
                f"ALTER COLUMN id RESTART WITH {next_id};"
            )
    out.append("")

    if dialect == "mysql":
        out.append("SET FOREIGN_KEY_CHECKS = 1;")
        out.append("SET UNIQUE_CHECKS = 1;")
    else:
        out.append("SET REFERENTIAL_INTEGRITY TRUE;")
    out.append("")

    return "\n".join(out), stats


def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    default_src = os.path.normpath(os.path.join(here, "..", "..", "backend", "smartmall.db"))

    parser = argparse.ArgumentParser(description="把 Python 版 SQLite 数据搬到 MySQL / H2")
    parser.add_argument("--src", default=default_src, help="SQLite 文件路径")
    parser.add_argument("--out", default=os.path.join(here, "dist"), help="输出目录")
    parser.add_argument("--dialect", choices=["mysql", "h2", "both"], default="both")
    args = parser.parse_args()

    if not os.path.isfile(args.src):
        print(f"[X] 源库不存在: {args.src}", file=sys.stderr)
        return 1

    os.makedirs(args.out, exist_ok=True)
    conn = sqlite3.connect(args.src)

    dialects = ["mysql", "h2"] if args.dialect == "both" else [args.dialect]
    total_stats: dict[str, int] = {}

    for dialect in dialects:
        script, stats = build_script(conn, dialect)
        path = os.path.join(args.out, f"data_{dialect}.sql")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(script)
        total_stats = stats
        size_kb = os.path.getsize(path) / 1024
        print(f"[OK] {path}  ({size_kb:.1f} KB)")

    conn.close()

    print("\n数据量统计:")
    total = 0
    for table, count in total_stats.items():
        print(f"  {table:<20} {count:>6}")
        total += count
    print(f"  {'合计':<18} {total:>6}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
