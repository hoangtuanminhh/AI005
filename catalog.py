"""
Lotus Fin AI005 - Standard Financing Products Catalog.
Contains public credit offerings from Vietnamese banks and financial institutions for SME financing.
All data points are based on published public credit tariffs with audit source refs.
"""

from decimal import Decimal
from typing import Any, Dict, List
from .models import FinancingProduct, ProductType, RateType


DEFAULT_FINANCING_CATALOG: List[FinancingProduct] = [
    FinancingProduct(
        product_id="VPB_SME_FAST_LOAN",
        provider="VPBank",
        product_name="Gói Vay Vốn Lưu Động Tín Chấp SME Siêu Tốc",
        product_type=ProductType.UNSECURED_LOAN,
        amount_min=Decimal("100000000"),        # 100M VND
        amount_max=Decimal("1500000000"),       # 1.5 Tỷ VND
        currency="VND",
        rate_type=RateType.FIXED,
        nominal_rate_annual=Decimal("0.115"),   # 11.5% / năm
        rate_spread_range="10.5% - 13.5%/năm",
        term_min_months=3,
        term_max_months=12,
        disbursement_speed_days=2,              # 2 ngày
        min_operating_months=12,
        min_annual_revenue=Decimal("800000000"), # 800M VND
        min_dscr_threshold=Decimal("1.10"),
        requires_collateral=False,
        accepted_collaterals=[],
        requires_audited_financials=False,
        source_ref="https://vpbank.com.vn/sme/tin-dung/vay-tin-chap-sme-2026",
        source_as_of="2026-09-01",
        verified_at="2026-09-20",
        ttl_days=30,
        status="ACTIVE"
    ),
    FinancingProduct(
        product_id="TCB_SME_OVERDRAFT",
        provider="Techcombank",
        product_name="Hạn Mức Thấu Chi Doanh Nghiệp Chủ Động",
        product_type=ProductType.OVERDRAFT,
        amount_min=Decimal("200000000"),        # 200M VND
        amount_max=Decimal("3000000000"),       # 3 Tỷ VND
        currency="VND",
        rate_type=RateType.FLOATING,
        nominal_rate_annual=Decimal("0.108"),   # 10.8% / năm
        rate_spread_range="9.8% - 12.2%/năm",
        term_min_months=6,
        term_max_months=12,
        disbursement_speed_days=1,              # 1 ngày sau khi duyệt hạn mức
        min_operating_months=18,
        min_annual_revenue=Decimal("1500000000"), # 1.5 Tỷ VND
        min_dscr_threshold=Decimal("1.25"),
        requires_collateral=False,
        accepted_collaterals=[],
        requires_audited_financials=False,
        source_ref="https://techcombank.com/doanh-nghiep/thau-chi-tai-khoan-sme",
        source_as_of="2026-09-05",
        verified_at="2026-09-22",
        ttl_days=30,
        status="ACTIVE"
    ),
    FinancingProduct(
        product_id="VCB_WORKING_CAPITAL_SECURED",
        provider="Vietcombank",
        product_name="Tài Trợ Vốn Lưu Động Ngắn Hạn Có Tài Sản Bảo Đảm",
        product_type=ProductType.SECURED_LOAN,
        amount_min=Decimal("500000000"),        # 500M VND
        amount_max=Decimal("10000000000"),      # 10 Tỷ VND
        currency="VND",
        rate_type=RateType.FIXED,
        nominal_rate_annual=Decimal("0.075"),   # 7.5% / năm (Lãi suất ưu đãi vì có TSĐB)
        rate_spread_range="7.0% - 8.5%/năm",
        term_min_months=6,
        term_max_months=24,
        disbursement_speed_days=7,              # 7 ngày (thẩm định tài sản)
        min_operating_months=24,
        min_annual_revenue=Decimal("2000000000"), # 2 Tỷ VND
        min_dscr_threshold=Decimal("1.30"),
        requires_collateral=True,
        accepted_collaterals=["REAL_ESTATE", "DEPOSIT", "FACTORY_WAREHOUSE"],
        requires_audited_financials=True,
        source_ref="https://vietcombank.com.vn/sme/tin-dung/tai-tro-von-luu-dong",
        source_as_of="2026-09-10",
        verified_at="2026-09-25",
        ttl_days=45,
        status="ACTIVE"
    ),
    FinancingProduct(
        product_id="BIDV_EASY_SME_CREDIT",
        provider="BIDV",
        product_name="Gói Tín Dụng SME Tiếp Sức Tăng Trưởng",
        product_type=ProductType.SECURED_LOAN,
        amount_min=Decimal("300000000"),        # 300M VND
        amount_max=Decimal("5000000000"),       # 5 Tỷ VND
        currency="VND",
        rate_type=RateType.FLOATING,
        nominal_rate_annual=Decimal("0.082"),   # 8.2% / năm
        rate_spread_range="7.8% - 9.0%/năm",
        term_min_months=6,
        term_max_months=36,
        disbursement_speed_days=5,
        min_operating_months=18,
        min_annual_revenue=Decimal("1200000000"), # 1.2 Tỷ VND
        min_dscr_threshold=Decimal("1.20"),
        requires_collateral=True,
        accepted_collaterals=["REAL_ESTATE", "VEHICLE", "DEPOSIT"],
        requires_audited_financials=False,
        source_ref="https://bidv.com.vn/vn/doanh-nghiep/khach-hang-doanh-nghiep/tin-dung/sme-easy",
        source_as_of="2026-09-01",
        verified_at="2026-09-18",
        ttl_days=30,
        status="ACTIVE"
    ),
    FinancingProduct(
        product_id="TPB_INVOICE_FACTORING",
        provider="TPBank",
        product_name="Bao Thanh Toán & Chiết Khấu Hóa Đơn Thương Mại",
        product_type=ProductType.FACTORING,
        amount_min=Decimal("150000000"),        # 150M VND
        amount_max=Decimal("2500000000"),       # 2.5 Tỷ VND
        currency="VND",
        rate_type=RateType.FIXED,
        nominal_rate_annual=Decimal("0.098"),   # 9.8% / năm
        rate_spread_range="9.2% - 10.8%/năm",
        term_min_months=1,
        term_max_months=6,
        disbursement_speed_days=2,              # 2 ngày
        min_operating_months=12,
        min_annual_revenue=Decimal("1000000000"), # 1 Tỷ VND
        min_dscr_threshold=Decimal("1.00"),
        requires_collateral=False,
        accepted_collaterals=["RECEIVABLES"],   # Thế quyền đòi nợ từ hóa đơn
        requires_audited_financials=False,
        source_ref="https://tpb.vn/doanh-nghiep/tai-tro-thuong-mai/bao-thanh-toan",
        source_as_of="2026-09-12",
        verified_at="2026-09-24",
        ttl_days=30,
        status="ACTIVE"
    ),
    FinancingProduct(
        product_id="TCB_SUPPLY_CHAIN_FINANCE",
        provider="Techcombank",
        product_name="Tài Trợ Chuỗi Cung Ứng Khách Hàng Doanh Nghiệp (SCF)",
        product_type=ProductType.SUPPLY_CHAIN_FINANCE,
        amount_min=Decimal("200000000"),
        amount_max=Decimal("4000000000"),
        currency="VND",
        rate_type=RateType.FIXED,
        nominal_rate_annual=Decimal("0.089"),   # 8.9% / năm
        rate_spread_range="8.5% - 9.8%/năm",
        term_min_months=2,
        term_max_months=9,
        disbursement_speed_days=1,
        min_operating_months=12,
        min_annual_revenue=Decimal("1500000000"),
        min_dscr_threshold=Decimal("1.15"),
        requires_collateral=False,
        accepted_collaterals=["SUPPLY_CHAIN_PO"],
        requires_audited_financials=False,
        source_ref="https://techcombank.com/doanh-nghiep/tai-tro-chuoi-cung-ung",
        source_as_of="2026-09-08",
        verified_at="2026-09-21",
        ttl_days=30,
        status="ACTIVE"
    )
]


def get_catalog() -> List[FinancingProduct]:
    """Trả về bản sao danh mục sản phẩm tín dụng."""
    return list(DEFAULT_FINANCING_CATALOG)


def get_active_catalog() -> List[FinancingProduct]:
    """Lọc ra các sản phẩm đang có hiệu lực (status == 'ACTIVE')."""
    return [p for p in DEFAULT_FINANCING_CATALOG if p.status == "ACTIVE"]
