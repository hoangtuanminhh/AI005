"""
Lotus Fin AI005 - Models and Type Definitions for Financing Decision Support & What-if Scenario Engine.
Enforces:
1. Strict Decimal arithmetic.
2. Immutability and type safety.
3. Explicit data_mode = "simulation" for What-if outputs.
4. Comprehensive 9 KPIs layer definitions.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional


class ProductType(str, Enum):
    UNSECURED_LOAN = "UNSECURED_LOAN"          # Vay tín chấp
    SECURED_LOAN = "SECURED_LOAN"              # Vay thế chấp
    OVERDRAFT = "OVERDRAFT"                    # Thấu chi doanh nghiệp
    FACTORING = "FACTORING"                    # Bao thanh toán / Mua bán nợ
    INVOICE_DISCOUNTING = "INVOICE_DISCOUNT"   # Chiết khấu hóa đơn
    SUPPLY_CHAIN_FINANCE = "SCF"               # Tài trợ chuỗi cung ứng


class RateType(str, Enum):
    FIXED = "FIXED"                            # Lãi suất cố định
    FLOATING = "FLOATING"                      # Lãi suất thả nổi


class FundingPurpose(str, Enum):
    WORKING_CAPITAL = "WORKING_CAPITAL"        # Bổ sung vốn lưu động
    EQUIPMENT = "EQUIPMENT"                    # Mua sắm máy móc thiết bị
    INVOICE_RECOVERY = "INVOICE_RECOVERY"      # Ứng vốn hóa đơn / Giảm áp lực AR
    EXPANSION = "EXPANSION"                    # Mở rộng quy mô kinh doanh


@dataclass
class FinancingProduct:
    """Đặc tả một sản phẩm tài trợ công khai từ ngân hàng / tổ chức tín dụng."""
    product_id: str
    provider: str
    product_name: str
    product_type: ProductType
    amount_min: Decimal
    amount_max: Decimal
    currency: str = "VND"
    rate_type: RateType = RateType.FIXED
    nominal_rate_annual: Decimal = Decimal("0.10")  # 10% / năm
    rate_spread_range: str = "9.0% - 12.0%/năm"
    term_min_months: int = 3
    term_max_months: int = 36
    disbursement_speed_days: int = 5
    
    # Tiêu chí đủ điều kiện (Public Eligibility Rules)
    min_operating_months: int = 12
    min_annual_revenue: Decimal = Decimal("1000000000")  # 1 tỷ VND
    min_dscr_threshold: Optional[Decimal] = Decimal("1.20")
    requires_collateral: bool = False
    accepted_collaterals: List[str] = field(default_factory=lambda: ["REAL_ESTATE", "VEHICLE", "DEPOSIT"])
    requires_audited_financials: bool = False
    
    # Metadata kiểm toán & tính hiệu lực
    source_ref: str = "https://bank.example.com/rates"
    source_as_of: str = "2026-09-01"
    verified_at: str = "2026-09-15"
    ttl_days: int = 30
    status: str = "ACTIVE"  # "ACTIVE" | "STALE" | "DEPRECATED"


@dataclass
class CompanyFinancialProfile:
    """Hồ sơ tài chính và năng lực của doanh nghiệp SME trích xuất từ Core Snapshot."""
    company_name: str
    operating_months: int
    annual_revenue: Decimal
    current_cash_balance: Decimal
    current_dscr: Decimal
    has_collateral: bool = False
    collateral_types: List[str] = field(default_factory=list)
    projected_shortfall_days: int = 999
    has_audited_financials: bool = False
    as_of_date: str = "2026-09-30"


@dataclass
class FundingRequest:
    """Nhu cầu vốn của doanh nghiệp."""
    amount: Decimal
    term_months: int
    purpose: FundingPurpose = FundingPurpose.WORKING_CAPITAL
    currency: str = "VND"


@dataclass
class ScoreBreakdown:
    """Bóc tách điểm số 100 điểm minh bạch."""
    cost_score: Decimal          # Trọng số 45% (Lãi suất thấp hơn -> Điểm cao hơn)
    capacity_fit_score: Decimal  # Trọng số 35% (Mục đích vay & khả năng trả nợ)
    speed_score: Decimal         # Trọng số 20% (Tốc độ giải ngân vs Độ gấp của dòng tiền)
    total_score: Decimal         # Điểm tổng hợp


@dataclass
class MatchedOption:
    """Sản phẩm tài trợ sau khi so khớp và chấm điểm."""
    product_id: str
    provider: str
    product_name: str
    product_type: str
    match_score: float
    score_breakdown: Dict[str, float]
    nominal_rate_annual: float
    estimated_monthly_interest: float
    disbursement_speed_days: int
    requires_collateral: bool
    source_ref: str
    source_as_of: str
    is_stale: bool
    matched_reasons: List[str]
    missing_criteria: List[str]


@dataclass
class DisqualifiedOption:
    """Sản phẩm bị loại kèm lý do không đáp ứng điều kiện cứng."""
    product_id: str
    provider: str
    product_name: str
    reasons: List[str]


@dataclass
class FinancingDecisionResult:
    """Kết quả trả về của AI-F005."""
    status: str  # "SUCCESS" | "NO_MATCH"
    request_summary: Dict[str, Any]
    matched_options_count: int
    matched_products: List[Dict[str, Any]]
    disqualified_products_count: int
    disqualified_summary: List[Dict[str, Any]]
    policy_declaration: Dict[str, Any]


# ==========================================
# 9 KPIS LAYER DEFINITIONS FOR WHAT-IF SCENARIO
# ==========================================

@dataclass
class KPIValue:
    """Cấu trúc một KPI đơn lẻ trong lớp 9 KPIs Layer."""
    metric_id: str
    metric_name: str
    baseline: Optional[float]
    simulation: Optional[float]
    absolute_change: Optional[float]
    relative_change: Optional[float]
    unit: str
    status: str = "AVAILABLE"  # "AVAILABLE" | "UNAVAILABLE"
    limitations: List[str] = field(default_factory=list)


@dataclass
class ScenarioParameters:
    """Tham số đầu vào của kịch bản mô phỏng What-if."""
    sales_change_pct: Decimal = Decimal("0.0")           # Biến động doanh số (-0.20 = giảm 20%)
    collection_delay_days: int = 0                       # Số ngày thu tiền trễ thêm (+15 ngày)
    supplier_due_shift_days: int = 0                     # Dời ngày trả nợ NCC (+10 ngày)
    payroll_change_pct: Decimal = Decimal("0.0")         # Tăng/giảm lương (+0.05 = tăng 5%)
    opex_change_pct: Decimal = Decimal("0.0")            # Tăng/giảm chi phí vận hành
    one_off_expense: Decimal = Decimal("0.0")            # Chi phí phát sinh 1 lần (sửa chữa, bảo trì)
    financing_amount: Decimal = Decimal("0.0")           # Khoản tài trợ nhận vào
    financing_term_months: int = 0                       # Kỳ hạn vay
    financing_rate_annual: Decimal = Decimal("0.0")      # Lãi suất vay năm


@dataclass
class ShortfallEvent:
    """Sự kiện thâm hụt tiền mặt theo ngày."""
    date: str
    projected_cash: float
    deficit_amount: float
    urgency_level: str  # "HIGH" | "CRITICAL" | "MODERATE"


@dataclass
class ScenarioSimulationResult:
    """Kết quả hoàn chỉnh của What-if Engine với đầy đủ 9 KPIs Layer."""
    scenario_id: str
    company: str
    base_snapshot_id: str
    data_mode: str = "simulation"  # Luôn luôn là "simulation"
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # 9 KPIs Layer
    revenue: KPIValue = field(default_factory=lambda: KPIValue("revenue", "Revenue", None, None, None, None, "VND"))
    gross_profit: KPIValue = field(default_factory=lambda: KPIValue("gross_profit", "Gross Profit", None, None, None, None, "VND"))
    gross_margin: KPIValue = field(default_factory=lambda: KPIValue("gross_margin", "Gross Margin", None, None, None, None, "%"))
    ar_outstanding: KPIValue = field(default_factory=lambda: KPIValue("ar_outstanding", "Accounts Receivable", None, None, None, None, "VND"))
    dso: KPIValue = field(default_factory=lambda: KPIValue("dso", "Days Sales Outstanding", None, None, None, None, "days"))
    net_cash_flow: KPIValue = field(default_factory=lambda: KPIValue("net_cash_flow", "Net Cash Flow", None, None, None, None, "VND"))
    ending_cash: KPIValue = field(default_factory=lambda: KPIValue("ending_cash", "Ending Cash Balance", None, None, None, None, "VND"))
    ccc: KPIValue = field(default_factory=lambda: KPIValue("ccc", "Cash Conversion Cycle", None, None, None, None, "days"))
    cash_shortfall: KPIValue = field(default_factory=lambda: KPIValue("cash_shortfall", "Cash Shortfall Deficit", None, None, None, None, "VND"))
    
    shortfall_events: List[Dict[str, Any]] = field(default_factory=list)
    limitations: List[str] = field(default_factory=list)
