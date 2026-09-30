"""
Lotus Fin AI005 - Standardized What-if Scenario Simulation Engine with 9 KPIs Layer.
Strictly deterministic arithmetic (Decimal, ROUND_HALF_UP).
Guarantees: data_mode = 'simulation', zero database mutation, full evidence lineage.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional
from .models import (
    KPIValue,
    ScenarioParameters,
    ScenarioSimulationResult,
    ShortfallEvent
)


class WhatIfScenarioEngine:
    """
    Công cụ mô phỏng kịch bản giả định What-if với lớp 9 KPIs chuẩn hóa:
    1. Revenue (Doanh thu)
    2. Gross Profit (Lợi nhuận gộp)
    3. Gross Margin (Biên lợi nhuận gộp)
    4. AR (Phải thu khách hàng)
    5. DSO (Số ngày thu tiền bình quân)
    6. Net Cash Flow (Dòng tiền thuần)
    7. Ending Cash (Tiền mặt cuối kỳ)
    8. CCC (Chu kỳ chuyển đổi tiền mặt)
    9. Cash Shortfall (Thâm hụt tiền mặt)
    """

    def __init__(self, period_days: int = 90, safety_cash_buffer: Decimal = Decimal("50000000")):
        self.period_days = period_days  # Mặc định quý (90 ngày)
        self.safety_cash_buffer = safety_cash_buffer  # Đệm an toàn tiền mặt (50M VND)

    def simulate(
        self,
        base_snapshot: Dict[str, Any],
        params: ScenarioParameters,
        scenario_id: str = "sim_001",
        company: str = "Demo SME"
    ) -> ScenarioSimulationResult:
        """
        Thực hiện tính toán mô phỏng từ Base Snapshot và tập tham số giả định.
        """
        # Trích xuất dữ liệu gốc (Baseline) dưới dạng Decimal
        rev_base = Decimal(str(base_snapshot.get("revenue", "1000000000")))
        cogs_base = Decimal(str(base_snapshot.get("cogs", "600000000")))
        ar_base = Decimal(str(base_snapshot.get("ar_outstanding", "250000000")))
        ap_base = Decimal(str(base_snapshot.get("ap_outstanding", "150000000")))
        inv_base = Decimal(str(base_snapshot.get("inventory_value", "200000000")))
        cash_open = Decimal(str(base_snapshot.get("opening_cash", "300000000")))
        payroll_base = Decimal(str(base_snapshot.get("payroll_expense", "120000000")))
        opex_base = Decimal(str(base_snapshot.get("opex_expense", "80000000")))
        days = Decimal(str(self.period_days))

        # --- 1. BASELINE CALCULATIONS ---
        gp_base = rev_base - cogs_base
        gm_base = (gp_base / rev_base) if rev_base > Decimal("0") else Decimal("0")
        dso_base = (ar_base / rev_base * days) if rev_base > Decimal("0") else Decimal("45")
        dpo_base = (ap_base / cogs_base * days) if cogs_base > Decimal("0") else Decimal("30")
        dio_base = (inv_base / cogs_base * days) if cogs_base > Decimal("0") else Decimal("40")
        ccc_base = dio_base + dso_base - dpo_base
        ncf_base = rev_base - cogs_base - payroll_base - opex_base
        end_cash_base = cash_open + ncf_base
        shortfall_base = max(Decimal("0"), self.safety_cash_buffer - end_cash_base)

        # --- 2. SIMULATION CALCULATIONS (APPLYING PARAMETERS) ---
        sales_factor = Decimal("1.0") + params.sales_change_pct
        rev_sim = max(Decimal("0"), rev_base * sales_factor)
        cogs_sim = max(Decimal("0"), cogs_base * sales_factor)
        gp_sim = rev_sim - cogs_sim
        gm_sim = (gp_sim / rev_sim) if rev_sim > Decimal("0") else Decimal("0")

        # DSO & AR Simulation
        dso_sim = max(Decimal("0"), dso_base + Decimal(str(params.collection_delay_days)))
        ar_sim = (rev_sim * dso_sim / days) if days > Decimal("0") else ar_base

        # DPO & AP Simulation
        dpo_sim = max(Decimal("0"), dpo_base + Decimal(str(params.supplier_due_shift_days)))
        ap_sim = (cogs_sim * dpo_sim / days) if days > Decimal("0") else ap_base

        # DIO & CCC Simulation
        dio_sim = dio_base
        ccc_sim = dio_sim + dso_sim - dpo_sim

        # Cash Flow Details
        payroll_sim = payroll_base * (Decimal("1.0") + params.payroll_change_pct)
        opex_sim = opex_base * (Decimal("1.0") + params.opex_change_pct)
        
        # Tiền thu thực tế = Doanh thu - Phần công nợ chưa thu tăng thêm
        delta_ar = ar_sim - ar_base
        actual_inflow_sim = rev_sim - delta_ar

        # Tiền chi thực tế = COGS - Phần công nợ phải trả tăng thêm + Lương + OPEX + Chi phí 1 lần
        delta_ap = ap_sim - ap_base
        actual_supplier_paid = cogs_sim - delta_ap
        
        # Chi phí lãi vay nếu có gói tài trợ bổ sung
        financing_interest = Decimal("0")
        if params.financing_amount > Decimal("0") and params.financing_rate_annual > Decimal("0"):
            financing_interest = (params.financing_amount * (params.financing_rate_annual / Decimal("12")) * (days / Decimal("30"))).quantize(
                Decimal("1.0"), rounding=ROUND_HALF_UP
            )

        actual_outflow_sim = (
            actual_supplier_paid +
            payroll_sim +
            opex_sim +
            params.one_off_expense +
            financing_interest
        )

        ncf_sim = actual_inflow_sim - actual_outflow_sim
        end_cash_sim = cash_open + ncf_sim + params.financing_amount
        shortfall_sim = max(Decimal("0"), self.safety_cash_buffer - end_cash_sim)

        # --- 3. GENERATE 9 KPIS VALUES ---
        kpi_revenue = self._create_kpi("revenue", "Revenue", rev_base, rev_sim, "VND")
        kpi_gp = self._create_kpi("gross_profit", "Gross Profit", gp_base, gp_sim, "VND")
        kpi_gm = self._create_kpi("gross_margin", "Gross Margin", gm_base, gm_sim, "%", is_ratio=True)
        kpi_ar = self._create_kpi("ar_outstanding", "Accounts Receivable", ar_base, ar_sim, "VND")
        kpi_dso = self._create_kpi("dso", "Days Sales Outstanding", dso_base, dso_sim, "days")
        kpi_ncf = self._create_kpi("net_cash_flow", "Net Cash Flow", ncf_base, ncf_sim, "VND")
        kpi_end_cash = self._create_kpi("ending_cash", "Ending Cash Balance", end_cash_base, end_cash_sim, "VND")
        kpi_ccc = self._create_kpi("ccc", "Cash Conversion Cycle", ccc_base, ccc_sim, "days")
        kpi_shortfall = self._create_kpi("cash_shortfall", "Cash Shortfall Deficit", shortfall_base, shortfall_sim, "VND")

        # --- 4. SHORTFALL TIMELINE EVENTS ---
        shortfall_events = []
        if shortfall_sim > Decimal("0"):
            shortfall_events.append({
                "date": "T+45 (Giữa kỳ)",
                "projected_cash": float(end_cash_sim.quantize(Decimal("1.0"), rounding=ROUND_HALF_UP)),
                "deficit_amount": float(shortfall_sim.quantize(Decimal("1.0"), rounding=ROUND_HALF_UP)),
                "urgency_level": "CRITICAL" if end_cash_sim < Decimal("0") else "HIGH",
                "recommended_action": "Kích hoạt gói tài trợ vốn lưu động hoặc chiết khấu hóa đơn (AI-F005)."
            })

        limitations = [
            "Mô hình giả định cấu trúc biến phí / định phí duy trì ổn định theo kỳ cơ sở.",
            "DIO (số ngày tồn kho) được giả định cố định trong mô phỏng cơ sở.",
            "Kết quả tính mang cờ 'data_mode = simulation' và không thay đổi dữ liệu sổ cái ERPNext."
        ]

        return ScenarioSimulationResult(
            scenario_id=scenario_id,
            company=company,
            base_snapshot_id=str(base_snapshot.get("snapshot_id", "snap_base_001")),
            data_mode="simulation",
            parameters={
                "sales_change_pct": float(params.sales_change_pct),
                "collection_delay_days": params.collection_delay_days,
                "supplier_due_shift_days": params.supplier_due_shift_days,
                "payroll_change_pct": float(params.payroll_change_pct),
                "opex_change_pct": float(params.opex_change_pct),
                "one_off_expense": float(params.one_off_expense),
                "financing_amount": float(params.financing_amount),
                "financing_term_months": params.financing_term_months,
                "financing_rate_annual": float(params.financing_rate_annual)
            },
            revenue=kpi_revenue,
            gross_profit=kpi_gp,
            gross_margin=kpi_gm,
            ar_outstanding=kpi_ar,
            dso=kpi_dso,
            net_cash_flow=kpi_ncf,
            ending_cash=kpi_end_cash,
            ccc=kpi_ccc,
            cash_shortfall=kpi_shortfall,
            shortfall_events=shortfall_events,
            limitations=limitations
        )

    def _create_kpi(
        self,
        metric_id: str,
        name: str,
        base_val: Decimal,
        sim_val: Decimal,
        unit: str,
        is_ratio: bool = False
    ) -> KPIValue:
        """Tạo KPI với Decimal rounding và tính toán absolute/relative change."""
        abs_change = (sim_val - base_val).quantize(Decimal("0.0001") if is_ratio else Decimal("1.0"), rounding=ROUND_HALF_UP)
        
        rel_change = None
        limitations = []
        if base_val != Decimal("0"):
            rel_change = float(((sim_val - base_val) / abs(base_val)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
        else:
            limitations.append("Giá trị kỳ cơ sở bằng 0; không tính relative_change.")

        return KPIValue(
            metric_id=metric_id,
            metric_name=name,
            baseline=float(base_val.quantize(Decimal("0.0001") if is_ratio else Decimal("1.0"), rounding=ROUND_HALF_UP)),
            simulation=float(sim_val.quantize(Decimal("0.0001") if is_ratio else Decimal("1.0"), rounding=ROUND_HALF_UP)),
            absolute_change=float(abs_change),
            relative_change=rel_change,
            unit=unit,
            status="AVAILABLE",
            limitations=limitations
        )
