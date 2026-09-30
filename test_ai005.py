"""
Unit tests for AI005 - Financing Decision Support & 9 KPIs What-If Engine.
Verifies:
1. NLU Intent Extraction from natural Vietnamese / English queries.
2. Grounded AI Advisor reasoning and trade-off synthesis.
3. 3-Tier Matching Engine (Eligibility filters, 100-pt scoring, gap analysis).
4. What-If Scenario Engine (9 KPIs Layer precision, shortfall detection, Decimal calculations).
5. Fail-safe edge cases & Policy invariants (R4/R5 bank-write = OFF, data_mode = simulation).
"""

import unittest
from decimal import Decimal
from lotus_fin.AI005.models import (
    CompanyFinancialProfile,
    FundingRequest,
    FundingPurpose,
    ScenarioParameters
)
from lotus_fin.AI005.matcher import FinancingDecisionEngine
from lotus_fin.AI005.scenario_engine import WhatIfScenarioEngine
from lotus_fin.AI005.catalog import get_catalog
from lotus_fin.AI005.service import FinancingService
from lotus_fin.AI005.ai_advisor import FinancingIntentParser, FinancingAIAdvisor


class TestAI005FinancingAndScenario(unittest.TestCase):

    def setUp(self):
        self.catalog = get_catalog()
        self.matcher = FinancingDecisionEngine(self.catalog)
        self.scenario_engine = WhatIfScenarioEngine(period_days=90, safety_cash_buffer=Decimal("50000000"))
        self.service = FinancingService(ai_provider="mock")
        self.intent_parser = FinancingIntentParser()
        self.ai_advisor = FinancingAIAdvisor(provider="mock")

    # ==============================================================
    # 1. TEST NLU INTENT EXTRACTION & GROUNDED AI ADVISOR
    # ==============================================================

    def test_nlu_intent_extraction_vietnamese(self):
        """Test AI NLU bóc tách chính xác số tiền, kỳ hạn và mục đích từ ngôn ngữ tự nhiên."""
        query = "Công ty tôi cần vay 500 triệu trong 12 tháng để bổ sung vốn lưu động do khách hàng chậm thanh toán"
        req = self.intent_parser.parse_user_query(query)

        self.assertEqual(req.amount, Decimal("500000000"))
        self.assertEqual(req.term_months, 12)
        self.assertEqual(req.purpose, FundingPurpose.INVOICE_RECOVERY)

        # Test query với đơn vị tỷ và thiết bị
        query2 = "Cần vay 1.5 tỷ thời hạn 2 năm mua máy móc thiết bị nhà xưởng"
        req2 = self.intent_parser.parse_user_query(query2)
        self.assertEqual(req2.amount, Decimal("1500000000"))
        self.assertEqual(req2.term_months, 24)
        self.assertEqual(req2.purpose, FundingPurpose.EQUIPMENT)

    def test_grounded_ai_advisor_synthesis(self):
        """Test AI Advisor sinh báo cáo tư vấn có căn cứ, bao gồm executive_summary, trade-offs và cashflow warning."""
        profile = CompanyFinancialProfile(
            company_name="An Phu Trading Ltd",
            operating_months=24,
            annual_revenue=Decimal("2000000000"),
            current_cash_balance=Decimal("250000000"),
            current_dscr=Decimal("1.45"),
            has_collateral=False,
            projected_shortfall_days=10
        )
        request = FundingRequest(
            amount=Decimal("500000000"),
            term_months=12,
            purpose=FundingPurpose.WORKING_CAPITAL
        )

        match_result = self.matcher.evaluate(profile, request)
        advice = self.ai_advisor.generate_advice(
            profile=profile,
            request=request,
            match_result=match_result,
            user_query="Tư vấn gói vay 500tr"
        )

        self.assertEqual(advice["status"], "SUCCESS")
        self.assertIn("executive_summary", advice)
        self.assertIn("top_recommendation", advice)
        self.assertIn("tradeoff_comparison", advice)
        self.assertIn("cashflow_impact_warning", advice)
        self.assertIn("actionable_next_steps", advice)
        self.assertEqual(advice["policy_compliance"]["bank_write_status"], "OFF (Read-only simulation)")

    def test_copilot_end_to_end_workflow(self):
        """Test toàn bộ luồng Copilot: User hỏi tự nhiên -> NLU -> Matcher -> AI Advisor."""
        copilot_response = self.service.ask_financing_copilot(
            company="An Phu Trading Ltd",
            user_query="Chúng tôi muốn vay 300 triệu trong 6 tháng để chi trả lương và nhập hàng"
        )

        self.assertEqual(copilot_response["status"], "SUCCESS")
        self.assertEqual(copilot_response["parsed_intent"]["amount"], 300000000.0)
        self.assertEqual(copilot_response["parsed_intent"]["term_months"], 6)
        self.assertIn("ai_advice", copilot_response)
        self.assertGreater(len(copilot_response["deterministic_matching_result"]["matched_products"]), 0)

    # ==============================================================
    # 2. TEST DETERMINISTIC FINANCING MATCHING ENGINE (AI-F005)
    # ==============================================================

    def test_unsecured_loan_matching_success(self):
        """Test doanh nghiệp SME đủ điều kiện vay vốn lưu động tín chấp."""
        profile = CompanyFinancialProfile(
            company_name="An Phu Trading Ltd",
            operating_months=24,
            annual_revenue=Decimal("2000000000"),
            current_cash_balance=Decimal("250000000"),
            current_dscr=Decimal("1.45"),
            has_collateral=False,
            projected_shortfall_days=10
        )
        request = FundingRequest(
            amount=Decimal("500000000"),
            term_months=12,
            purpose=FundingPurpose.WORKING_CAPITAL
        )

        result = self.matcher.evaluate(profile, request)

        self.assertEqual(result.status, "SUCCESS")
        self.assertGreater(result.matched_options_count, 0)
        
        top_match = result.matched_products[0]
        self.assertIn("VPB_SME_FAST_LOAN", [p["product_id"] for p in result.matched_products])
        self.assertGreaterEqual(top_match["match_score"], 60.0)
        self.assertEqual(result.policy_declaration["bank_submission_active"], False)
        self.assertEqual(result.policy_declaration["data_mode"], "simulation")

    def test_collateral_rejection_tier_1(self):
        """Test sản phẩm yêu cầu TSĐB bị loại ở Vòng 1 nếu doanh nghiệp không có TSĐB."""
        profile = CompanyFinancialProfile(
            company_name="Tech Startup JSC",
            operating_months=36,
            annual_revenue=Decimal("5000000000"),
            current_cash_balance=Decimal("500000000"),
            current_dscr=Decimal("1.80"),
            has_collateral=False,
            projected_shortfall_days=45
        )
        request = FundingRequest(
            amount=Decimal("1000000000"),
            term_months=12,
            purpose=FundingPurpose.WORKING_CAPITAL
        )

        result = self.matcher.evaluate(profile, request)
        disqualified_ids = [d["product_id"] for d in result.disqualified_summary]
        self.assertIn("VCB_WORKING_CAPITAL_SECURED", disqualified_ids)
        self.assertIn("BIDV_EASY_SME_CREDIT", disqualified_ids)

    # ==============================================================
    # 3. TEST STANDARDIZED 9 KPIS WHAT-IF SCENARIO ENGINE
    # ==============================================================

    def test_scenario_9_kpis_calculation(self):
        """Test mô phỏng What-if tính toán chính xác cả 9 KPIs Layer."""
        base_snapshot = {
            "snapshot_id": "snap_test_q3",
            "revenue": 1000000000.0,
            "cogs": 600000000.0,
            "ar_outstanding": 250000000.0,
            "ap_outstanding": 150000000.0,
            "inventory_value": 200000000.0,
            "opening_cash": 300000000.0,
            "payroll_expense": 120000000.0,
            "opex_expense": 80000000.0
        }

        params = ScenarioParameters(
            sales_change_pct=Decimal("-0.20"),
            collection_delay_days=15,
            payroll_change_pct=Decimal("0.0"),
            opex_change_pct=Decimal("0.0"),
            one_off_expense=Decimal("50000000"),
            financing_amount=Decimal("0.0")
        )

        sim = self.scenario_engine.simulate(
            base_snapshot=base_snapshot,
            params=params,
            scenario_id="scen_test_01",
            company="Test Company"
        )

        self.assertEqual(sim.revenue.simulation, 800000000.0)
        self.assertEqual(sim.revenue.relative_change, -0.20)
        self.assertEqual(sim.gross_profit.simulation, 320000000.0)
        self.assertAlmostEqual(sim.gross_margin.simulation, 0.40, places=2)
        self.assertGreater(sim.dso.simulation, sim.dso.baseline)
        self.assertLess(sim.net_cash_flow.simulation, sim.net_cash_flow.baseline)
        self.assertLess(sim.ending_cash.simulation, sim.ending_cash.baseline)
        self.assertEqual(sim.data_mode, "simulation")

    def test_scenario_financing_injection(self):
        """Test việc bơm khoản vay tài trợ vào kịch bản giúp giải quyết Cash Shortfall."""
        base_snapshot = {
            "revenue": 500000000.0,
            "cogs": 350000000.0,
            "ar_outstanding": 150000000.0,
            "ap_outstanding": 100000000.0,
            "inventory_value": 100000000.0,
            "opening_cash": 20000000.0,
            "payroll_expense": 80000000.0,
            "opex_expense": 50000000.0
        }

        params_no_loan = ScenarioParameters(
            sales_change_pct=Decimal("-0.10"),
            collection_delay_days=20,
            financing_amount=Decimal("0.0")
        )
        sim_no_loan = self.scenario_engine.simulate(base_snapshot, params_no_loan)
        self.assertGreater(sim_no_loan.cash_shortfall.simulation, 0)

        params_with_loan = ScenarioParameters(
            sales_change_pct=Decimal("-0.10"),
            collection_delay_days=20,
            financing_amount=Decimal("200000000"),
            financing_term_months=12,
            financing_rate_annual=Decimal("0.10")
        )
        sim_with_loan = self.scenario_engine.simulate(base_snapshot, params_with_loan)
        self.assertEqual(sim_with_loan.cash_shortfall.simulation, 0.0)
        self.assertGreater(sim_with_loan.ending_cash.simulation, sim_no_loan.ending_cash.simulation)


if __name__ == "__main__":
    unittest.main()
