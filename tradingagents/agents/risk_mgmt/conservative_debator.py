from langchain_core.messages import AIMessage
import time
import json

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger
logger = get_logger("default")

# 导入模板客户端
from tradingagents.utils.template_client import get_agent_prompt
from tradingagents.agents.utils.prompt_trim import (
    trim_text_for_prompt,
    trim_history_for_prompt,
)
from tradingagents.agents.utils.llm_safe_invoke import invoke_with_rate_limit_fallback


def create_safe_debator(llm):
    def safe_node(state) -> dict:
        # 使用 .get() 安全访问辩论状态
        risk_debate_state = state.get("risk_debate_state", {})
        history = risk_debate_state.get("history", "")
        safe_history = risk_debate_state.get("safe_history", "")

        current_risky_response = risk_debate_state.get("current_risky_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")

        # 使用 .get() 安全访问，支持用户只选择部分分析师的情况
        market_research_report = state.get("market_report", "")
        sentiment_report = state.get("sentiment_report", "")
        news_report = state.get("news_report", "")
        fundamentals_report = state.get("fundamentals_report", "")

        trader_decision = state.get("trader_investment_plan", "")

        # Prompt裁剪：保留关键信息，降低TPM峰值
        market_research_report_prompt = trim_text_for_prompt(market_research_report, 2200)
        sentiment_report_prompt = trim_text_for_prompt(sentiment_report, 1600)
        news_report_prompt = trim_text_for_prompt(news_report, 2000)
        fundamentals_report_prompt = trim_text_for_prompt(fundamentals_report, 2000)
        trader_decision_prompt = trim_text_for_prompt(
            trader_decision, 1800, keep_tail_ratio=0.4
        )
        history_prompt = trim_history_for_prompt(history, 2800)
        current_risky_response_prompt = trim_text_for_prompt(
            current_risky_response, 1000, keep_tail_ratio=0.5
        )
        current_neutral_response_prompt = trim_text_for_prompt(
            current_neutral_response, 1000, keep_tail_ratio=0.5
        )

        # 📊 记录输入数据长度
        logger.info(f"📊 [Safe Analyst] 输入数据长度统计:")
        logger.info(f"  - market_report: {len(market_research_report):,} 字符")
        logger.info(f"  - sentiment_report: {len(sentiment_report):,} 字符")
        logger.info(f"  - news_report: {len(news_report):,} 字符")
        logger.info(f"  - fundamentals_report: {len(fundamentals_report):,} 字符")
        logger.info(f"  - trader_decision: {len(trader_decision):,} 字符")
        logger.info(f"  - history: {len(history):,} 字符")
        total_length = (
            len(market_research_report_prompt)
            + len(sentiment_report_prompt)
            + len(news_report_prompt)
            + len(fundamentals_report_prompt)
            + len(trader_decision_prompt)
            + len(history_prompt)
            + len(current_risky_response_prompt)
            + len(current_neutral_response_prompt)
        )
        logger.info(f"  - 总Prompt长度: {total_length:,} 字符 (~{total_length//4:,} tokens)")

        # 🆕 使用模板系统获取提示词
        try:
            # 准备模板变量
            template_variables = {
                "ticker": state.get("company_of_interest", ""),
                "company_name": state.get("company_of_interest", ""),
                "market_name": "",
                "current_date": state.get("trade_date", ""),
                "start_date": state.get("trade_date", ""),
                "currency_name": "",
                "currency_symbol": "",
                "tool_names": ""
            }

            from tradingagents.utils.template_client import get_template_client
            ctx = state.get("agent_context") or {}
            tpl_info = get_template_client().get_effective_template(
                agent_type="debators",
                agent_name="conservative_debator",
                user_id=ctx.get("user_id"),
                preference_id=ctx.get("preference_id") or "conservative",
                context=None
            )
            if tpl_info:
                logger.info(f"📚 [模板选择] source={tpl_info.get('source')} id={tpl_info.get('template_id')} version={tpl_info.get('version')} agent=debators/conservative_debator")

            # 从模板系统获取提示词
            system_prompt = get_agent_prompt(
                agent_type="debators",
                agent_name="conservative_debator",
                variables=template_variables,
                preference_id="conservative",
                fallback_prompt=None
            )

            # 检查模板内容是否有效（防止模板系统返回默认6字占位符）
            if not system_prompt or len(system_prompt.strip()) < 100:
                raise ValueError(f"模板内容不足({len(system_prompt or '')}字符)，使用硬编码提示词")
            logger.info(f"✅ [保守风险分析师] 成功从模板系统获取提示词 (长度: {len(system_prompt)})")

        except Exception as e:
            logger.warning(f"⚠️ [保守风险分析师] 模板获取失败，使用硬编码提示词: {e}")
            # 降级：使用硬编码提示词
            system_prompt = """作为安全/保守风险分析师，您的主要目标是保护资产、最小化波动性，并确保稳定、可靠的增长。

您优先考虑稳定性、安全性和风险缓解，仔细评估潜在损失、经济衰退和市场波动。

在评估交易员的决策或计划时，请批判性地审查高风险要素，指出决策可能使公司面临不当风险的地方。

您的任务是积极反驳激进和中性分析师的论点，突出他们的观点可能忽视的潜在威胁。

请用中文以对话方式输出。"""
            logger.warning(f"⚠️ [保守风险分析师] 使用降级提示词 (长度: {len(system_prompt)})")

        # 构建完整提示词
        prompt = f"""{system_prompt}

以下是交易员的决策：
{trader_decision_prompt}

将以下来源的见解纳入您的论点：
市场研究报告：{market_research_report_prompt}
社交媒体情绪报告：{sentiment_report_prompt}
最新世界事务报告：{news_report_prompt}
公司基本面报告：{fundamentals_report_prompt}

当前对话历史：{history_prompt}
激进分析师的最后回应：{current_risky_response_prompt}
中性分析师的最后回应：{current_neutral_response_prompt}

请提出您的保守观点，强调为什么低风险方法是最安全的。"""

        logger.info(f"⏱️ [Safe Analyst] 开始调用LLM...")
        llm_start_time = time.time()

        response = invoke_with_rate_limit_fallback(
            llm=llm,
            prompt=prompt,
            fallback_content=(
                "当前存在模型限流，基于已有信息给出保守替代意见："
                "优先防守，降低仓位波动，等待风险信号进一步明朗后再加仓。"
            ),
            logger=logger,
            node_name="Safe Analyst",
        )

        llm_elapsed = time.time() - llm_start_time
        logger.info(f"⏱️ [Safe Analyst] LLM调用完成，耗时: {llm_elapsed:.2f}秒")

        argument = f"Safe Analyst: {response.content}"

        new_count = risk_debate_state["count"] + 1
        logger.info(f"🛡️ [保守风险分析师] 发言完成，计数: {risk_debate_state['count']} -> {new_count}")

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "risky_history": risk_debate_state.get("risky_history", ""),
            "safe_history": safe_history + "\n" + argument,
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Safe",
            "current_risky_response": risk_debate_state.get(
                "current_risky_response", ""
            ),
            "current_safe_response": argument,
            "current_neutral_response": risk_debate_state.get(
                "current_neutral_response", ""
            ),
            "count": new_count,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return safe_node
