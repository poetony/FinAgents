#!/usr/bin/env python3
"""
统一新闻分析工具
整合A股、港股、美股等不同市场的新闻获取逻辑到一个工具函数中
让大模型只需要调用一个工具就能获取所有类型股票的新闻数据

⚠️ DEPRECATED - 此文件已废弃
====================================
此工具已迁移到新的工具系统：
- 新位置: core/tools/implementations/news/stock_news.py
- 迁移日期: 2025-12-15
- 移除计划: 2026-06-15 (6个月后)

请使用新的工具系统：
    from core.tools.implementations.news import get_stock_news_unified

或通过工具注册表：
    from core.tools import get_tool
    tool = get_tool("get_stock_news_unified")

注意：新工具使用了更简洁的实现（减少76%代码），但可能缺少以下功能：
- MongoDB数据库缓存
- 复杂的同步机制（线程池+事件循环）

如果需要这些功能，请参考迁移指南：
docs/design/v2.0/tools/TOOLS_MIGRATION_GUIDE.md
====================================
"""

import logging
import warnings
from datetime import datetime
import re

# 发出废弃警告
warnings.warn(
    "tradingagents.tools.unified_news_tool 已废弃，请使用 core.tools.implementations.news.stock_news",
    DeprecationWarning,
    stacklevel=2
)

logger = logging.getLogger(__name__)

class UnifiedNewsAnalyzer:
    """统一新闻分析器，整合所有新闻获取逻辑"""
    
    def __init__(self, toolkit):
        """初始化统一新闻分析器
        
        Args:
            toolkit: 包含各种新闻获取工具的工具包
        """
        self.toolkit = toolkit
        
    def get_stock_news_unified(self, stock_code: str, max_news: int = 10, model_info: str = "") -> str:
        """
        统一新闻获取接口
        根据股票代码自动识别股票类型并获取相应新闻
        
        Args:
            stock_code: 股票代码
            max_news: 最大新闻数量
            model_info: 当前使用的模型信息，用于特殊处理
            
        Returns:
            str: 格式化的新闻内容
        """
        logger.info(f"[统一新闻工具] 开始获取 {stock_code} 的新闻，模型: {model_info}")
        logger.info(f"[统一新闻工具] 🤖 当前模型信息: {model_info}")
        
        # 识别股票类型
        stock_type = self._identify_stock_type(stock_code)
        logger.info(f"[统一新闻工具] 股票类型: {stock_type}")
        
        # 根据股票类型调用相应的获取方法
        if stock_type == "A股":
            result = self._get_a_share_news(stock_code, max_news, model_info)
        elif stock_type == "港股":
            result = self._get_hk_share_news(stock_code, max_news, model_info)
        elif stock_type == "美股":
            result = self._get_us_share_news(stock_code, max_news, model_info)
        else:
            # 默认使用A股逻辑
            result = self._get_a_share_news(stock_code, max_news, model_info)
        
        # 🔍 添加详细的结果调试日志
        logger.info(f"[统一新闻工具] 📊 新闻获取完成，结果长度: {len(result)} 字符")
        logger.info(f"[统一新闻工具] 📋 返回结果预览 (前1000字符): {result[:1000]}")
        
        # 如果结果为空或过短，记录警告
        if not result or len(result.strip()) < 50:
            logger.warning(f"[统一新闻工具] ⚠️ 返回结果异常短或为空！")
            logger.warning(f"[统一新闻工具] 📝 完整结果内容: '{result}'")
        
        return result
    
    def _identify_stock_type(self, stock_code: str) -> str:
        """识别股票类型"""
        stock_code = stock_code.upper().strip()
        
        # A股判断
        if re.match(r'^(00|30|60|68)\d{4}$', stock_code):
            return "A股"
        elif re.match(r'^(SZ|SH)\d{6}$', stock_code):
            return "A股"
        
        # 港股判断
        elif re.match(r'^\d{4,5}\.HK$', stock_code):
            return "港股"
        elif re.match(r'^\d{4,5}$', stock_code) and len(stock_code) <= 5:
            return "港股"
        
        # 美股判断
        elif re.match(r'^[A-Z]{1,5}$', stock_code):
            return "美股"
        elif '.' in stock_code and not stock_code.endswith('.HK'):
            return "美股"
        
        # 默认按A股处理
        else:
            return "A股"

    def _get_news_from_database(self, stock_code: str, max_news: int = 10) -> str:
        """
        从数据库获取新闻

        Args:
            stock_code: 股票代码
            max_news: 最大新闻数量

        Returns:
            str: 格式化的新闻内容，如果没有新闻则返回空字符串
        """
        try:
            from tradingagents.config.database_manager import get_db_client
            from datetime import timedelta

            # 🔧 确保 max_news 是整数（防止传入浮点数）
            max_news = int(max_news)

            client = get_db_client()
            if not client:
                logger.warning(f"[统一新闻工具] 无法连接到 PostgreSQL")
                return ""

            db = client.get_database('tradingagents')
            collection = db.stock_news

            # 标准化股票代码（去除后缀）
            clean_code = stock_code.replace('.SH', '').replace('.SZ', '').replace('.SS', '')\
                                   .replace('.XSHE', '').replace('.XSHG', '').replace('.HK', '')

            # 查询最近30天的新闻（扩大时间范围）
            thirty_days_ago = datetime.now() - timedelta(days=30)

            # 尝试多种查询方式（使用 symbol 字段）
            query_list = [
                {'symbol': clean_code, 'publish_time': {'$gte': thirty_days_ago}},
                {'symbol': stock_code, 'publish_time': {'$gte': thirty_days_ago}},
                {'symbols': clean_code, 'publish_time': {'$gte': thirty_days_ago}},
                # 如果最近30天没有新闻，则查询所有新闻（不限时间）
                {'symbol': clean_code},
                {'symbols': clean_code},
            ]

            news_items = []
            for query in query_list:
                cursor = collection.find(query).sort('publish_time', -1).limit(max_news)
                news_items = list(cursor)
                if news_items:
                    logger.info(f"[统一新闻工具] 📊 使用查询 {query} 找到 {len(news_items)} 条新闻")
                    break

            if not news_items:
                logger.info(f"[统一新闻工具] 数据库中没有找到 {stock_code} 的新闻")
                return ""

            # 格式化新闻
            report = f"# {stock_code} 最新新闻 (数据库缓存)\n\n"
            report += f"📅 查询时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            report += f"📊 新闻数量: {len(news_items)} 条\n\n"

            for i, news in enumerate(news_items, 1):
                title = news.get('title', '无标题')
                content = news.get('content', '') or news.get('summary', '')
                source = news.get('source', '未知来源')
                publish_time = news.get('publish_time', datetime.now())
                sentiment = news.get('sentiment', 'neutral')

                # 情绪图标
                sentiment_icon = {
                    'positive': '📈',
                    'negative': '📉',
                    'neutral': '➖'
                }.get(sentiment, '➖')

                report += f"## {i}. {sentiment_icon} {title}\n\n"
                report += f"**来源**: {source} | **时间**: {publish_time.strftime('%Y-%m-%d %H:%M') if isinstance(publish_time, datetime) else publish_time}\n"
                report += f"**情绪**: {sentiment}\n\n"

                if content:
                    # 限制内容长度
                    content_preview = content[:500] + '...' if len(content) > 500 else content
                    report += f"{content_preview}\n\n"

                report += "---\n\n"

            logger.info(f"[统一新闻工具] ✅ 成功从数据库获取并格式化 {len(news_items)} 条新闻")
            return report

        except Exception as e:
            logger.error(f"[统一新闻工具] 从数据库获取新闻失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return ""

    def _sync_news_from_akshare(self, stock_code: str, max_news: int = 10) -> bool:
        """
        从AKShare同步新闻到数据库（同步方法）
        使用同步的数据库客户端和新线程中的事件循环，避免事件循环冲突

        Args:
            stock_code: 股票代码
            max_news: 最大新闻数量

        Returns:
            bool: 是否同步成功
        """
        try:
            import asyncio
            import concurrent.futures

            # 标准化股票代码（去除后缀）
            clean_code = stock_code.replace('.SH', '').replace('.SZ', '').replace('.SS', '')\
                                   .replace('.XSHE', '').replace('.XSHG', '').replace('.HK', '')

            logger.info(f"[统一新闻工具] 🔄 开始同步 {clean_code} 的新闻...")

            # 🔥 在新线程中运行，使用同步数据库客户端
            def run_sync_in_new_thread():
                """在新线程中创建新的事件循环并运行同步任务"""
                # 创建新的事件循环
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)

                try:
                    # 定义异步获取新闻任务
                    async def get_news_task():
                        try:
                            # 动态导入 AKShare provider（正确的导入路径）
                            from tradingagents.dataflows.providers.china.akshare import AKShareProvider

                            # 创建 provider 实例
                            provider = AKShareProvider()

                            # 调用 provider 获取新闻
                            news_data = await provider.get_stock_news(
                                symbol=clean_code,
                                limit=max_news
                            )

                            # API限流：成功后休眠
                            await asyncio.sleep(0.2)

                            return news_data

                        except Exception as e:
                            logger.error(f"[统一新闻工具] ❌ 获取新闻失败: {e}")
                            import traceback
                            logger.error(traceback.format_exc())

                            # 失败后也要休眠，避免"失败雪崩"
                            # 失败时休眠更长时间，给API服务器恢复的机会
                            await asyncio.sleep(1.0)

                            return None

                    # 在新的事件循环中获取新闻
                    news_data = new_loop.run_until_complete(get_news_task())

                    if not news_data:
                        logger.warning(f"[统一新闻工具] ⚠️ 未获取到新闻数据")
                        return False

                    logger.info(f"[统一新闻工具] 📥 获取到 {len(news_data)} 条新闻")

                    # 🔥 使用同步方法保存到数据库（不依赖事件循环）
                    from app.services.news_data_service import NewsDataService

                    news_service = NewsDataService()
                    saved_count = news_service.save_news_data_sync(
                        news_data=news_data,
                        data_source="akshare",
                        market="CN"
                    )

                    logger.info(f"[统一新闻工具] ✅ 同步成功: {saved_count} 条新闻")
                    return saved_count > 0

                finally:
                    # 清理事件循环
                    new_loop.close()

            # 在线程池中执行
            logger.info(f"[统一新闻工具] 在新线程中运行同步任务，避免事件循环冲突")
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_sync_in_new_thread)
                result = future.result(timeout=30)  # 30秒超时
                return result

        except concurrent.futures.TimeoutError:
            logger.error(f"[统一新闻工具] ❌ 同步新闻超时（30秒）")
            return False
        except Exception as e:
            logger.error(f"[统一新闻工具] ❌ 同步新闻失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def _get_a_share_news(self, stock_code: str, max_news: int, model_info: str = "") -> str:
        """获取A股新闻"""
        logger.info(f"[统一新闻工具] 获取A股 {stock_code} 新闻")

        # 获取当前日期
        curr_date = datetime.now().strftime("%Y-%m-%d")

        # 优先级0: 从数据库获取新闻（最高优先级）
        try:
            logger.info(f"[统一新闻工具] 🔍 优先从数据库获取 {stock_code} 的新闻...")
            db_news = self._get_news_from_database(stock_code, max_news)
            if db_news:
                logger.info(f"[统一新闻工具] ✅ 数据库新闻获取成功: {len(db_news)} 字符")
                return self._format_news_result(db_news, "数据库缓存", model_info)
            else:
                logger.info(f"[统一新闻工具] ⚠️ 数据库中没有 {stock_code} 的新闻，尝试同步...")

                # 🔥 数据库没有数据时，调用同步服务同步新闻
                try:
                    logger.info(f"[统一新闻工具] 📡 调用同步服务同步 {stock_code} 的新闻...")
                    synced_news = self._sync_news_from_akshare(stock_code, max_news)

                    if synced_news:
                        logger.info(f"[统一新闻工具] ✅ 同步成功，重新从数据库获取...")
                        # 重新从数据库获取
                        db_news = self._get_news_from_database(stock_code, max_news)
                        if db_news:
                            logger.info(f"[统一新闻工具] ✅ 同步后数据库新闻获取成功: {len(db_news)} 字符")
                            return self._format_news_result(db_news, "数据库缓存(新同步)", model_info)
                    else:
                        logger.warning(f"[统一新闻工具] ⚠️ 同步服务未返回新闻数据")

                except Exception as sync_error:
                    logger.warning(f"[统一新闻工具] ⚠️ 同步服务调用失败: {sync_error}")

                logger.info(f"[统一新闻工具] ⚠️ 同步后仍无数据，尝试其他数据源...")
        except Exception as e:
            logger.warning(f"[统一新闻工具] 数据库新闻获取失败: {e}")

        # 优先级1: 东方财富实时新闻
        try:
            if hasattr(self.toolkit, 'get_realtime_stock_news'):
                logger.info(f"[统一新闻工具] 尝试东方财富实时新闻...")
                # 使用LangChain工具的正确调用方式：.invoke()方法和字典参数
                result = self.toolkit.get_realtime_stock_news.invoke({"ticker": stock_code, "curr_date": curr_date})
                
                # 🔍 详细记录东方财富返回的内容
                logger.info(f"[统一新闻工具] 📊 东方财富返回内容长度: {len(result) if result else 0} 字符")
                logger.info(f"[统一新闻工具] 📋 东方财富返回内容预览 (前500字符): {result[:500] if result else 'None'}")
                
                if result and len(result.strip()) > 100 and not self._is_failed_content(result):
                    logger.info(f"[统一新闻工具] ✅ 东方财富新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "东方财富实时新闻", model_info)
                elif result and self._is_failed_content(result):
                    logger.warning(f"[统一新闻工具] ⚠️ 东方财富A股新闻返回失败内容，尝试其他来源")
                else:
                    logger.warning(f"[统一新闻工具] ⚠️ 东方财富新闻内容过短或为空")
        except Exception as e:
            logger.warning(f"[统一新闻工具] 东方财富新闻获取失败: {e}")
        
        # 优先级2: OpenAI全球新闻
        try:
            if hasattr(self.toolkit, 'get_global_news_openai'):
                logger.info(f"[统一新闻工具] 尝试OpenAI全球新闻...")
                # 使用LangChain工具的正确调用方式：.invoke()方法和字典参数
                result = self.toolkit.get_global_news_openai.invoke({"curr_date": curr_date})
                if result and len(result.strip()) > 50 and not self._is_failed_content(result):
                    logger.info(f"[统一新闻工具] ✅ OpenAI新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "OpenAI全球新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] OpenAI新闻获取失败: {e}")

        # 优先级3: Google新闻（中文搜索，放在最后以避免90秒超时影响其他来源）
        try:
            if hasattr(self.toolkit, 'get_google_news'):
                logger.info(f"[统一新闻工具] 尝试Google新闻...")
                query = f"{stock_code} 股票 新闻 财报 业绩"
                # 使用LangChain工具的正确调用方式：.invoke()方法和字典参数
                result = self.toolkit.get_google_news.invoke({"query": query, "curr_date": curr_date})
                if result and len(result.strip()) > 50 and not self._is_failed_content(result):
                    logger.info(f"[统一新闻工具] ✅ Google新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "Google新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] Google新闻获取失败: {e}")
        
        return "❌ 无法获取A股新闻数据，所有新闻源均不可用"
    
    def _get_hk_share_news(self, stock_code: str, max_news: int, model_info: str = "") -> str:
        """获取港股新闻"""
        logger.info(f"[统一新闻工具] 获取港股 {stock_code} 新闻")

        # 获取当前日期
        curr_date = datetime.now().strftime("%Y-%m-%d")

        # 优先级1: 东方财富搜索API（无需API Key，速度快）
        # 港股公司大多在中国大陆知名，用公司中文名搜索效果好
        try:
            hk_cn_name = self._get_hk_stock_cn_name(stock_code)
            result = self._get_us_news_via_eastmoney_search(hk_cn_name or stock_code, max_news)
            if result and len(result.strip()) > 100:
                logger.info(f"[统一新闻工具] ✅ 东方财富搜索港股新闻成功: {len(result)} 字符")
                return self._format_news_result(result, "东方财富搜索(港股)", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] 东方财富搜索港股新闻失败: {e}")

        # 优先级2: 实时新闻（如果支持港股）
        try:
            if hasattr(self.toolkit, 'get_realtime_stock_news'):
                logger.info(f"[统一新闻工具] 尝试实时港股新闻...")
                result = self.toolkit.get_realtime_stock_news.invoke({"ticker": stock_code, "curr_date": curr_date})
                if result and len(result.strip()) > 100 and not self._is_failed_content(result):
                    logger.info(f"[统一新闻工具] ✅ 实时港股新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "实时港股新闻", model_info)
                elif result and self._is_failed_content(result):
                    logger.warning(f"[统一新闻工具] ⚠️ 实时港股新闻返回失败内容，尝试其他来源")
        except Exception as e:
            logger.warning(f"[统一新闻工具] 实时港股新闻获取失败: {e}")

        # 优先级3: OpenAI全球新闻
        try:
            if hasattr(self.toolkit, 'get_global_news_openai'):
                logger.info(f"[统一新闻工具] 尝试OpenAI港股新闻...")
                result = self.toolkit.get_global_news_openai.invoke({"curr_date": curr_date})
                if result and len(result.strip()) > 50 and not self._is_failed_content(result):
                    logger.info(f"[统一新闻工具] ✅ OpenAI港股新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "OpenAI港股新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] OpenAI港股新闻获取失败: {e}")

        # 优先级4: Google新闻（仅当前面来源均失败时尝试）
        try:
            if hasattr(self.toolkit, 'get_google_news'):
                logger.info(f"[统一新闻工具] 尝试Google港股新闻...")
                cn_name = self._get_hk_stock_cn_name(stock_code) or stock_code
                query = f"{cn_name} 港股 新闻"
                result = self.toolkit.get_google_news.invoke({"query": query, "curr_date": curr_date})
                if result and len(result.strip()) > 50 and not self._is_failed_content(result):
                    logger.info(f"[统一新闻工具] ✅ Google港股新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "Google港股新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] Google港股新闻获取失败: {e}")

        return "❌ 无法获取港股新闻数据，所有新闻源均不可用"

    # 常见港股中文名映射（按4位数字代码）
    _HK_STOCK_CN_NAMES = {
        '0700': '腾讯', '700': '腾讯',
        '9988': '阿里巴巴', '3690': '美团', '1024': '快手',
        '2318': '中国平安', '0939': '建设银行', '939': '建设银行',
        '1398': '工商银行', '3988': '中国银行', '0941': '中国移动', '941': '中国移动',
        '2628': '中国人寿', '0883': '中国海洋石油', '883': '中国海洋石油',
        '0857': '中国石油', '857': '中国石油', '0386': '中国石化', '386': '中国石化',
        '1177': '中升控股', '2020': '安踏体育', '9618': '京东',
        '1211': '比亚迪', '0175': '吉利汽车', '175': '吉利汽车',
        '2333': '长城汽车', '02121': '长城汽车', '2121': '长城汽车',
        '0981': '中芯国际', '981': '中芯国际',
        '6690': '海尔智家', '0992': '联想集团', '992': '联想集团',
        '1833': '平安好医生', '0762': '中国联通', '762': '中国联通',
        '0728': '中国电信', '728': '中国电信',
        '1919': '中远海控', '0688': '中国海外发展', '688': '中国海外发展',
        '2899': '紫金矿业', '0358': '江西铜业', '358': '江西铜业',
        '0267': '中信股份', '267': '中信股份',
        '6862': '海底捞', '9961': '携程', '0322': '康师傅', '322': '康师傅',
        '1928': '金沙中国', '1038': '长江基建', '0002': '长江实业', '2': '长江实业',
    }

    def _get_hk_stock_cn_name(self, stock_code: str) -> str:
        """获取港股中文名称（用于东方财富搜索）"""
        # 标准化：去掉前导零但保留原始形式查表
        code = stock_code.strip().lstrip('0') or '0'
        code_padded = stock_code.strip().zfill(4)
        return (self._HK_STOCK_CN_NAMES.get(stock_code.strip()) or
                self._HK_STOCK_CN_NAMES.get(code_padded) or
                self._HK_STOCK_CN_NAMES.get(code) or
                "")
    
    @staticmethod
    def _is_failed_content(content: str) -> bool:
        """检查内容是否为失败/错误消息，而非真实新闻数据"""
        failure_markers = [
            "实时新闻获取失败",
            "无法获取美股新闻数据",
            "无法获取港股新闻数据",
            "无法获取A股新闻数据",
            "所有新闻源均不可用",
            "新闻获取失败",
            "❌ 无法获取",
        ]
        return any(marker in content for marker in failure_markers)

    def _get_us_share_news(self, stock_code: str, max_news: int, model_info: str = "") -> str:
        """获取美股新闻"""
        logger.info(f"[统一新闻工具] 获取美股 {stock_code} 新闻")
        # 调试日志：配置、API Key、数据库状态
        try:
            import os
            from tradingagents.config.config_manager import config_manager
            config_dir = str(getattr(config_manager, 'config_dir', 'N/A'))
            data_dir = config_manager.get_data_dir() if hasattr(config_manager, 'get_data_dir') else 'N/A'
            finnhub_ok = bool(os.getenv("FINNHUB_API_KEY"))
            alpha_ok = bool(os.getenv("ALPHA_VANTAGE_API_KEY"))
            logger.info(f"[统一新闻工具] config_dir={config_dir}, data_dir={data_dir}, FINNHUB_API_KEY={'已加载' if finnhub_ok else '未加载'}, ALPHA_VANTAGE_API_KEY={'已加载' if alpha_ok else '未加载'}")
        except Exception as e:
            logger.warning(f"[统一新闻工具] 配置/API读取: {e}")
        try:
            from tradingagents.config.database_manager import get_db_client
            client = get_db_client()
            logger.info(f"[统一新闻工具] 数据库连接: {'已就绪' if client else '未连接'}")
        except Exception as e:
            logger.warning(f"[统一新闻工具] 数据库状态: {e}")
        
        # 获取当前日期
        curr_date = datetime.now().strftime("%Y-%m-%d")
        import os as _os
        _finnhub_key = _os.getenv("FINNHUB_API_KEY", "").strip()
        _alpha_key = _os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()

        # 优先级1: 东方财富搜索API（无需API Key，速度快）
        try:
            result = self._get_us_news_via_eastmoney_search(stock_code, max_news)
            if result and len(result.strip()) > 100:
                logger.info(f"[统一新闻工具] ✅ 东方财富搜索美股新闻成功: {len(result)} 字符")
                return self._format_news_result(result, "东方财富搜索(美股)", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] 东方财富搜索美股新闻失败: {e}")

        # 优先级2: 实时新闻聚合器（仅当配置了API Key时尝试，否则跳过以避免90秒超时）
        if _finnhub_key or _alpha_key:
            try:
                if hasattr(self.toolkit, 'get_realtime_stock_news'):
                    logger.info(f"[统一新闻工具] 尝试实时新闻聚合器（Finnhub/Alpha Vantage）...")
                    result = self.toolkit.get_realtime_stock_news.invoke({
                        "ticker": stock_code,
                        "curr_date": curr_date
                    })
                    if result and len(result.strip()) > 100 and not self._is_failed_content(result):
                        logger.info(f"[统一新闻工具] ✅ 实时新闻聚合器获取成功: {len(result)} 字符")
                        return self._format_news_result(result, "实时新闻（Finnhub/Alpha Vantage）", model_info)
            except Exception as e:
                logger.warning(f"[统一新闻工具] 实时新闻聚合器获取失败: {e}")
        else:
            logger.info(f"[统一新闻工具] 跳过Finnhub/Alpha Vantage（未配置API Key）")

        # 优先级3: OpenAI全球新闻
        try:
            if hasattr(self.toolkit, 'get_global_news_openai'):
                logger.info(f"[统一新闻工具] 尝试OpenAI美股新闻...")
                result = self.toolkit.get_global_news_openai.invoke({"curr_date": curr_date})
                if result and len(result.strip()) > 50 and not self._is_failed_content(result):
                    logger.info(f"[统一新闻工具] ✅ OpenAI美股新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "OpenAI美股新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] OpenAI美股新闻获取失败: {e}")

        # 优先级4: Google新闻（英文搜索）
        try:
            if hasattr(self.toolkit, 'get_google_news'):
                logger.info(f"[统一新闻工具] 尝试Google美股新闻...")
                query = f"{stock_code} stock news earnings financial"
                result = self.toolkit.get_google_news.invoke({"query": query, "curr_date": curr_date})
                if result and len(result.strip()) > 50 and not self._is_failed_content(result):
                    logger.info(f"[统一新闻工具] ✅ Google美股新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "Google美股新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] Google美股新闻获取失败: {e}")

        # 优先级5: FinnHub新闻（本地文件，需预下载；参数为 ticker, start_date, end_date）
        try:
            if hasattr(self.toolkit, 'get_finnhub_news'):
                logger.info(f"[统一新闻工具] 尝试FinnHub本地新闻...")
                from datetime import timedelta
                end_dt = datetime.strptime(curr_date, "%Y-%m-%d")
                start_dt = end_dt - timedelta(days=7)
                result = self.toolkit.get_finnhub_news.invoke({
                    "ticker": stock_code,
                    "start_date": start_dt.strftime("%Y-%m-%d"),
                    "end_date": curr_date
                })
                if result and len(result.strip()) > 50 and "⚠️ 无法获取" not in result:
                    logger.info(f"[统一新闻工具] ✅ FinnHub美股新闻获取成功: {len(result)} 字符")
                    return self._format_news_result(result, "FinnHub美股新闻", model_info)
        except Exception as e:
            logger.warning(f"[统一新闻工具] FinnHub美股新闻获取失败: {e}")

        return "❌ 无法获取美股新闻数据，所有新闻源均不可用"

    # 常见美股中文名映射表（用于东方财富搜索）
    _US_STOCK_CN_NAMES = {
        'AAPL': '苹果公司', 'TSLA': '特斯拉', 'GOOGL': '谷歌', 'GOOG': '谷歌',
        'META': 'Meta', 'AMZN': '亚马逊', 'MSFT': '微软', 'NVDA': '英伟达',
        'NFLX': '奈飞', 'BABA': '阿里巴巴', 'JD': '京东', 'PDD': '拼多多',
        'NIO': '蔚来汽车', 'XPEV': '小鹏汽车', 'LI': '理想汽车',
        'BIDU': '百度', 'TCEHY': '腾讯', 'JPM': '摩根大通', 'BAC': '美国银行',
        'WMT': '沃尔玛', 'DIS': '迪士尼', 'INTC': '英特尔', 'AMD': 'AMD',
        'QCOM': '高通', 'CRM': 'Salesforce', 'ORCL': '甲骨文',
        'UBER': 'Uber', 'ABNB': 'Airbnb', 'PYPL': 'PayPal', 'COIN': 'Coinbase',
        'V': 'Visa', 'MA': '万事达', 'GS': '高盛', 'MS': '摩根士丹利',
        'SHOP': 'Shopify', 'SNOW': 'Snowflake', 'PLTR': 'Palantir',
        'ARM': 'ARM', 'AVGO': '博通', 'TSM': '台积电',
        'SMCI': '超微电脑', 'MSTR': 'MicroStrategy',
    }

    def _get_us_news_via_eastmoney_search(self, ticker: str, max_news: int = 10) -> str:
        """通过东方财富搜索API获取美股相关中文新闻（无需API Key）"""
        import json
        import time

        ticker_clean = ticker.upper().strip()
        cn_name = self._US_STOCK_CN_NAMES.get(ticker_clean, "")
        # 搜索关键词列表：优先用中文名，其次用英文代码
        keywords = []
        if cn_name:
            keywords.append(cn_name)
        keywords.append(ticker_clean)

        url = "https://search-api-web.eastmoney.com/search/jsonp"
        headers = {
            "Referer": "https://so.eastmoney.com/news/s",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
        }

        for keyword in keywords:
            try:
                param = {
                    "uid": "",
                    "keyword": keyword,
                    "type": ["cmsArticleWebOld"],
                    "client": "web",
                    "clientType": "web",
                    "clientVersion": "curr",
                    "param": {
                        "cmsArticleWebOld": {
                            "searchScope": "default",
                            "sort": "pubtime",
                            "pageIndex": 1,
                            "pageSize": min(int(max_news), 20),
                            "preTag": "<em>",
                            "postTag": "</em>"
                        }
                    }
                }
                params = {
                    "cb": f"jQuery{int(time.time() * 1000)}",
                    "param": json.dumps(param, ensure_ascii=False),
                    "_": str(int(time.time() * 1000))
                }

                try:
                    from curl_cffi import requests as curl_requests
                    response = curl_requests.get(url, params=params, timeout=10,
                                                 impersonate="chrome120", headers=headers)
                except ImportError:
                    import requests as _req
                    response = _req.get(url, params=params, timeout=10, headers=headers)

                if response.status_code != 200:
                    logger.warning(f"[统一新闻工具] 东方财富搜索'{keyword}'返回状态码: {response.status_code}")
                    continue

                text = response.text
                if text.startswith("jQuery"):
                    text = text[text.find("(") + 1:text.rfind(")")]

                data = json.loads(text)
                if "result" not in data or "cmsArticleWebOld" not in data["result"]:
                    logger.warning(f"[统一新闻工具] 东方财富搜索'{keyword}'数据结构异常")
                    continue

                raw_articles = data["result"]["cmsArticleWebOld"]
                articles = raw_articles.get("list", []) if isinstance(raw_articles, dict) else raw_articles

                if not articles:
                    logger.info(f"[统一新闻工具] 东方财富搜索'{keyword}'无结果，尝试下一关键词")
                    continue

                news_items = []
                for i, article in enumerate(articles[:max_news]):
                    title = article.get("title", "").replace("<em>", "").replace("</em>", "").strip()
                    content = article.get("content", "").replace("<em>", "").replace("</em>", "").strip()
                    pub_time = article.get("date", "")
                    source = article.get("source", "东方财富网")
                    if title:
                        news_items.append(f"[{i+1}] {pub_time} | {source}")
                        news_items.append(f"    标题: {title}")
                        if content:
                            news_items.append(f"    摘要: {content[:300]}")
                        news_items.append("")

                if news_items:
                    header = f"=== 东方财富 - {ticker_clean}({cn_name or ticker_clean}) 相关新闻 ===\n"
                    logger.info(f"[统一新闻工具] 东方财富搜索'{keyword}'获取到 {len(articles)} 条新闻")
                    return header + "\n".join(news_items)

            except Exception as e:
                logger.warning(f"[统一新闻工具] 东方财富搜索'{keyword}'失败: {e}")
                continue

        return ""
    
    def _format_news_result(self, news_content: str, source: str, model_info: str = "") -> str:
        """格式化新闻结果"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 🔍 添加调试日志：打印原始新闻内容
        logger.info(f"[统一新闻工具] 📋 原始新闻内容预览 (前500字符): {news_content[:500]}")
        logger.info(f"[统一新闻工具] 📊 原始内容长度: {len(news_content)} 字符")
        
        # 检测是否为Google/Gemini模型
        is_google_model = any(keyword in model_info.lower() for keyword in ['google', 'gemini', 'gemma'])
        original_length = len(news_content)
        google_control_applied = False
        
        # 🔍 添加Google模型检测日志
        if is_google_model:
            logger.info(f"[统一新闻工具] 🤖 检测到Google模型，启用特殊处理")
        
        # 对Google模型进行特殊的长度控制
        if is_google_model and len(news_content) > 5000:  # 降低阈值到5000字符
            logger.warning(f"[统一新闻工具] 🔧 检测到Google模型，新闻内容过长({len(news_content)}字符)，进行长度控制...")
            
            # 更严格的长度控制策略
            lines = news_content.split('\n')
            important_lines = []
            char_count = 0
            target_length = 3000  # 目标长度设为3000字符
            
            # 第一轮：优先保留包含关键词的重要行
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # 检查是否包含重要关键词
                important_keywords = ['股票', '公司', '财报', '业绩', '涨跌', '价格', '市值', '营收', '利润', 
                                    '增长', '下跌', '上涨', '盈利', '亏损', '投资', '分析', '预期', '公告']
                
                is_important = any(keyword in line for keyword in important_keywords)
                
                if is_important and char_count + len(line) < target_length:
                    important_lines.append(line)
                    char_count += len(line)
                elif not is_important and char_count + len(line) < target_length * 0.7:  # 非重要内容更严格限制
                    important_lines.append(line)
                    char_count += len(line)
                
                # 如果已达到目标长度，停止添加
                if char_count >= target_length:
                    break
            
            # 如果提取的重要内容仍然过长，进行进一步截断
            if important_lines:
                processed_content = '\n'.join(important_lines)
                if len(processed_content) > target_length:
                    processed_content = processed_content[:target_length] + "...(内容已智能截断)"
                
                news_content = processed_content
                google_control_applied = True
                logger.info(f"[统一新闻工具] ✅ Google模型智能长度控制完成，从{original_length}字符压缩至{len(news_content)}字符")
            else:
                # 如果没有重要行，直接截断到目标长度
                news_content = news_content[:target_length] + "...(内容已强制截断)"
                google_control_applied = True
                logger.info(f"[统一新闻工具] ⚠️ Google模型强制截断至{target_length}字符")
        
        # 计算最终的格式化结果长度，确保总长度合理
        base_format_length = 300  # 格式化模板的大概长度
        if is_google_model and (len(news_content) + base_format_length) > 4000:
            # 如果加上格式化后仍然过长，进一步压缩新闻内容
            max_content_length = 3500
            if len(news_content) > max_content_length:
                news_content = news_content[:max_content_length] + "...(已优化长度)"
                google_control_applied = True
                logger.info(f"[统一新闻工具] 🔧 Google模型最终长度优化，内容长度: {len(news_content)}字符")
        
        is_failed_content = ("实时新闻获取失败" in news_content) or ("❌" in news_content)
        status_text = "获取失败" if is_failed_content else "成功获取"

        formatted_result = f"""
=== 📰 新闻数据来源: {source} ===
获取时间: {timestamp}
数据长度: {len(news_content)} 字符
{f"模型类型: {model_info}" if model_info else ""}
{f"🔧 Google模型长度控制已应用 (原长度: {original_length} 字符)" if google_control_applied else ""}

=== 📋 新闻内容 ===
{news_content}

=== ✅ 数据状态 ===
状态: {status_text}
来源: {source}
时间戳: {timestamp}
"""
        return formatted_result.strip()


def create_unified_news_tool(toolkit):
    """创建统一新闻工具函数"""
    analyzer = UnifiedNewsAnalyzer(toolkit)
    
    def get_stock_news_unified(stock_code: str, max_news: int = 100, model_info: str = ""):
        """
        统一新闻获取工具
        
        Args:
            stock_code (str): 股票代码 (支持A股如000001、港股如0700.HK、美股如AAPL)
            max_news (int): 最大新闻数量，默认100
            model_info (str): 当前使用的模型信息，用于特殊处理
        
        Returns:
            str: 格式化的新闻内容
        """
        if not stock_code:
            return "❌ 错误: 未提供股票代码"
        
        return analyzer.get_stock_news_unified(stock_code, max_news, model_info)
    
    # 设置工具属性
    get_stock_news_unified.name = "get_stock_news_unified"
    get_stock_news_unified.description = """
统一新闻获取工具 - 根据股票代码自动获取相应市场的新闻

功能:
- 自动识别股票类型（A股/港股/美股）
- 根据股票类型选择最佳新闻源
- A股: 优先东方财富 -> Google中文 -> OpenAI
- 港股: 优先Google -> OpenAI -> 实时新闻
- 美股: 优先OpenAI -> Google英文 -> FinnHub
- 返回格式化的新闻内容
- 支持Google模型的特殊长度控制
"""
    
    return get_stock_news_unified