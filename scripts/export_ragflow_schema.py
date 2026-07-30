#!/usr/bin/env python3
"""
RAGFlow 数据库初始化 SQL 导出脚本
===================================
用途：从当前运行的 RAGFlow 实例导出完整的数据库 schema + 种子数据，
      生成可供 DBA 审核和在新服务器上执行的 SQL 文件。

用法：
  # 方式一：从 conf/service_conf.yaml 读取数据库连接信息
  PYTHONPATH=. python scripts/export_ragflow_schema.py

  # 方式二：选择导出范围
  PYTHONPATH=. python scripts/export_ragflow_schema.py --schema-only    # 仅表结构，不含种子数据
  PYTHONPATH=. python scripts/export_ragflow_schema.py --data-only      # 仅种子数据，不含表结构
  PYTHONPATH=. python scripts/export_ragflow_schema.py --output init.sql  # 指定输出文件

输出：
  ragflow_init.sql — 包含 CREATE DATABASE + 全部建表语句 + 种子数据 INSERT

前置条件：
  - conf/service_conf.yaml 已正确配置 MySQL 连接信息
  - 当前环境可连接到 RAGFlow 的 MySQL 数据库
"""

import argparse
import os
import sys
from datetime import datetime

# 确保项目根目录在 path 中
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from common import settings
from common.config_utils import decrypt_database_config

settings.init_settings()

# ============================================================
# 数据库连接
# ============================================================
import pymysql

DB_CONFIG = decrypt_database_config(name=settings.DATABASE_TYPE)

connection = pymysql.connect(
    host=DB_CONFIG["host"],
    port=int(DB_CONFIG.get("port", 3306)),
    user=DB_CONFIG["user"],
    password=DB_CONFIG["password"],
    database=DB_CONFIG["name"],
    charset="utf8mb4",
)


def get_all_tables(cursor) -> list[str]:
    """获取 rag_flow 数据库中所有表名（按依赖关系排序）。"""
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]
    # 按字母序排列，简单可靠（Peewee 建表时不涉及外键约束）
    tables.sort()
    return tables


def export_schema(cursor) -> str:
    """导出所有表的 CREATE TABLE 语句。"""
    tables = get_all_tables(cursor)
    lines = []
    lines.append("-- ============================================================")
    lines.append(f"-- RAGFlow 数据库初始化脚本")
    lines.append(f"-- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"-- 数据库名: {DB_CONFIG['name']}")
    lines.append(f"-- 表数量:   {len(tables)}")
    lines.append("-- ============================================================")
    lines.append("")
    lines.append(f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['name']}`")
    lines.append("  CHARACTER SET utf8mb4")
    lines.append("  COLLATE utf8mb4_unicode_ci;")
    lines.append("")
    lines.append(f"USE `{DB_CONFIG['name']}`;")
    lines.append("")

    for table in tables:
        cursor.execute(f"SHOW CREATE TABLE `{table}`")
        _, create_sql = cursor.fetchone()
        lines.append(f"-- ----------------------------")
        lines.append(f"-- 表: {table}")
        lines.append(f"-- ----------------------------")
        lines.append(f"DROP TABLE IF EXISTS `{table}`;")
        lines.append(create_sql + ";")
        lines.append("")

    return "\n".join(lines)


def export_seed_data(cursor) -> str:
    """导出种子数据（llm_factories, system_settings, canvas_template）。"""
    lines = []
    lines.append("")
    lines.append("-- ============================================================")
    lines.append("-- 种子数据（初始配置数据）")
    lines.append("-- ============================================================")
    lines.append("")

    # 需要导出种子数据的表
    seed_tables = [
        "llm_factories",
        "llm",
        "system_settings",
        "canvas_template",
    ]

    for table in seed_tables:
        # 检查表是否存在
        cursor.execute(f"SHOW TABLES LIKE '{table}'")
        if not cursor.fetchone():
            lines.append(f"-- 表 {table} 不存在，跳过")
            lines.append("")
            continue

        cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
        count = cursor.fetchone()[0]
        if count == 0:
            lines.append(f"-- 表 {table} 无数据，跳过")
            lines.append("")
            continue

        cursor.execute(f"SELECT * FROM `{table}`")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        lines.append(f"-- {table}: {count} 行")
        col_names = ", ".join(f"`{c}`" for c in columns)

        for row in rows:
            values = []
            for val in row:
                if val is None:
                    values.append("NULL")
                elif isinstance(val, (int, float)):
                    values.append(str(val))
                elif isinstance(val, bytes):
                    values.append(f"_binary'{val.hex()}'")
                else:
                    escaped = str(val).replace("\\", "\\\\").replace("'", "\\'")
                    values.append(f"'{escaped}'")
            lines.append(f"INSERT IGNORE INTO `{table}` ({col_names}) VALUES ({', '.join(values)});")

        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="RAGFlow 数据库初始化 SQL 导出")
    parser.add_argument(
        "--output", "-o",
        default="ragflow_init.sql",
        help="输出 SQL 文件路径（默认: ragflow_init.sql）",
    )
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="仅导出表结构，不含种子数据",
    )
    parser.add_argument(
        "--data-only",
        action="store_true",
        help="仅导出种子数据，不含表结构",
    )
    args = parser.parse_args()

    cursor = connection.cursor()
    try:
        sql_parts = []

        if not args.data_only:
            print("正在导出表结构...")
            sql_parts.append(export_schema(cursor))
            tables = get_all_tables(cursor)
            print(f"  已导出 {len(tables)} 张表的 CREATE TABLE 语句")

        if not args.schema_only:
            print("正在导出种子数据...")
            sql_parts.append(export_seed_data(cursor))
            print("  种子数据导出完成")

        full_sql = "\n".join(sql_parts)

        with open(args.output, "w", encoding="utf-8") as f:
            f.write(full_sql)

        file_size = os.path.getsize(args.output)
        print(f"\n✅ SQL 文件已生成: {os.path.abspath(args.output)}")
        print(f"   大小: {file_size:,} 字节")
        print(f"\n下一步:")
        print(f"   1. 将此文件提交给 DBA 审核")
        print(f"   2. 审核通过后，在新服务器 MySQL 上执行:")
        print(f"      mysql -u root -p < {args.output}")

    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
