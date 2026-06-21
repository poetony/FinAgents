"""
智能体适配器

将现有的函数式智能体适配为 BaseAgent 子类
"""

import logging
from .legacy_adapter import LegacyAgentAdapter

logger = logging.getLogger(__name__)
from .market_analyst import MarketAnalystAgent
from .market_analyst_v2 import MarketAnalystV2
from .news_analyst import NewsAnalystAgent
from .fundamentals_analyst import FundamentalsAnalystAgent
from .fundamentals_analyst_v2 import FundamentalsAnalystAgentV2
from .social_analyst import SocialMediaAnalystAgent
from .sector_analyst import SectorAnalystAgent
from .index_analyst import IndexAnalystAgent

# v2.0 基于基类的Agent
from .bull_researcher_v2 import BullResearcherV2
from .bear_researcher_v2 import BearResearcherV2
from .research_manager_v2 import ResearchManagerV2
from .risk_manager_v2 import RiskManagerV2
from .trader_v2 import TraderV2
from .news_analyst_v2 import NewsAnalystV2
from .social_analyst_v2 import SocialMediaAnalystV2
from .sector_analyst_v2 import SectorAnalystV2
from .index_analyst_v2 import IndexAnalystV2
from .risky_analyst_v2 import RiskyAnalystV2
from .safe_analyst_v2 import SafeAnalystV2
from .neutral_analyst_v2 import NeutralAnalystV2

# 复盘相关智能体 (v1 & v2)
from .review import (
    # v1.0
    TimingAnalystAgent,
    PositionAnalystAgent,
    EmotionAnalystAgent,
    AttributionAnalystAgent,
    ReviewManagerAgent,
    # v2.0
    TimingAnalystV2,
    PositionAnalystV2,
    EmotionAnalystV2,
    AttributionAnalystV2,
    ReviewManagerV2,
)

# 持仓分析相关智能体 (v1 & v2)
from .position import (
    # v1.0
    TechnicalAnalystAgent,
    FundamentalAnalystAgent,
    RiskAssessorAgent,
    ActionAdvisorAgent,
    # v2.0
    TechnicalAnalystV2,
    FundamentalAnalystV2,
    RiskAssessorV2,
    ActionAdvisorV2,
)

__all__ = [
    "LegacyAgentAdapter",
    "MarketAnalystAgent",
    "MarketAnalystV2",
    "NewsAnalystAgent",
    "FundamentalsAnalystAgent",
    "FundamentalsAnalystAgentV2",
    "SocialMediaAnalystAgent",
    "SectorAnalystAgent",
    "IndexAnalystAgent",
    # v2.0 基于基类的Agent
    "BullResearcherV2",
    "BearResearcherV2",
    "ResearchManagerV2",
    "RiskManagerV2",
    "TraderV2",
    "NewsAnalystV2",
    "SocialMediaAnalystV2",
    "SectorAnalystV2",
    "IndexAnalystV2",
    # 复盘相关 (v1)
    "TimingAnalystAgent",
    "PositionAnalystAgent",
    "EmotionAnalystAgent",
    "AttributionAnalystAgent",
    "ReviewManagerAgent",
    # 复盘相关 (v2)
    "TimingAnalystV2",
    "PositionAnalystV2",
    "EmotionAnalystV2",
    "AttributionAnalystV2",
    "ReviewManagerV2",
    # 持仓分析相关 (v1)
    "TechnicalAnalystAgent",
    "FundamentalAnalystAgent",
    "RiskAssessorAgent",
    "ActionAdvisorAgent",
    # 持仓分析相关 (v2)
    "TechnicalAnalystV2",
    "FundamentalAnalystV2",
    "RiskAssessorV2",
    "ActionAdvisorV2",
]
