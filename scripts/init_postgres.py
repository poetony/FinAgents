#!/usr/bin/env python3
"""
PostgreSQL 数据库初始化脚本
创建 tradingagents 数据库及所需表结构
运行前请确保 .env 中已配置 POSTGRES_* 变量
"""

import os
import sys

# 确保项目根目录在 path 中
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 加载 .env
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(project_root, ".env"))
except ImportError:
    pass


def main():
    print("PostgreSQL 数据库初始化...")
    try:
        from app.core.database import init_database, _get_postgres_config
        config = _get_postgres_config()
        print(f"  连接: {config.get('host', 'localhost')}:{config.get('port', 5432)}/{config.get('database', 'tradingagents')}")
        init_database()
        print("[OK] 初始化完成")
    except Exception as e:
        print(f"[FAIL] 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
