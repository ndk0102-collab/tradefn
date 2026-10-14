# Halden Industrial Supplies Ltd.(가상) — 대금 지급 위험 신호 점검

- 원문: `data/day1/reports/halden_fictional_annual_report.md` (FY2026 = 2025-07-01 ~ 2026-06-30, 가상 문서)
- 관점: 한빛정밀(가상)이 이 바이어에게 **60일 O/A**로 수출할 때의 대금 회수 위험
- 계산: `scripts/d1_halden_signal_numbers.py` (`uv run python -X utf8 scripts/d1_halden_signal_numbers.py`)
- 결정은 사람이 한다. 이 문서는 판단 근거 초안이다.

## 1. 위험 신호 표 (체크리스트 8개 유형)

| # | 유형 | 신호 | 원문 인용 | 위치 | 심각도 |
|---|---|---|---|---|---|
| 1 | 계속기업 불확실성 | 감사인이 계속기업 '중요한 불확실성'을 강조했다. 경영진도 주석 2에서 같은 문구를 썼다 | "indicate that a material uncertainty exists that may cast significant doubt on the Company's ability to continue as a going concern." / "These conditions indicate the existence of a material uncertainty which may cast significant doubt on the Company's ability to continue as a going concern." | [H5] 감사보고서 p.14 / [H8] 주석 2 p.21 | 상 |
| 2 | 유동성 부족 | 기준 시나리오에서도 최소 여유 한도가 £0.9m에 그친다. 현금은 2,860 → 1,140(-60.1%), 유동비율은 2.37배 → 1.40배로 떨어졌다 | "In the base case the Company operates within its facilities, with minimum headroom of £0.9 million in November 2026." | [H8] 주석 2 p.21 · [H7] p.19 | 상 |
| 2-b | 유동성 부족 | 공급업체 신용 조건이 바뀌면 유동성이 흔들린다고 회사가 직접 적었다 | "Changes to the payment terms or to the availability of credit offered by our suppliers could affect our liquidity." | [H4] p.7 | 중 |
| 3 | 차입 약정 위반 | 2026-03-31 레버리지 약정을 위반했고 은행이 면제(waiver)했다. 면제 조건은 한도 축소(£15.0m → £11.0m)와 가산금리 인상(2.25% → 3.75%)이다. 매출이 기준보다 5% 낮으면 2026-12-31 최소 EBITDA 약정도 지키지 못한다 | "At the 31 March 2026 quarterly test date the Company did not meet its leverage covenant." / "the facility limit was reduced from £15.0 million to £11.0 million; (ii) the margin increased from 2.25% to 3.75% over SONIA" / "In a reasonably possible downside scenario, in which revenue is 5% below the base case, the Company would not meet the minimum EBITDA covenant at 31 December 2026 and would require a further waiver from the bank." | [H3] p.5 / [H8] 주석 15 p.30 / [H8] 주석 2 p.21 | 상 |
| 4 | 차입 만기 | 회전신용(RCF)이 2027-03-31에 만기된다. 재약정 조건은 합의되지 않았다. 인출액 £8.4m은 유동부채로 바뀌었다 | "The facility expires on 31 March 2027. Discussions on a renewal have commenced, but no terms had been agreed at the date of approval of these financial statements. Accordingly, the amount drawn of £8.4 million is presented within current liabilities" | [H8] 주석 15 p.30 | 상 |
| 5 | 매출 감소·영업손실 | 매출 -7.0%, 영업이익 흑자 £3.5m → 적자 £0.9m, 매출총이익률 23.0% → 20.4%, 당기순손실 £1,770k | "Revenue was £86.4 million (2025: £93.0 million), a decrease of 7.0%" / "we reported an operating loss of £0.9 million (2025: operating profit of £3.5 million)." | [H1] p.3 · [H6] p.18 | 중 |
| 6 | 자본잠식 | **명시되지 않음.** 자본총계 21,110 ÷ 자본금 2,000 = 10.6배라 계산상으로도 잠식이 아니다. 다만 순손실 때문에 자본이 22,880 → 21,110으로 줄었다 | 명시되지 않음 | [H7] p.19 (계산) | 하 |
| 7 | 결제조건 변경 | **우리에게 직접 해당한다.** 한국·일본·대만 공급업체의 결제기간을 60일에서 90일로 늘렸고, 매입의 약 35%는 L/C에서 O/A로 바꿨다. 매입채무회전일수는 62일 → 88일. 은행의 공급망금융 한도도 2026-08-01부터 £10.0m → £3.0m로 줄었는데, 2026-06-30 사용액은 £7.6m이다(£4.6m 초과) | "extending standard payment terms from 60 to 90 days from the bill of lading date and replacing documentary letters of credit with open account terms for suppliers representing approximately 35% of our purchases." / "the bank reduced the programme limit from £10.0 million to £3.0 million with effect from 1 August 2026. Certain suppliers agreed to extended payment terms on the basis that early payment would be available under the programme." | [H3] p.5 / [H8] 주석 16 p.31 | 상 |
| 8 | 구조조정 | **명시되지 않음.** 원가 대응을 했다는 말만 있고 구조조정(인력 감축 · 사업 매각 · 채무 재조정)은 쓰여 있지 않다. 참고로 관리비는 11,870 → 12,310으로 늘었다 | 명시되지 않음 (관련 문구: "We have taken decisive action on costs and working capital") | [H1] p.3 · [H6] p.18 | 하 |

### 체크리스트 밖에서 본 신호 (참고)

| 신호 | 원문 인용 | 위치 | 심각도 |
|---|---|---|---|
| 은행이 전 자산에 담보권을 갖고 있다. 무담보 O/A 채권자인 우리는 회수 순위에서 뒤로 밀린다 | "secured by a fixed and floating charge over all of the Company's assets." | [H8] 주석 15 p.30 | 중 |
| 고객 집중도가 높아졌다(최대 고객 24% → 31%, 상위 3사 44% → 52%). 최대 고객은 90일 결제로 바꿨다 | "Our largest customer accounted for 31% of revenue (2025: 24%) and our three largest customers for 52% (2025: 44%)." / "the move of our largest customer to 90-day payment terms from January 2026" | [H4] p.7 / [H3] p.5 | 중 |
| 60일 넘게 연체된 매출채권이 세 배 가까이로 늘었다 | "Trade receivables more than 60 days past due were £2.6 million (2025: £0.9 million)." | [H8] 주석 13 p.28 | 중 |
| 영업현금흐름 £1.9m 가운데 £4.4m가 운전자본 조치에서 나왔다. 그것을 빼면 영업현금은 마이너스로, 공급업체 결제를 늦춰 현금을 만든 구조다 | "Net cash generated from operating activities was £1.9 million (2025: £4.6 million), of which working capital initiatives contributed £4.4 million." | [H3] p.5 | 상 |

## 2. 안심 요소 표

| 안심 요소 | 원문 인용 | 위치 | 한계 |
|---|---|---|---|
| 모회사가 £4.0m 현금 증자를 했고 입금도 끝났다 | "On 5 September 2026, Altmoor Holdings Ltd, the Company's parent company, subscribed £4.0 million in cash for 4,000,000 new ordinary shares of £1 each. The proceeds were received on that date and will be used for working capital." | [H8] 주석 24 p.34 | 공급망금융 축소분(£7.0m) · 초과분(£4.6m)보다 작다. 경영진은 증자를 반영한 뒤에도 중요한 불확실성이 있다고 결론 냈다 |
| 감사의견은 한정이 아니다(적정) | "Our opinion is not modified in respect of this matter." | [H5] p.14 | 계속기업 불확실성 강조 문단이 함께 붙어 있다 |
| 은행이 약정 위반을 면제했다 | "On 12 May 2026 the bank agreed to waive the covenant breach for the March and June 2026 test dates" | [H3] p.5 | 대가로 한도 축소 · 금리 인상 · 배당 금지 조건이 붙었고, 2026-12 시험이 남아 있다 |
| 매출채권의 91%가 신용보험으로 덮여 있고 손상차손이 작다 | "At 30 June 2026, 91% of gross trade receivables (2025: 89%) were covered by trade credit insurance with Arcbridge Credit Insurance Ltd." | [H8] 주석 13 p.28 | Halden이 *받을* 돈의 보험이다. 우리 채권(Halden이 *줄* 돈)은 보호하지 않는다 |
| 자본총계가 플러스(£21.1m)이고 자본잠식이 아니다 | (표 수치 옮김) **Net assets** 2026: 21,110 / 2025: 22,880 (£'000) | [H7] p.19 | 자산 중 재고(19,450)와 매출채권(18,700) 비중이 커서 현금화 속도는 확인 필요 |
| 기준 시나리오에서는 한도 안에서 운영된다 | "In the base case the Company operates within its facilities" | [H8] 주석 2 p.21 | RCF 재약정과 '현재 공급업체 결제조건 유지'를 전제로 한 결과다 |
| 최대 고객 매입이 20% 늘었다 | "whose purchases from us grew by 20% during the year." | [H1] p.3 | 같은 고객이 90일 결제로 바꿔 운전자본 부담을 키웠다 |

## 3. 세 줄 요약

1. **계속기업 · 차입이 핵심 위험이다.** 감사인과 경영진이 모두 '중요한 불확실성'을 적었다. RCF £8.4m은 2027-03-31에 만기되는데 재약정이 합의되지 않았고, 레버리지 약정은 이미 위반(면제)했다. 다음 시험인 2026-12 최소 EBITDA £2.5m도 FY2026 EBITDA £1.1m 기준으로는 멀다.
2. **공급업체 돈으로 버티는 구조다.** 한국 등 공급업체 결제를 60일에서 90일로, L/C를 O/A로 바꿔 현금을 만들었다. 그런데 공급망금융 한도가 £10.0m에서 £3.0m로 줄어, 공급업체 대금 압박이 커질 수 있다. 무담보 O/A 채권자인 우리는 회수 순위에서 은행보다 뒤다.
3. **안심 요소(모회사 증자 £4.0m, 은행 면제, 적정의견)는 시간을 벌어 줄 뿐 위험을 없애지 못한다.** 60일 O/A 거래를 늘리려면 우리 수출채권의 보험 · 보증 여부, RCF 재약정 결과, 결제기간 연장(90일) 요청 여부를 사람이 먼저 확인해야 한다(확인 필요).

---

### 계산 근거 (`scripts/d1_halden_signal_numbers.py` 출력)

| 지표 | 계산식 | 값 |
|---|---|---:|
| 매출 증감률 | (86,420 − 92,950) ÷ 92,950 | −7.0% |
| 영업이익률 2026 | −920 ÷ 86,420 | −1.1% |
| 유동비율 2026 / 2025 | 40,500 ÷ 28,920 / 39,000 ÷ 16,450 | 1.40배 / 2.37배 |
| 현금 증감률 | (1,140 − 2,860) ÷ 2,860 | −60.1% |
| 순차입금 ÷ EBITDA 2026 | 7.2 ÷ 1.1 (약정 한도 3.0배) | 6.5배 |
| 최소 EBITDA 부족분 | 2.5 − 1.1 | £1.4m |
| RCF 미사용 한도 | 11.0 − 8.4 | £2.6m |
| 공급망금융 사용액 − 새 한도 | 7.6 − 3.0 | £4.6m |
| 자본총계 ÷ 자본금 | 21,110 ÷ 2,000 | 10.6배 |

- 순차입금/EBITDA와 EBITDA 부족분은 FY2026(7월~6월) 연간 숫자로 계산한 참고값이다. 약정 시험 기간(분기 시험일, 2026-12까지 12개월)과 기간이 달라서 실제 약정 수치는 확인 필요.
- 주석 16의 £7.6m은 2026-06-30 잔액이다. 2026-08-01 한도 축소 이후 실제 잔액은 원문에 없다(확인 필요).
