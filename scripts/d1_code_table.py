"""1일차: payment_terms_raw 표기 → 표준 코드 7개 매핑표(실습 B2).

실행: uv run python scripts/d1_code_table.py
입력: data/day1/d1_buyers_raw.xlsx (buyers 시트, 읽기만)
출력: workbench/day1/outputs/d1_code_table.csv (utf-8-sig)

원래 표기는 앞뒤 공백까지 그대로 한 행씩 남긴다. 판단은 아래 규칙 순서대로 처음 맞는 것 하나.
애매하면 '검토 필요'로 두고 추측하지 않는다.
"""

import re

import pandas as pd

SRC = "data/day1/d1_buyers_raw.xlsx"
OUT = "workbench/day1/outputs/d1_code_table.csv"
REVIEW = "검토 필요"

# (정규식, 표준 코드, 판단 근거, 확신) — 대소문자 무시, 앞뒤 공백 제거한 표기에 적용
RULES = [
    # 섞인 조건: 7개 코드 중 하나로 못 나눔
    (r"10%.*advance.*90%.*o/a", REVIEW, "'10% T/T advance' + '90% O/A' — 선수 10%·외상 90% 혼합, 7개 코드 중 해당 없음", "낮음"),
    # 선수 + 잔금 30/70
    (r"30%.*advance.*70%", "TT_SPLIT_30_70", "'30% T/T advance' + '70% ... after B/L' — 선수 30%·잔금 70%", "높음"),
    (r"^t/t 30[/:]70$", "TT_SPLIT_30_70", "'T/T 30/70' — 30:70 분할 송금(어느 쪽이 선수인지는 표기 없음, 관행상 30% 선수)", "낮음"),
    # 선수금
    (r"100% t/t before shipment", "TT_ADV", "'before shipment' — 선적 전 100% 송금", "높음"),
    (r"t/t in advance", "TT_ADV", "'in advance' — 선적 전 송금", "높음"),
    # 신용장
    (r"usance l/c", "LC_USANCE", "'Usance L/C' — 기한부 신용장", "높음"),
    (r"^l/c \d+ days$", "LC_USANCE", "'L/C' + 'N days' — 일람 후 N일 지급이라 기한부로 봄", "높음"),
    (r"l/?c at sight", "LC_SIGHT", "'L/C at sight' — 일람불 신용장", "높음"),
    (r"신용장 일람불", "LC_SIGHT", "'신용장 일람불' — 일람불 신용장(한글 표기)", "높음"),
    # 추심
    (r"^d/?p\b", "DP", "'D/P' — 지급인도조건", "높음"),
    (r"^d/?a\s?\d+|documents against acceptance", "DA", "'D/A' / 'Documents against acceptance' — 인수인도조건", "높음"),
    # 송금 외상
    (r"^o/?a\s?\d+|\d+ days o/a|open acc(oun)?t", "OA", "'O/A' / 'Open account' — 사후송금(외상)", "높음"),
    (r"^net \d+", "OA", "'Net N' — 송장 후 N일 내 지급, 은행 서류 없는 외상", "높음"),
    (r"^t/t \d+ days after b/l$", "OA", "'T/T' + 'N days after B/L' — 선적 후 송금(외상). 7개 코드에 '후지급 T/T'가 없어 OA로 봄", "낮음"),
    (r"^t/t \d+ ?days$", "OA", "'T/T' + 'N days' — 후지급으로 보이나 기산점(B/L·송장) 표기 없음", "낮음"),
    # T/T만: 선적 전인지 후인지 모름
    (r"^tt$", REVIEW, "'TT'만 있음 — 선적 전(선수)인지 후(외상)인지 알 수 없음", "낮음"),
]


def classify(raw):
    text = raw.strip().lower()
    for pattern, code, reason, conf in RULES:
        if re.search(pattern, text):
            return code, reason, conf
    return REVIEW, "규칙에 맞는 단어 없음", "낮음"


df = pd.read_excel(SRC, sheet_name="buyers", dtype=object)
raws = df["payment_terms_raw"].dropna().astype(str).drop_duplicates().sort_values(key=lambda s: s.str.strip().str.lower())

rows = [(raw, *classify(raw)) for raw in raws]
table = pd.DataFrame(rows, columns=["원래 표기", "표준 코드", "판단 근거(어느 단어로)", "확신(높음/낮음)"])
table.to_csv(OUT, index=False, encoding="utf-8-sig")

print(f"표기 {len(table)}종 → {OUT}")
print(table["표준 코드"].value_counts().to_string())
print(f"확신 낮음 {int((table['확신(높음/낮음)'] == '낮음').sum())}행 · 검토 필요 {int((table['표준 코드'] == REVIEW).sum())}행")
