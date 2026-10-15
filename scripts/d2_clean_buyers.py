"""2일차: buyers 시트 정제 — workbench/day2/rules/정제규칙.md 1 · 2 · 4칸.

- 1칸 통화: currency → 4코드(ccy 새 열). 원천 currency 열은 그대로 둔다.
- 2칸 숫자 변환: 잔액 · 버킷 글자 셀의 공백 · 콤마 · 통화문자를 지운다. k 표기는 버킷 합계로 바꾼다.
- 4칸 단위 의심: 잔액 ÷ 버킷 합계가 1,000배(±1%)면 버킷 합계로 바꾸고 unit_fix=1.
  (한도 기준 unit_suspect는 7칸 USD 환산이 필요해 아직 넣지 않았다.)

원본 data/checkpoints/d2_start.xlsx는 읽기만 한다.
검증: uv run pytest workbench/day2/tests -q
실행: uv run python scripts/d2_clean_buyers.py  → workbench/day2/outputs/d2_buyers_clean.csv
"""

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/checkpoints/d2_start.xlsx"
OUT = ROOT / "workbench/day2/outputs/d2_buyers_clean.csv"

BUCKETS = ["ar_current", "ar_1_30", "ar_31_60", "ar_61_90", "ar_91p"]
AMOUNT_COLS = ["ar_balance"] + BUCKETS

# 1칸: 앞뒤 공백 제거 · 대문자로 바꾼 뒤 이 표로 통일 (원본 map_ccy 시트는 비어 있어 여기에 둔다)
CCY_MAP = {
    "USD": "USD", "US$": "USD",
    "EUR": "EUR", "EURO": "EUR",
    "JPY": "JPY", "YEN": "JPY",
    "CNY": "CNY", "RMB": "CNY",
}
CCY_TEXT = re.compile(r"\b(?:USD|EUR|CNY|JPY|RMB)\b", re.IGNORECASE)
UNIT_RATIO = 1000
UNIT_TOL = 0.01


def load(path=SRC):
    return pd.read_excel(path, sheet_name="buyers", dtype=object)  # 셀 타입 그대로


def is_k(v):
    return isinstance(v, str) and v.strip().lower().endswith("k")


def to_number(v):
    """2칸: 공백 · 콤마 · 통화문자를 지우고 숫자로. 모르는 글자가 남으면 ValueError로 멈춘다."""
    if isinstance(v, str):
        return float(CCY_TEXT.sub("", v).replace(",", "").strip())
    return float(v)


def clean(df):
    out = df.copy()

    # 1칸 통화
    out["ccy"] = out["currency"].astype(str).str.strip().str.upper().map(CCY_MAP)

    # 2칸 숫자 변환: 버킷 먼저, 잔액은 k 표기만 버킷 합계로
    for c in BUCKETS + ["credit_limit_usd"]:
        out[c] = out[c].map(to_number).astype(float)
    bucket_sum = out[BUCKETS].sum(axis=1)
    out.insert(out.columns.get_loc("ar_balance"), "ar_balance_raw", df["ar_balance"].astype(str))
    bal = pd.Series(
        [bucket_sum[i] if is_k(v) else to_number(v) for i, v in df["ar_balance"].items()],
        index=df.index, dtype=float,
    )

    # 4칸 단위 의심: 1,000배(±1%)면 버킷 합계로
    ratio = bal / bucket_sum.where(bucket_sum > 0)
    unit = ratio.between(UNIT_RATIO * (1 - UNIT_TOL), UNIT_RATIO * (1 + UNIT_TOL))
    out["ar_balance"] = bal.where(~unit, bucket_sum)
    out["unit_fix"] = unit.astype(int)
    return out


def main():
    out = clean(load())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"저장: {OUT.relative_to(ROOT)} ({len(out)}행)")
    print("ccy:", out["ccy"].value_counts(dropna=False).to_dict())
    print("unit_fix:", out.loc[out.unit_fix == 1, ["buyer_id", "ar_balance_raw", "ar_balance"]].values.tolist())


if __name__ == "__main__":
    main()
