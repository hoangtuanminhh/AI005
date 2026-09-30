"""
Lotus Fin AI005 - Financing Decision Support Matching Engine.
Strictly deterministic 3-tier matching and scoring engine.
Policy invariant: R4/R5 bank-write = OFF (Read-only matching and simulation).
"""

from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional
from .models import (
    FinancingProduct,
    CompanyFinancialProfile,
    FundingRequest,
    FundingPurpose,
    ScoreBreakdown,
    MatchedOption,
    DisqualifiedOption,
    FinancingDecisionResult
)
from .catalog import get_active_catalog


class FinancingDecisionEngine:
    """
    Bộ máy so khớp và xếp hạng sản phẩm tài trợ tài chính 3 tầng (3-Tier Engine).
    Hoàn toàn tất định (Deterministic), sử dụng Decimal chính xác, không ảo giác LLM.
    """

    def __init__(self, catalog: Optional[List[FinancingProduct]] = None):
        self.catalog = catalog if catalog is not None else get_active_catalog()

    def evaluate(
        self,
        profile: CompanyFinancialProfile,
        request: FundingRequest
    ) -> FinancingDecisionResult:
        """
        Thực thi quy trình so khớp 3 vòng đối với nhu cầu tài trợ của doanh nghiệp.
        """
        req_amount = request.amount
        req_term = request.term_months
        operating_months = profile.operating_months
        annual_rev = profile.annual_revenue
        has_collateral = profile.has_collateral
        dscr = profile.current_dscr
        shortfall_days = profile.projected_shortfall_days

        matched_list: List[MatchedOption] = []
        disqualified_list: List[DisqualifiedOption] = []

        # Xác định min/max rate trong catalog để tính điểm chi phí tương đối
        active_rates = [p.nominal_rate_annual for p in self.catalog if p.status == "ACTIVE"]
        min_rate = min(active_rates) if active_rates else Decimal("0.075")
        max_rate = max(active_rates) if active_rates else Decimal("0.135")
        rate_range = max_rate - min_rate if max_rate > min_rate else Decimal("0.01")

        for product in self.catalog:
            # ==============================================================
            # VÒNG 1: BỘ LỌC CỨNG (TIER 1 - HARD ELIGIBILITY FILTERS)
            # ==============================================================
            rejections: List[str] = []

            # 1. Hạn mức vay
            if req_amount < product.amount_min:
                rejections.append(
                    f"Nhu cầu vốn ({req_amount:,.0f} VND) thấp hơn hạn mức tối thiểu ({product.amount_min:,.0f} VND)."
                )
            elif req_amount > product.amount_max:
                rejections.append(
                    f"Nhu cầu vốn ({req_amount:,.0f} VND) vượt quá hạn mức tối đa ({product.amount_max:,.0f} VND)."
                )

            # 2. Kỳ hạn vay
            if req_term < product.term_min_months or req_term > product.term_max_months:
                rejections.append(
                    f"Kỳ hạn yêu cầu ({req_term} tháng) nằm ngoài khung kỳ hạn của gói ({product.term_min_months} - {product.term_max_months} tháng)."
                )

            # 3. Doanh thu tối thiểu năm
            if annual_rev < product.min_annual_revenue:
                rejections.append(
                    f"Doanh thu năm ({annual_rev:,.0f} VND) chưa đạt ngưỡng tối thiểu ({product.min_annual_revenue:,.0f} VND)."
                )

            # 4. Thời gian hoạt động
            if operating_months < product.min_operating_months:
                rejections.append(
                    f"Thời gian hoạt động ({operating_months} tháng) chưa đủ điều kiện tối thiểu ({product.min_operating_months} tháng)."
                )

            # 5. Yêu cầu Tài sản bảo đảm (Collateral)
            if product.requires_collateral and not has_collateral:
                rejections.append(
                    "Sản phẩm yêu cầu tài sản bảo đảm (bất động sản, phương tiện, tiền gửi) nhưng doanh nghiệp chưa đăng ký TSĐB."
                )

            # 6. Yêu cầu BCTC Kiểm toán
            if product.requires_audited_financials and not profile.has_audited_financials:
                rejections.append(
                    "Sản phẩm yêu cầu Báo cáo tài chính năm gần nhất phải có kiểm toán độc lập."
                )

            # 7. Hệ số DSCR (Năng lực trả nợ)
            if product.min_dscr_threshold and dscr < product.min_dscr_threshold:
                rejections.append(
                    f"Hệ số chi trả nợ hiện tại (DSCR = {dscr:.2f}) thấp hơn mức yêu cầu của sản phẩm ({product.min_dscr_threshold:.2f})."
                )

            # Nếu có bất kỳ điều kiện cứng nào bị vi phạm -> Đưa vào danh sách loại trừ
            if rejections:
                disqualified_list.append(
                    DisqualifiedOption(
                        product_id=product.product_id,
                        provider=product.provider,
                        product_name=product.product_name,
                        reasons=rejections
                    )
                )
                continue

            # ==============================================================
            # VÒNG 2: CHẤM ĐIỂM ĐỘ PHÙ HỢP (TIER 2 - WEIGHTED 100-PT SCORING)
            # ==============================================================
            # 1. Điểm Chi phí vốn (Cost Score - Trọng số 45%)
            # Lãi suất càng thấp thì điểm càng tiến gần 100
            cost_norm = (product.nominal_rate_annual - min_rate) / rate_range
            score_cost = max(Decimal("0"), (Decimal("1") - cost_norm) * Decimal("100"))

            # 2. Điểm Tương thích Năng lực & Mục đích vay (Capacity & Purpose Fit - Trọng số 35%)
            score_fit = Decimal("75.0")  # Điểm cơ sở khi đã vượt qua Vòng 1
            if request.purpose == FundingPurpose.INVOICE_RECOVERY and product.product_type in ["FACTORING", "INVOICE_DISCOUNT"]:
                score_fit += Decimal("25.0")  # Tối ưu tuyệt đối cho giải phóng công nợ
            elif request.purpose == FundingPurpose.WORKING_CAPITAL and product.product_type in ["UNSECURED_LOAN", "OVERDRAFT", "SCF"]:
                score_fit += Decimal("20.0")
            elif request.purpose == FundingPurpose.EQUIPMENT and product.product_type == "SECURED_LOAN":
                score_fit += Decimal("20.0")
            
            # Thưởng điểm nếu DSCR vượt trội (> 1.5)
            if dscr >= Decimal("1.50"):
                score_fit = min(Decimal("100.0"), score_fit + Decimal("5.0"))
            score_fit = min(Decimal("100.0"), score_fit)

            # 3. Điểm Tốc độ giải ngân (Speed Score - Trọng số 20%)
            if shortfall_days <= 15:
                # Dòng tiền gấp: Ưu tiên giải ngân trong <= 2 ngày
                if product.disbursement_speed_days <= 2:
                    score_speed = Decimal("100.0")
                elif product.disbursement_speed_days <= 4:
                    score_speed = Decimal("70.0")
                else:
                    score_speed = Decimal("40.0")
            else:
                # Dòng tiền bình thường: Đánh giá đồng đều
                score_speed = Decimal("85.0") if product.disbursement_speed_days <= 5 else Decimal("65.0")

            # Tính điểm tổng hợp có trọng số
            total_score = (
                score_cost * Decimal("0.45") +
                score_fit * Decimal("0.35") +
                score_speed * Decimal("0.20")
            ).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

            # ==============================================================
            # VÒNG 3: BẰNG CHỨNG, KHOẢNG CÁCH & ĐỘ TƯƠI DỮ LIỆU (TIER 3 - EVIDENCE & GAPS)
            # ==============================================================
            # Kiểm tra thời hạn hiệu lực dữ liệu (TTL check)
            as_of_dt = datetime.strptime(product.source_as_of, "%Y-%m-%d").date()
            days_since_as_of = (date.today() - as_of_dt).days
            is_stale = days_since_as_of > product.ttl_days

            # Phân tích lý do thỏa mãn & điều kiện cần bổ sung
            matched_reasons = [
                f"Hạn mức {req_amount:,.0f} VND nằm trong khoảng duyệt [{product.amount_min:,.0f} - {product.amount_max:,.0f} VND].",
                f"Thời gian hoạt động ({operating_months} tháng) thỏa mãn tiêu chuẩn ngân hàng ({product.min_operating_months} tháng).",
                f"Doanh thu năm ({annual_rev:,.0f} VND) đáp ứng quy mô tối thiểu {product.min_annual_revenue:,.0f} VND.",
                f"Tốc độ giải ngân ước tính: ~{product.disbursement_speed_days} ngày làm việc."
            ]

            missing_criteria = []
            if not product.requires_collateral and product.nominal_rate_annual >= Decimal("0.11"):
                missing_criteria.append(
                    "Gói vay tín chấp có biên lãi suất cao; doanh nghiệp có thể đăng ký thêm TSĐB để chuyển sang gói ưu đãi hơn."
                )
            if product.product_type == "OVERDRAFT":
                missing_criteria.append(
                    "Cần duy trì tài khoản thanh toán và phát sinh dòng tiền định kỳ tại ngân hàng tài trợ."
                )

            # Tính lãi ước tính tháng đầu tiên (để tham khảo)
            est_monthly_interest = (req_amount * (product.nominal_rate_annual / Decimal("12"))).quantize(
                Decimal("1.0"), rounding=ROUND_HALF_UP
            )

            matched_list.append(
                MatchedOption(
                    product_id=product.product_id,
                    provider=product.provider,
                    product_name=product.product_name,
                    product_type=str(product.product_type),
                    match_score=float(total_score),
                    score_breakdown={
                        "cost_score": float(score_cost.quantize(Decimal("0.1"))),
                        "capacity_fit_score": float(score_fit.quantize(Decimal("0.1"))),
                        "speed_score": float(score_speed.quantize(Decimal("0.1")))
                    },
                    nominal_rate_annual=float(product.nominal_rate_annual),
                    estimated_monthly_interest=float(est_monthly_interest),
                    disbursement_speed_days=product.disbursement_speed_days,
                    requires_collateral=product.requires_collateral,
                    source_ref=product.source_ref,
                    source_as_of=product.source_as_of,
                    is_stale=is_stale,
                    matched_reasons=matched_reasons,
                    missing_criteria=missing_criteria
                )
            )

        # Sắp xếp theo thứ tự điểm Match Score giảm dần
        matched_list.sort(key=lambda item: item.match_score, reverse=True)

        return FinancingDecisionResult(
            status="SUCCESS" if matched_list else "NO_MATCH",
            request_summary={
                "company_name": profile.company_name,
                "amount": float(req_amount),
                "term_months": req_term,
                "purpose": str(request.purpose),
                "currency": request.currency,
                "as_of_date": profile.as_of_date,
                "action_mode": "READ_ONLY_SIMULATION"
            },
            matched_options_count=len(matched_list),
            matched_products=[self._option_to_dict(opt) for opt in matched_list],
            disqualified_products_count=len(disqualified_list),
            disqualified_summary=[
                {
                    "product_id": d.product_id,
                    "provider": d.provider,
                    "product_name": d.product_name,
                    "reasons": d.reasons
                }
                for d in disqualified_list
            ],
            policy_declaration={
                "bank_submission_active": False,
                "loan_approval_guaranteed": False,
                "data_mode": "simulation",
                "notice": "Kết quả so khớp mang tính chất tham khảo dựa trên biểu phí công bố công khai của các TCTD. Không có bất kỳ hồ sơ vay nào được tự động gửi đến ngân hàng."
            }
        )

    def _option_to_dict(self, opt: MatchedOption) -> Dict[str, Any]:
        return {
            "product_id": opt.product_id,
            "provider": opt.provider,
            "product_name": opt.product_name,
            "product_type": opt.product_type,
            "match_score": opt.match_score,
            "score_breakdown": opt.score_breakdown,
            "nominal_rate_annual": opt.nominal_rate_annual,
            "estimated_monthly_interest": opt.estimated_monthly_interest,
            "disbursement_speed_days": opt.disbursement_speed_days,
            "requires_collateral": opt.requires_collateral,
            "source_ref": opt.source_ref,
            "source_as_of": opt.source_as_of,
            "is_stale": opt.is_stale,
            "matched_reasons": opt.matched_reasons,
            "missing_criteria": opt.missing_criteria
        }
