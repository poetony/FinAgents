#!/usr/bin/env python3
"""
将 prompt_templates 从导出 JSON 导入到 PostgreSQL

适用于已迁移到 PostgreSQL 的环境。使用 app.core.database 的 PostgresDBCompat。

使用方法:
    cd TradingAgents
    python scripts/import_prompt_templates_postgres.py
    python scripts/import_prompt_templates_postgres.py install/database_export_config_2026-02-03.json
    python scripts/import_prompt_templates_postgres.py --overwrite
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 加载 .env（与 app.main 一致，确保数据库连接能读取配置）
try:
    from dotenv import load_dotenv
    for p in [project_root / ".env", project_root.parent / "Stock_analysis" / ".env"]:
        if p.exists():
            load_dotenv(p, override=True)
except ImportError:
    pass


def load_export_file(file_path: str) -> Dict[str, Any]:
    """加载导出的 JSON 文件"""
    print(f"\n[LOAD] 加载导出文件: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "data" not in data or "prompt_templates" not in data["data"]:
        raise ValueError("文件格式不正确，缺少 data.prompt_templates")
    return data


def prepare_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """准备文档：确保 _id 为字符串，处理日期等"""
    d = dict(doc)
    if "_id" in d:
        d["_id"] = str(d["_id"])
    return d


def main():
    import argparse
    parser = argparse.ArgumentParser(description="导入 prompt_templates 到 PostgreSQL")
    parser.add_argument(
        "export_file",
        nargs="?",
        help="导出 JSON 路径（默认：install/database_export_config_*.json 最新文件）",
    )
    parser.add_argument("--overwrite", action="store_true", help="覆盖已存在的模板（按 agent_type+agent_name+preference_type）")
    args = parser.parse_args()

    # 默认文件
    if not args.export_file:
        install_dir = project_root / "install"
        config_files = sorted(install_dir.glob("database_export_config_*.json"))
        if not config_files:
            print("[ERROR] install 目录中未找到 database_export_config_*.json")
            sys.exit(1)
        args.export_file = str(config_files[-1])
        print(f"[INFO] 使用: {args.export_file}")

    export_data = load_export_file(args.export_file)
    templates: List[Dict[str, Any]] = export_data["data"]["prompt_templates"]
    print(f"[OK] 找到 {len(templates)} 个模板")

    from app.core.database import get_mongo_db_sync

    db = get_mongo_db_sync()
    coll = db.prompt_templates

    inserted = 0
    skipped = 0
    for doc in templates:
        doc = prepare_doc(doc)
        doc_id = str(doc.get("_id", doc.get("id", "")))
        if not doc_id:
            continue
        if not args.overwrite:
            existing = coll.find_one({"_id": doc_id})
            if existing:
                skipped += 1
                continue
        coll.insert_one(doc)
        inserted += 1

    print(f"\n[OK] 导入完成: 插入 {inserted}, 跳过 {skipped}")
    print("   重启后端后，analysts/fundamentals_analyst 等模板将生效。")


if __name__ == "__main__":
    main()
