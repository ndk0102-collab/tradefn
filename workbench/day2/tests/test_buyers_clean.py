"""2일차: buyers 정제 결과 검증 — 정제규칙.md 1 · 2 · 4칸.

실행: uv run pytest workbench/day2/tests -q
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from d2_clean_buyers import AMOUNT_COLS, clean, load  # noqa: E402

N_ROWS = 150  # outputs/profile.md: buyers 시트 150행 × 28열
CCY_CODES = {"USD", "EUR", "JPY", "CNY"}  # 정제규칙 1칸


@pytest.fixture(scope="module")
def clean_df():
    return clean(load())


def test_row_count(clean_df):
    assert len(clean_df) == N_ROWS


def test_buyer_id_unique(clean_df):
    assert clean_df["buyer_id"].notna().all()
    assert clean_df["buyer_id"].is_unique


def test_currency_four_codes(clean_df):
    assert clean_df["ccy"].notna().all(), "map에 없는 통화 표기가 있다"
    assert set(clean_df["ccy"]) == CCY_CODES


@pytest.mark.parametrize("col", AMOUNT_COLS + ["credit_limit_usd"])
def test_amount_numeric_non_negative(clean_df, col):
    s = clean_df[col]
    assert pd.api.types.is_numeric_dtype(s), f"{col}에 숫자가 아닌 값이 남아 있다"
    assert s.notna().all()
    assert (s >= 0).all()


def test_b072_unit_flag(clean_df):
    by_id = clean_df.set_index("buyer_id")
    assert by_id.loc["B072", "unit_fix"] == 1
    assert by_id.loc["B072", "ar_balance"] == 8320  # 버킷 합계(8,320,000의 1/1,000)
    assert clean_df["unit_fix"].sum() == 1, "B072 말고도 unit_fix가 달렸다"
