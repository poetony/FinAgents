"""
辩论阶段 Prompt 长度裁剪工具。

目标：
- 在不丢失关键上下文的前提下，降低单次请求 token 峰值。
- 报告类文本保留首尾（通常开头有摘要，结尾有结论）。
- 对话历史优先保留最近轮次（对当前决策最相关）。
"""

from typing import Optional


def _safe_text(text: Optional[str]) -> str:
    if not text:
        return ""
    return str(text).strip()


def trim_text_for_prompt(
    text: Optional[str],
    max_chars: int,
    keep_tail_ratio: float = 0.3,
    marker: str = "\n...[内容已裁剪]...\n",
) -> str:
    """
    通用文本裁剪：保留开头 + 结尾。
    """
    content = _safe_text(text)
    if len(content) <= max_chars or max_chars <= 0:
        return content

    tail_len = int(max_chars * keep_tail_ratio)
    tail_len = max(200, min(tail_len, max_chars - 200))
    head_len = max_chars - tail_len - len(marker)
    if head_len < 100:
        head_len = 100
        tail_len = max_chars - head_len - len(marker)

    return content[:head_len] + marker + content[-tail_len:]


def trim_history_for_prompt(
    history: Optional[str],
    max_chars: int,
    marker: str = "\n...[历史已裁剪，仅保留最近轮次]...\n",
) -> str:
    """
    历史裁剪：优先保留最近内容（尾部）。
    """
    content = _safe_text(history)
    if len(content) <= max_chars or max_chars <= 0:
        return content

    keep_len = max_chars - len(marker)
    if keep_len <= 0:
        return content[-max_chars:]
    return marker + content[-keep_len:]
