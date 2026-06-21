#!/usr/bin/env python3
"""
行业板块分析提供器
整合 sector_cluster 项目的封板密度 + 资金流向因子，
为单股分析提供行业上下文。
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# 将 sector_cluster 项目加入路径
SECTOR_CLUSTER_DIR = "/Data/soft/sector_cluster"
if SECTOR_CLUSTER_DIR not in sys.path:
    sys.path.insert(0, SECTOR_CLUSTER_DIR)


def _get_db_conn(dbname: str):
    """获取数据库连接"""
    import psycopg2
    from urllib.parse import quote_plus

    host = os.getenv("QUANTDB_HOST", os.getenv("POSTGRES_HOST", "localhost"))
    port = os.getenv("QUANTDB_PORT", os.getenv("POSTGRES_PORT", "5432"))
    user = os.getenv("QUANTDB_USER", os.getenv("POSTGRES_USER", "postgres"))
    password = os.getenv("QUANTDB_PASSWORD", os.getenv("POSTGRES_PASSWORD", ""))
    pw = quote_plus(str(password)) if password else ""
    conn_str = f"postgresql://{user}:{pw}@{host}:{port}/{dbname}" if pw else f"postgresql://{user}@{host}:{port}/{dbname}"
    return psycopg2.connect(conn_str)


def get_stock_sectors(symbol: str) -> Dict[str, str]:
    """
    获取股票的申万行业分类

    Returns:
        {"sw1": "建筑材料", "sw2": "装修建材", "concepts": ["光伏", ...]}
    """
    code6 = str(symbol).strip()
    if "." in code6:
        code6 = code6.split(".")[0]
    code6 = code6.zfill(6) if len(code6) <= 6 else code6[-6:]

    result = {"sw1": "", "sw2": "", "concepts": []}

    try:
        conn = _get_db_conn("heatmap")
        cur = conn.cursor()

        for try_code in (code6, f"{code6}.SZ" if code6.startswith(("0", "3")) else f"{code6}.SH"):
            cur.execute("""
                SELECT s.name, s.type FROM sectors s
                JOIN stock_sectors ss ON ss.sector_code = s.code
                WHERE ss.stock_code = %s
            """, (try_code,))
            rows = cur.fetchall()
            if rows:
                break
        conn.close()

        if not rows:
            return result

        for name, stype in rows:
            if stype == 0:  # SW1
                result["sw1"] = name.replace("A股-申万行业-", "")
            elif stype == 1:  # SW2
                result["sw2"] = name.replace("A股-申万二级-", "")
            elif stype in (2, 3):  # 概念
                concept = name.replace("A股-热门概念-", "").replace("A股-概念板块-", "")
                result["concepts"].append(concept)

        logger.info(f"[Sector] {code6} -> SW1={result['sw1']}, SW2={result['sw2']}, concepts={len(result['concepts'])}个")
        return result

    except Exception as e:
        logger.warning(f"[Sector] 获取 {symbol} 行业分类失败: {e}")
        return result


def get_sector_analysis(date: str, sw1: str = None, sw2: str = None) -> Dict[str, Any]:
    """
    获取指定日期的行业板块分析

    Args:
        date: 分析日期 YYYY-MM-DD
        sw1: 申万一级行业名（如 "建筑材料"）
        sw2: 申万二级行业名（如 "装修建材"）

    Returns:
        {
            "date": "2026-06-09",
            "total_sealed": 45,
            "sw1_sector": {
                "name": "建筑材料",
                "sealed_count": 3, "total_stocks": 75,
                "density_pct": 4.0, "amount_yi": 45.2, "share_pct": 2.1,
                "avg_chg": 1.5, "up_ratio": 0.62,
                "cluster_score": 0.35, "capital_score": 0.28, "herding_score": 0.32,
                "signal": "偏强"
            },
            "sw2_sector": {...},
            "top_sectors": [{"name": ..., "herding_score": ...}, ...],
            "market_temperature": "偏热"
        }
    """
    try:
        from sector_cluster_factor import compute_all_factors

        factors = compute_all_factors(date)
    except Exception as e:
        logger.warning(f"[Sector] 计算行业因子失败 (date={date}): {e}")
        return {"date": date, "error": str(e)}

    detail = factors.get("detail", {})
    herding = factors.get("herding", {})
    cluster = factors.get("cluster", {})

    result = {
        "date": date,
        "total_sealed": factors.get("total_sealed", 0),
    }

    # 查找目标行业
    for sector_type, sector_name in [("sw1_sector", sw1), ("sw2_sector", sw2)]:
        if not sector_name:
            continue
        # sector_cluster 使用的名称格式: "A股-申万行业-建筑材料" / "A股-申万二级-装修建材"
        full_name = f"A股-申万行业-{sector_name}" if sector_type == "sw1_sector" else f"A股-申万二级-{sector_name}"
        if full_name in detail:
            d = detail[full_name]
            result[sector_type] = {
                "name": sector_name,
                "sealed_count": d.get("sealed_count", 0),
                "total_stocks": d.get("total_stocks", 0),
                "density_pct": d.get("density_pct", 0),
                "amount_yi": d.get("amount_yi", 0),
                "share_pct": d.get("share_pct", 0),
                "avg_chg": d.get("avg_chg", 0),
                "up_ratio": d.get("up_ratio", 0),
                "cluster_score": cluster.get(full_name, 0),
                "capital_score": factors.get("capital", {}).get(full_name, 0),
                "herding_score": herding.get(full_name, 0),
            }
            # 信号标签
            hs = result[sector_type]["herding_score"]
            if hs > 1.0:
                result[sector_type]["signal"] = "真抱团"
            elif hs > 0.3:
                result[sector_type]["signal"] = "偏强"
            elif hs > -0.3:
                result[sector_type]["signal"] = "中性"
            elif hs > -1.0:
                result[sector_type]["signal"] = "偏弱"
            else:
                result[sector_type]["signal"] = "冷门"

    # Top 行业排名
    sorted_sectors = sorted(herding.items(), key=lambda x: x[1], reverse=True)
    result["top_sectors"] = [
        {"name": name, "herding_score": score}
        for name, score in sorted_sectors[:10] if score > 0
    ]
    result["bottom_sectors"] = [
        {"name": name, "herding_score": score}
        for name, score in sorted_sectors[-5:] if score < 0
    ]

    # 市场温度
    avg_herding = sum(herding.values()) / len(herding) if herding else 0
    if avg_herding > 0.3:
        result["market_temperature"] = "偏热"
    elif avg_herding > 0:
        result["market_temperature"] = "温和"
    elif avg_herding > -0.3:
        result["market_temperature"] = "偏冷"
    else:
        result["market_temperature"] = "冰点"

    logger.info(f"[Sector] 行业分析完成: total_sealed={result['total_sealed']}, "
                f"market_temp={result['market_temperature']}")
    return result


def format_sector_context(sector_analysis: Dict[str, Any], stock_sectors: Dict[str, str]) -> str:
    """
    将行业分析结果格式化为 LLM 可读的上下文文本
    """
    if sector_analysis.get("error"):
        return ""

    lines = []
    lines.append(f"## 行业板块分析 (日期: {sector_analysis.get('date', '')})")
    lines.append(f"市场温度: {sector_analysis.get('market_temperature', '未知')}")
    lines.append(f"当日全市场封板股票数: {sector_analysis.get('total_sealed', 0)}")
    lines.append("")

    # SW1 行业
    sw1 = sector_analysis.get("sw1_sector")
    if sw1:
        lines.append(f"### 所属申万一级行业: {sw1.get('name', '')}")
        lines.append(f"- 封板数: {sw1.get('sealed_count', 0)}/{sw1.get('total_stocks', 0)} (密度 {sw1.get('density_pct', 0):.1f}%)")
        lines.append(f"- 成交额: {sw1.get('amount_yi', 0):.1f}亿 (全市场占比 {sw1.get('share_pct', 0):.1f}%)")
        lines.append(f"- 平均涨跌幅: {sw1.get('avg_chg', 0):.1f}%, 上涨比例: {sw1.get('up_ratio', 0):.1%}")
        lines.append(f"- 封板密度分: {sw1.get('cluster_score', 0):.2f}, 资金流分: {sw1.get('capital_score', 0):.2f}")
        lines.append(f"- 综合抱团分: {sw1.get('herding_score', 0):.2f} → 信号: **{sw1.get('signal', '')}**")
        lines.append("")

    # SW2 行业
    sw2 = sector_analysis.get("sw2_sector")
    if sw2:
        lines.append(f"### 所属申万二级行业: {sw2.get('name', '')}")
        lines.append(f"- 封板数: {sw2.get('sealed_count', 0)}/{sw2.get('total_stocks', 0)} (密度 {sw2.get('density_pct', 0):.1f}%)")
        lines.append(f"- 成交额: {sw2.get('amount_yi', 0):.1f}亿 (全市场占比 {sw2.get('share_pct', 0):.1f}%)")
        lines.append(f"- 平均涨跌幅: {sw2.get('avg_chg', 0):.1f}%, 上涨比例: {sw2.get('up_ratio', 0):.1%}")
        lines.append(f"- 综合抱团分: {sw2.get('herding_score', 0):.2f} → 信号: **{sw2.get('signal', '')}**")
        lines.append("")

    # 概念板块
    concepts = stock_sectors.get("concepts", [])
    if concepts:
        lines.append(f"### 相关概念板块: {', '.join(concepts[:8])}")

    # Top 抱团行业
    tops = sector_analysis.get("top_sectors", [])
    if tops:
        lines.append(f"\n### 当日资金抱团Top{len(tops)}行业:")
        for i, s in enumerate(tops, 1):
            lines.append(f"  {i}. {s['name']} (抱团分: {s['herding_score']:.2f})")

    return "\n".join(lines)
