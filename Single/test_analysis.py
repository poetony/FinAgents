#!/usr/bin/env python3
"""测试单股分析 API - 000536"""
import requests
import time
import json

API = "http://localhost:8303"
headers = {"Authorization": "Bearer anonymous", "Content-Type": "application/json"}

payload = {
    "symbol": "000536",
    "stock_code": "000536",
    "parameters": {
        "market_type": "A股",
        "analysis_date": time.strftime("%Y-%m-%d"),
        "research_depth": "标准",
        "selected_analysts": ["市场分析师", "基本面分析师", "新闻分析师"],
        "include_sentiment": True,
        "include_risk": True,
        "language": "zh-CN",
        "quick_analysis_model": "stepfun-ai/Step-3.5-Flash",
        "deep_analysis_model": "deepseek-ai/DeepSeek-V3.2",
        "engine": "v2",
    },
}

print("1. 提交分析任务 000536...")
try:
    r = requests.post(f"{API}/api/analysis/single", json=payload, headers=headers, timeout=30)
    print(f"   状态码: {r.status_code}")
    if r.status_code != 200:
        print(f"   响应: {r.text[:500]}")
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if not data.get("success") or not data.get("data", {}).get("task_id"):
        print("提交失败:", data)
        exit(1)
except Exception as e:
    print("请求异常:", e)
    exit(1)
task_id = data["data"]["task_id"]
print(f"   任务已创建: {task_id}")

print("2. 轮询任务状态...")
for i in range(60):
    r = requests.get(f"{API}/api/analysis/tasks/{task_id}/status", headers=headers, timeout=10)
    d = r.json().get("data", r.json())
    status = d.get("status", "")
    progress = d.get("progress", 0)
    msg = d.get("message", d.get("current_step", ""))
    print(f"   [{i+1}] {status} {progress}% - {msg[:50] if msg else '-'}")
    if status == "completed":
        print("   分析完成!")
        break
    if status == "failed":
        err = d.get("error_message", d.get("last_error", ""))
        print("   分析失败:", err[:500] if err else "(无详细错误)")
        print("   [调试] 完整状态:", json.dumps(d, ensure_ascii=False, default=str)[:800])
        exit(1)
    time.sleep(5)

if status != "completed":
    print("   超时，请稍后在前端查看结果")
    exit(0)

print("3. 获取分析结果...")
r = requests.get(f"{API}/api/analysis/tasks/{task_id}/result", headers=headers, timeout=30)
result = r.json().get("data", r.json())
decision = result.get("decision", {})
summary = result.get("summary", "")[:200]
print(f"   决策: {decision.get('action', decision.get('analysis_view', '-'))}")
print(f"   摘要: {summary}...")
print("\n测试完成.")
