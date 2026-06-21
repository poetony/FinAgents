#!/usr/bin/env python3
"""模拟后端调用 prepare_stock_data_async"""
import asyncio
import sys
from pathlib import Path

# 与 run_backend 相同：添加路径并加载 env
SINGLE_DIR = Path(__file__).resolve().parent
PARENT_DIR = SINGLE_DIR.parent
sys.path.insert(0, str(PARENT_DIR))
sys.path.insert(0, str(SINGLE_DIR))

from dotenv import load_dotenv
load_dotenv(PARENT_DIR / ".env")
load_dotenv(SINGLE_DIR / ".env", override=True)

async def main():
    from tradingagents.utils.stock_validator import prepare_stock_data_async
    import time
    analysis_date = time.strftime("%Y-%m-%d")
    print(f"Testing prepare_stock_data_async for 000536, analysis_date={analysis_date}")
    r = await prepare_stock_data_async(
        stock_code="000536",
        market_type="A股",
        period_days=30,
        analysis_date=analysis_date
    )
    print(f"is_valid: {r.is_valid}")
    print(f"error_message: {r.error_message}")
    print(f"stock_name: {r.stock_name}")
    return 0 if r.is_valid else 1

if __name__ == "__main__":
    exit(asyncio.run(main()))
