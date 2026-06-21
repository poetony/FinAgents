#!/usr/bin/env python3
"""直接调用分析逻辑，捕获真实异常（不依赖 API 重启）"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

SINGLE_DIR = Path(__file__).resolve().parent
PARENT_DIR = SINGLE_DIR.parent
sys.path.insert(0, str(PARENT_DIR))
sys.path.insert(0, str(SINGLE_DIR))

from dotenv import load_dotenv
load_dotenv(PARENT_DIR / ".env")
if (SINGLE_DIR / ".env").exists():
    load_dotenv(SINGLE_DIR / ".env", override=True)

# 导入分析请求模型
from app.models.analysis import SingleAnalysisRequest, AnalysisParameters

async def main():
    from app.services.simple_analysis_service import get_simple_analysis_service

    request = SingleAnalysisRequest(
        symbol="000536",
        stock_code="000536",
        parameters=AnalysisParameters(
            market_type="A股",
            analysis_date=datetime.now().strftime("%Y-%m-%d"),
            research_depth="标准",
            selected_analysts=["市场分析师", "基本面分析师", "新闻分析师"],
            include_sentiment=True,
            include_risk=True,
            language="zh-CN",
            quick_analysis_model="stepfun-ai/Step-3.5-Flash",
            deep_analysis_model="deepseek-ai/DeepSeek-V3.2",
            engine="v2",
        ),
    )

    print("直接执行分析逻辑（会显示真实异常）...")
    service = get_simple_analysis_service()
    try:
        result = await service._execute_analysis_sync(
            "test-direct-001",
            "anonymous",
            request,
            progress_tracker=None,
        )
        print("分析成功:", list(result.keys())[:5])
    except Exception as e:
        print("\n" + "="*60)
        print("【真实异常】")
        print(f"  类型: {type(e).__name__}")
        print(f"  消息: {e}")
        print("="*60)
        import traceback
        traceback.print_exc()
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
