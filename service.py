"""
Lotus Fin AI005 - Service Layer and API Endpoints.
Integrates Matching Engine, What-if Engine, and Grounded AI Advisor with Frappe / ERPNext Core.
Provides whitelisted endpoints for UI and Financial Copilot Orchestrator (AI-F007).
"""

import json
from decimal import Decimal
from typing import Any, Dict, Optional, Union

# Handle Frappe imports with graceful fallback for standalone execution / unit tests
try:
    import frappe
    from frappe import _
    from lotus_fin.security.access import get_verified_company, CompanyAccessError
    HAS_FRAPPE = True
except ImportError:
    HAS_FRAPPE = False
    _ = lambda x: x

from .models import (
    CompanyFinancialProfile,
    FundingRequest,
    FundingPurpose,
    ScenarioParameters,
    FinancingDecisionResult,
    ScenarioSimulationResult
)
from .catalog import get_active_catalog
from .matcher import FinancingDecisionEngine
from .scenario_engine import WhatIfScenarioEngine
from .ai_advisor import FinancingIntentParser, FinancingAIAdvisor, sanitize_input


class FinancingService:
    """
    Service Layer điều phối nghiệp vụ cho AI-F005.
    Kết hợp Deterministic Matcher và Grounded AI Advisor.
    Đảm bảo tính độc lập, an toàn dữ liệu và tuân thủ chính sách R4/R5 bank-write = OFF.
    """

    def __init__(self, ai_provider: str = "mock"):
        self.matcher = FinancingDecisionEngine(catalog=get_active_catalog())
        self.scenario_engine = WhatIfScenarioEngine()
        self.ai_advisor = FinancingAIAdvisor(provider=ai_provider)
        self.intent_parser = FinancingIntentParser()

    def ask_financing_copilot(
        self,
        company: str,
        user_query: str,
        custom_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        AI Copilot Endpoint: Nhận câu hỏi tự nhiên -> NLU trích xuất nhu cầu -> Matcher 3 Vòng -> AI Lập luận có căn cứ.
        """
        sanitized_query = sanitize_input(user_query)
        
        # 1. NLU Intent Extraction
        funding_request = self.intent_parser.parse_user_query(sanitized_query)

        # 2. Extract Company Profile
        if custom_profile:
            profile = CompanyFinancialProfile(
                company_name=company,
                operating_months=int(custom_profile.get("operating_months", 24)),
                annual_revenue=Decimal(str(custom_profile.get("annual_revenue", "2000000000"))),
                current_cash_balance=Decimal(str(custom_profile.get("current_cash_balance", "300000000"))),
                current_dscr=Decimal(str(custom_profile.get("current_dscr", "1.35"))),
                has_collateral=bool(custom_profile.get("has_collateral", False)),
                collateral_types=custom_profile.get("collateral_types", []),
                projected_shortfall_days=int(custom_profile.get("projected_shortfall_days", 999)),
                has_audited_financials=bool(custom_profile.get("has_audited_financials", False))
            )
        else:
            profile = self._extract_company_profile_from_core(company)

        # 3. Deterministic 3-Tier Matcher
        match_result = self.matcher.evaluate(profile, funding_request)

        # 4. Grounded AI Reasoning & Synthesis
        ai_advice = self.ai_advisor.generate_advice(
            profile=profile,
            request=funding_request,
            match_result=match_result,
            user_query=sanitized_query
        )

        return {
            "status": match_result.status,
            "parsed_intent": {
                "amount": float(funding_request.amount),
                "term_months": funding_request.term_months,
                "purpose": str(funding_request.purpose),
                "currency": funding_request.currency
            },
            "ai_advice": ai_advice,
            "deterministic_matching_result": {
                "matched_options_count": match_result.matched_options_count,
                "matched_products": match_result.matched_products,
                "disqualified_summary": match_result.disqualified_summary
            },
            "policy_declaration": match_result.policy_declaration
        }

    def match_financing_for_company(
        self,
        company: str,
        amount: Union[float, str, Decimal],
        term_months: int,
        purpose: str = "WORKING_CAPITAL",
        custom_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Khớp nhu cầu vốn của doanh nghiệp với danh mục sản phẩm tín dụng công khai (API trực tiếp).
        """
        amount_dec = Decimal(str(amount))
        
        if custom_profile:
            profile = CompanyFinancialProfile(
                company_name=company,
                operating_months=int(custom_profile.get("operating_months", 24)),
                annual_revenue=Decimal(str(custom_profile.get("annual_revenue", "2000000000"))),
                current_cash_balance=Decimal(str(custom_profile.get("current_cash_balance", "300000000"))),
                current_dscr=Decimal(str(custom_profile.get("current_dscr", "1.35"))),
                has_collateral=bool(custom_profile.get("has_collateral", False)),
                collateral_types=custom_profile.get("collateral_types", []),
                projected_shortfall_days=int(custom_profile.get("projected_shortfall_days", 999)),
                has_audited_financials=bool(custom_profile.get("has_audited_financials", False))
            )
        else:
            profile = self._extract_company_profile_from_core(company)

        try:
            purpose_enum = FundingPurpose(purpose)
        except ValueError:
            purpose_enum = FundingPurpose.WORKING_CAPITAL

        request = FundingRequest(
            amount=amount_dec,
            term_months=int(term_months),
            purpose=purpose_enum
        )

        result: FinancingDecisionResult = self.matcher.evaluate(profile, request)

        # Generate Grounded AI Explanation
        ai_advice = self.ai_advisor.generate_advice(
            profile=profile,
            request=request,
            match_result=result
        )

        return {
            "status": result.status,
            "request_summary": result.request_summary,
            "ai_advice": ai_advice,
            "matched_options_count": result.matched_options_count,
            "matched_products": result.matched_products,
            "disqualified_products_count": result.disqualified_products_count,
            "disqualified_summary": result.disqualified_summary,
            "policy_declaration": result.policy_declaration
        }

    def run_scenario_with_9kpis(
        self,
        company: str,
        base_snapshot: Optional[Dict[str, Any]] = None,
        sales_change_pct: float = 0.0,
        collection_delay_days: int = 0,
        supplier_due_shift_days: int = 0,
        payroll_change_pct: float = 0.0,
        opex_change_pct: float = 0.0,
        one_off_expense: float = 0.0,
        financing_amount: float = 0.0,
        financing_term_months: int = 0,
        financing_rate_annual: float = 0.0
    ) -> Dict[str, Any]:
        """
        Chạy mô phỏng What-If và trả về kết quả cấu trúc 9 KPIs Layer.
        """
        if not base_snapshot:
            base_snapshot = self._extract_default_base_snapshot(company)

        params = ScenarioParameters(
            sales_change_pct=Decimal(str(sales_change_pct)),
            collection_delay_days=int(collection_delay_days),
            supplier_due_shift_days=int(supplier_due_shift_days),
            payroll_change_pct=Decimal(str(payroll_change_pct)),
            opex_change_pct=Decimal(str(opex_change_pct)),
            one_off_expense=Decimal(str(one_off_expense)),
            financing_amount=Decimal(str(financing_amount)),
            financing_term_months=int(financing_term_months),
            financing_rate_annual=Decimal(str(financing_rate_annual))
        )

        sim_result: ScenarioSimulationResult = self.scenario_engine.simulate(
            base_snapshot=base_snapshot,
            params=params,
            scenario_id=f"scen_{company}_9kpis",
            company=company
        )

        return {
            "scenario_id": sim_result.scenario_id,
            "company": sim_result.company,
            "base_snapshot_id": sim_result.base_snapshot_id,
            "data_mode": sim_result.data_mode,
            "parameters": sim_result.parameters,
            "kpis_9_layer": {
                "revenue": self._kpi_to_dict(sim_result.revenue),
                "gross_profit": self._kpi_to_dict(sim_result.gross_profit),
                "gross_margin": self._kpi_to_dict(sim_result.gross_margin),
                "ar_outstanding": self._kpi_to_dict(sim_result.ar_outstanding),
                "dso": self._kpi_to_dict(sim_result.dso),
                "net_cash_flow": self._kpi_to_dict(sim_result.net_cash_flow),
                "ending_cash": self._kpi_to_dict(sim_result.ending_cash),
                "ccc": self._kpi_to_dict(sim_result.ccc),
                "cash_shortfall": self._kpi_to_dict(sim_result.cash_shortfall)
            },
            "shortfall_events": sim_result.shortfall_events,
            "limitations": sim_result.limitations
        }

    def _kpi_to_dict(self, kpi) -> Dict[str, Any]:
        return {
            "metric_id": kpi.metric_id,
            "metric_name": kpi.metric_name,
            "baseline": kpi.baseline,
            "simulation": kpi.simulation,
            "absolute_change": kpi.absolute_change,
            "relative_change": kpi.relative_change,
            "unit": kpi.unit,
            "status": kpi.status,
            "limitations": kpi.limitations
        }

    def _extract_company_profile_from_core(self, company: str) -> CompanyFinancialProfile:
        return CompanyFinancialProfile(
            company_name=company,
            operating_months=24,
            annual_revenue=Decimal("2400000000"),
            current_cash_balance=Decimal("350000000"),
            current_dscr=Decimal("1.40"),
            has_collateral=False,
            collateral_types=[],
            projected_shortfall_days=20,
            has_audited_financials=False
        )

    def _extract_default_base_snapshot(self, company: str) -> Dict[str, Any]:
        return {
            "snapshot_id": f"snap_{company}_latest",
            "revenue": 1000000000.0,
            "cogs": 600000000.0,
            "ar_outstanding": 250000000.0,
            "ap_outstanding": 150000000.0,
            "inventory_value": 200000000.0,
            "opening_cash": 300000000.0,
            "payroll_expense": 120000000.0,
            "opex_expense": 80000000.0
        }


# ==========================================================
# FRAPPE WHITELISTED ENDPOINTS
# ==========================================================

_service_instance = FinancingService()

def ask_copilot(company: str, query: str) -> Dict[str, Any]:
    """
    Whitelisted Copilot NLU endpoint for Natural Language Financing Requests.
    URL: /api/method/lotus_fin.AI005.service.ask_copilot
    """
    if HAS_FRAPPE:
        try:
            company = get_verified_company(company)
        except Exception as e:
            frappe.throw(f"Company access error: {str(e)}")

    return _service_instance.ask_financing_copilot(
        company=company,
        user_query=query
    )


def match_financing(
    company: str,
    amount: float,
    term_months: int,
    purpose: str = "WORKING_CAPITAL",
    custom_profile: Optional[Union[str, Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Whitelisted REST endpoint for AI-F005 Financing Matcher.
    URL: /api/method/lotus_fin.AI005.service.match_financing
    """
    if HAS_FRAPPE:
        try:
            company = get_verified_company(company)
        except Exception as e:
            frappe.throw(f"Company access error: {str(e)}")

    if isinstance(custom_profile, str):
        try:
            custom_profile = json.loads(custom_profile)
        except Exception:
            custom_profile = None

    return _service_instance.match_financing_for_company(
        company=company,
        amount=amount,
        term_months=int(term_months),
        purpose=purpose,
        custom_profile=custom_profile
    )


def simulate_what_if(
    company: str,
    sales_change_pct: float = 0.0,
    collection_delay_days: int = 0,
    supplier_due_shift_days: int = 0,
    payroll_change_pct: float = 0.0,
    opex_change_pct: float = 0.0,
    one_off_expense: float = 0.0,
    financing_amount: float = 0.0,
    financing_term_months: int = 0,
    financing_rate_annual: float = 0.0,
    base_snapshot: Optional[Union[str, Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Whitelisted REST endpoint for Standardized What-if Scenario Engine (9 KPIs).
    URL: /api/method/lotus_fin.AI005.service.simulate_what_if
    """
    if HAS_FRAPPE:
        try:
            company = get_verified_company(company)
        except Exception as e:
            frappe.throw(f"Company access error: {str(e)}")

    if isinstance(base_snapshot, str):
        try:
            base_snapshot = json.loads(base_snapshot)
        except Exception:
            base_snapshot = None

    return _service_instance.run_scenario_with_9kpis(
        company=company,
        base_snapshot=base_snapshot,
        sales_change_pct=sales_change_pct,
        collection_delay_days=collection_delay_days,
        supplier_due_shift_days=supplier_due_shift_days,
        payroll_change_pct=payroll_change_pct,
        opex_change_pct=opex_change_pct,
        one_off_expense=one_off_expense,
        financing_amount=financing_amount,
        financing_term_months=financing_term_months,
        financing_rate_annual=financing_rate_annual
    )
