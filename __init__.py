"""
Lotus Fin AI005 Package.
Includes:
- AI-F005 Financing Decision Support (Deterministic 3-Tier Matcher + Grounded AI Advisor)
- NLU Natural Language Intent Parser for SME Financing Requests
- Standardized What-if Scenario Simulation Engine with 9 KPIs Layer
"""

from .models import (
    FinancingProduct,
    CompanyFinancialProfile,
    FundingRequest,
    FundingPurpose,
    ProductType,
    RateType,
    ScoreBreakdown,
    MatchedOption,
    DisqualifiedOption,
    FinancingDecisionResult,
    KPIValue,
    ScenarioParameters,
    ScenarioSimulationResult,
    ShortfallEvent
)
from .catalog import get_catalog, get_active_catalog, DEFAULT_FINANCING_CATALOG
from .matcher import FinancingDecisionEngine
from .scenario_engine import WhatIfScenarioEngine
from .ai_advisor import FinancingIntentParser, FinancingAIAdvisor, sanitize_input
from .service import FinancingService, match_financing, simulate_what_if, ask_copilot

__all__ = [
    "FinancingProduct",
    "CompanyFinancialProfile",
    "FundingRequest",
    "FundingPurpose",
    "ProductType",
    "RateType",
    "ScoreBreakdown",
    "MatchedOption",
    "DisqualifiedOption",
    "FinancingDecisionResult",
    "KPIValue",
    "ScenarioParameters",
    "ScenarioSimulationResult",
    "ShortfallEvent",
    "get_catalog",
    "get_active_catalog",
    "DEFAULT_FINANCING_CATALOG",
    "FinancingDecisionEngine",
    "WhatIfScenarioEngine",
    "FinancingIntentParser",
    "FinancingAIAdvisor",
    "FinancingService",
    "match_financing",
    "simulate_what_if",
    "ask_copilot"
]
