"""1일차 A-1: Halden(가상) 위험 신호 판단에 쓴 보조 숫자 계산.

원문: data/day1/reports/halden_fictional_annual_report.md (재무표 단위 £'000, 본문 £m)
"""

# [H6] 손익계산서 (£'000)
revenue = {"2026": 86_420, "2025": 92_950}
op_profit = {"2026": -920, "2025": 3_500}
net_profit = {"2026": -1_770, "2025": 1_890}

# [H7] 재무상태표 (£'000)
current_assets = {"2026": 40_500, "2025": 39_000}
current_liab = {"2026": 28_920, "2025": 16_450}
cash = {"2026": 1_140, "2025": 2_860}
equity = {"2026": 21_110, "2025": 22_880}
share_capital = 2_000

# [H2] KPI (£m) · [H8] 주석 15 · 16 (£m)
ebitda_m = {"2026": 1.1, "2025": 5.5}
net_debt_m = {"2026": 7.2, "2025": 6.1}
facility_limit_m, drawn_m = 11.0, 8.4
scf_used_m, scf_new_limit_m = 7.6, 3.0
min_ebitda_m = 2.5

print(f"매출 증감률          = (86,420 - 92,950) / 92,950 = {revenue['2026'] / revenue['2025'] - 1:.1%}")
print(f"영업이익률 2026      = -920 / 86,420 = {op_profit['2026'] / revenue['2026']:.1%}")
for y in ("2026", "2025"):
    print(f"유동비율 {y}        = {current_assets[y]:,} / {current_liab[y]:,} = {current_assets[y] / current_liab[y]:.2f}배")
print(f"현금 증감률          = (1,140 - 2,860) / 2,860 = {cash['2026'] / cash['2025'] - 1:.1%}")
print(f"순차입금/EBITDA 2026 = 7.2 / 1.1 = {net_debt_m['2026'] / ebitda_m['2026']:.1f}배 (약정 한도 3.0배)")
print(f"EBITDA 부족분        = 2.5 - 1.1 = £{min_ebitda_m - ebitda_m['2026']:.1f}m (FY2026 기준, 시험 기간과 다름)")
print(f"한도 미사용분        = 11.0 - 8.4 = £{facility_limit_m - drawn_m:.1f}m")
print(f"공급망금융 초과분    = 7.6 - 3.0 = £{scf_used_m - scf_new_limit_m:.1f}m")
print(f"자본총계 / 자본금    = 21,110 / 2,000 = {equity['2026'] / share_capital:.1f}배 (1배 미만이면 자본잠식)")
