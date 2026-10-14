"""1일차: d1_buyers_raw.xlsx 데이터 품질 진단(읽기 전용).

원본은 고치지 않는다. 숫자 · 표기 예를 계산해 화면에 찍기만 한다.
보고서: workbench/day1/outputs/d1_quality_report.md
기준: data/data_dictionary.xlsx (columns · codes · payment_terms_map 시트)

실행: uv run python scripts/d1_buyers_quality_check.py
"""

import re
from collections import Counter

import pandas as pd

SRC = "data/day1/d1_buyers_raw.xlsx"
DICT = "data/data_dictionary.xlsx"
BASE_DATE = pd.Timestamp("2026-09-30")  # readme 시트 기준일

df = pd.read_excel(SRC, sheet_name="buyers", dtype=object)  # 엑셀 셀 타입 그대로(str/int/float)
df.insert(0, "excel_row", df.index + 2)  # 엑셀 행 번호(1행 = 머리글)
cols = [c for c in df.columns if c != "excel_row"]

dic = pd.read_excel(DICT, sheet_name="columns", dtype=object)
dic = dic[dic["file"].astype(str).str.contains("d1_buyers")].set_index("column")
ptmap = pd.read_excel(DICT, sheet_name="payment_terms_map", header=2, dtype=object)


def tname(v):
    if pd.isna(v):
        return "빈칸"
    return {"str": "글자", "int": "정수", "float": "실수"}.get(type(v).__name__, type(v).__name__)


def is_blank(v):
    return pd.isna(v) or (isinstance(v, str) and v.strip() == "")


NUM_LIKE = re.compile(r"\d")
PURE_NUM = re.compile(r"^-?\d+(\.\d+)?$")

# ── 1. 열별 요약 ─────────────────────────────────────────────
print(f"# 행 수 {len(df)} · 열 수 {len(cols)}\n")
print("## 1. 열별 요약")
for c in cols:
    s = df[c]
    types = Counter(tname(v) for v in s)
    strs = [v for v in s if isinstance(v, str)]
    ws = [v for v in strs if v != v.strip() or "  " in v]
    print(
        f"- {c} | 사전 dtype={dic.loc[c, 'dtype']} | 셀 타입={dict(types)} | "
        f"결측(빈칸)={sum(is_blank(v) for v in s)} | 고유값={s.nunique(dropna=False)} | "
        f"앞뒤공백={len(ws)}"
    )

# ── 2. 중복 ─────────────────────────────────────────────────
print("\n## 2. 중복")
print("완전 중복 행(전 열 동일):", df[cols].duplicated().sum())
dup = df[df["buyer_id"].duplicated(keep=False)].sort_values(["buyer_id", "excel_row"])
for bid, g in dup.groupby("buyer_id"):
    diff = [c for c in cols if g[c].astype(str).nunique() > 1]
    print(f"- {bid}: 엑셀 행 {list(g.excel_row)} · 값이 다른 열 {diff or '없음(완전 중복)'}")
    for c in diff:
        print(f"    {c}: {[g[c].iloc[i] for i in range(len(g))]}")
print("buyer_name 중복:", df["buyer_name"].duplicated().sum(),
      "· buyer_id 중복 제외 고유 바이어:", df["buyer_id"].nunique())

# ── 3. 숫자처럼 보이는 글자(숫자 열에 글자로 저장된 셀) ──────────
print("\n## 3. 숫자 열의 글자 셀")
num_cols = [c for c in cols if str(dic.loc[c, "dtype"]) in ("number", "integer", "number/text")]
for c in num_cols:
    for _, r in df.iterrows():
        v = r[c]
        if isinstance(v, str):
            kind = "숫자 포함" if NUM_LIKE.search(v) else "숫자 없음"
            print(f"- {c} | 행 {r.excel_row} ({r.buyer_id}) | {v!r} | {kind}")
# 글자 열인데 숫자로 저장된 셀
for c in [c for c in cols if c not in num_cols]:
    bad = df[df[c].map(lambda v: isinstance(v, (int, float)) and not pd.isna(v))]
    if len(bad):
        print(f"- (글자 열) {c}: 숫자 셀 {len(bad)}개")

# ── 4. 날짜 형식 ─────────────────────────────────────────────
print("\n## 4. since_date 형식")
PATTERNS = [
    ("YYYY-MM-DD", r"^\d{4}-\d{2}-\d{2}$"),
    ("YYYY.M.D", r"^\d{4}\.\d{1,2}\.\d{1,2}$"),
    ("NN/NN/YYYY", r"^\d{2}/\d{2}/\d{4}$"),
    ("Mon D YYYY", r"^[A-Z][a-z]{2} \d{1,2} \d{4}$"),
]


def date_fmt(v):
    if not isinstance(v, str):
        return f"엑셀 날짜/숫자({type(v).__name__})"
    for name, p in PATTERNS:
        if re.match(p, v.strip()):
            return name
    return "기타"


fmt = df["since_date"].map(date_fmt)
for name, n in fmt.value_counts().items():
    ex = df.loc[fmt == name, "since_date"].head(3).tolist()
    print(f"- {name}: {n}건 · 예 {ex}")

# 슬래시 형식: 앞 두 자리가 일(DD/MM)인지 월(MM/DD)인지
sl = df.loc[fmt == "NN/NN/YYYY", "since_date"].str.split("/", expand=True).astype(int)
print(f"  슬래시: 앞자리>12 {int((sl[0] > 12).sum())}건 · 가운데>12 {int((sl[1] > 12).sum())}건 · "
      f"둘 다 ≤12(일/월 모호) {int(((sl[0] <= 12) & (sl[1] <= 12)).sum())}건")


def parse(v):
    f = date_fmt(v)
    if f == "YYYY-MM-DD":
        return pd.to_datetime(v, format="%Y-%m-%d")
    if f == "YYYY.M.D":
        return pd.to_datetime(v, format="%Y.%m.%d")
    if f == "NN/NN/YYYY":
        return pd.to_datetime(v, format="%d/%m/%Y")  # 진단용 가정: DD/MM
    if f == "Mon D YYYY":
        return pd.to_datetime(v, format="%b %d %Y")
    return pd.NaT


d = df["since_date"].map(parse)
print(f"  (진단용 해석) 최소 {d.min().date()} · 최대 {d.max().date()} · 기준일 이후 {int((d > BASE_DATE).sum())}건")
for _, r in df[d > BASE_DATE].iterrows():
    print(f"    기준일 이후: 행 {r.excel_row} {r.buyer_id} {r.since_date!r}")

# ── 5. 열별 세부 진단 ────────────────────────────────────────
print("\n## 5. 세부")
# country ↔ country_code
cc = df.groupby("country_code")["country"].agg(lambda s: sorted(set(s)))
for k, v in cc.items():
    if len(v) > 1:
        print(f"- country_code {k} ← country {v}")
print("- country_code 형식 위반(3대문자 아님):",
      df.loc[~df.country_code.astype(str).str.fullmatch(r"[A-Z]{3}"), "country_code"].tolist())
rg = df.groupby("country_code")["region"].nunique()
print("- country_code별 region 2개 이상:", rg[rg > 1].to_dict())
for k in ["USA", "MEX", "BRA"]:
    print(f"  {k} → region {sorted(df.loc[df.country_code == k, 'region'].unique())}")

# industry 빈칸
print("- industry 빈칸 행:", df.loc[df.industry.isna(), ["excel_row", "buyer_id", "segment", "buyer_type"]].values.tolist())
# segment ↔ buyer_type ↔ industry
print("- segment × buyer_type:", pd.crosstab(df.segment, df.buyer_type).to_dict())
print("- public인데 industry≠public_agency:",
      int(((df.segment == "public") & (df.industry != "public_agency")).sum()),
      "· public_agency인데 private:", int(((df.industry == "public_agency") & (df.segment == "private")).sum()))

# payment_terms_raw
pt = df["payment_terms_raw"]
up = pt.str.strip().str.upper()
print(f"- payment_terms_raw 고유 표기 {pt.nunique()} · TRIM+UPPER 후 {up.nunique()}")
print("  앞뒤공백 셀:", [repr(v) for v in pt if v != v.strip()])
known = set(ptmap["raw_upper"].astype(str))
miss = df.loc[~up.isin(known), ["excel_row", "buyer_id", "payment_terms_raw"]]
print(f"  매핑표(payment_terms_map)에 없는 표기 {len(miss)}행:")
for _, r in miss.iterrows():
    print(f"    행 {r.excel_row} {r.buyer_id} {r.payment_terms_raw!r}")
ambig = df.loc[up.isin(["TT", "T/T"]), ["excel_row", "buyer_id", "payment_terms_raw"]].values.tolist()
print("  일수 없는 TT 표기(매핑표상 TT_ADV):", ambig)

# 통화
print("- ar_currency 값:", df.ar_currency.value_counts().to_dict())
cur_by_cc = df.groupby("ar_currency")["country_code"].agg(lambda s: dict(Counter(s)))
print("  ¥ 셀 국가:", cur_by_cc.get("¥"), "· € 셀 국가:", cur_by_cc.get("€"))

# 금액 · 연체 관계 (숫자 셀만)
def num(v):
    return v if isinstance(v, (int, float)) and not pd.isna(v) else None


ar = df.ar_balance.map(num)
od = df.overdue_amount.map(num)
dpd = df.max_dpd_days.map(num)
print("- ar_balance 숫자 셀 통계:", ar.dropna().describe().round(0).to_dict())
top = df.assign(_ar=ar).sort_values("_ar", ascending=False).head(5)
print("  ar_balance 상위 5:", top[["excel_row", "buyer_id", "ar_balance", "ar_currency"]].values.tolist())
print("  ar_balance=0 행 수:", int((ar == 0).sum()))
print("  overdue > ar_balance:", df.loc[(od > ar), ["excel_row", "buyer_id", "ar_balance", "overdue_amount"]].values.tolist())
print("  dpd>0 & overdue=0:", df.loc[(dpd > 0) & (od == 0), ["excel_row", "buyer_id", "max_dpd_days", "overdue_amount"]].values.tolist())
print("  dpd=0 & overdue>0:", df.loc[(dpd == 0) & (od > 0), ["excel_row", "buyer_id", "max_dpd_days", "overdue_amount"]].values.tolist())
print("  overdue 소수점:", df.loc[df.overdue_amount.map(lambda v: isinstance(v, float) and v % 1 != 0),
                                ["excel_row", "buyer_id", "overdue_amount"]].values.tolist())
print("  dpd≥91:", df.loc[dpd >= 91, ["excel_row", "buyer_id", "max_dpd_days"]].values.tolist())
print("  ar_balance 빈칸 행:", df.loc[df.ar_balance.isna(), ["excel_row", "buyer_id", "overdue_amount"]].values.tolist())

# pay_score
ps = df.pay_score.map(num)
print("- pay_score 범위:", ps.min(), "~", ps.max(), "· 1~100 밖:", int(((ps < 1) | (ps > 100)).sum()),
      "· 60 미만:", df.loc[ps < 60, ["excel_row", "buyer_id", "pay_score"]].values.tolist())

# oecd_crc
print("- oecd_crc '-' 국가:", sorted(df.loc[df.oecd_crc == "-", "country_code"].unique()))
print("  oecd_crc 국가별 값 2개 이상:",
      {k: sorted(map(str, g.unique())) for k, g in df.groupby("country_code")["oecd_crc"] if g.astype(str).nunique() > 1})

# 재무 열
fin = ["revenue_usd_fy2025", "current_ratio_fy2025", "debt_to_equity_fy2025", "dso_fy2025", "op_margin_fy2025"]
nr = df.fin_summary_text.str.contains("not received", case=False, na=False)
print("- 'not received' 문장 행:", int(nr.sum()), "· 그중 재무 5열 모두 빈칸:", int(df.loc[nr, fin].isna().all(axis=1).sum()))
print("  재무 5열 모두 빈칸 행:", int(df[fin].isna().all(axis=1).sum()))
print("  'not disclosed' 문장 행:", int(df.fin_summary_text.str.contains("not disclosed", na=False).sum()))
print("  D/E 음수:", df.loc[df.debt_to_equity_fy2025.map(lambda v: num(v) is not None and v < 0),
                          ["excel_row", "buyer_id", "debt_to_equity_fy2025"]].values.tolist())
print("  dso 정수 셀:", df.loc[df.dso_fy2025.map(lambda v: isinstance(v, int)), ["excel_row", "buyer_id", "dso_fy2025"]].values.tolist())

# 요약문 숫자 ↔ 열 숫자 대조 (매출 USD xM, 영업이익률 x%)
mism = []
for _, r in df.iterrows():
    t = r.fin_summary_text if isinstance(r.fin_summary_text, str) else ""
    m = re.search(r"USD ([\d.]+)M", t)
    if m and num(r.revenue_usd_fy2025) is not None and abs(float(m.group(1)) * 1e6 - r.revenue_usd_fy2025) > 0.06e6:
        mism.append((r.excel_row, r.buyer_id, "revenue", m.group(0), r.revenue_usd_fy2025))
    if m and r.revenue_usd_fy2025 is None or (m and pd.isna(r.revenue_usd_fy2025)):
        mism.append((r.excel_row, r.buyer_id, "revenue 빈칸인데 문장에 매출", m.group(0), r.revenue_usd_fy2025))
    m2 = re.search(r"\((-?[\d.]+)% margin\)|operating margin (-?[\d.]+)%", t)
    if m2:
        pct = float(m2.group(1) or m2.group(2))
        om = num(r.op_margin_fy2025)
        if om is None:
            mism.append((r.excel_row, r.buyer_id, "op_margin 빈칸인데 문장에 이익률", f"{pct}%", r.op_margin_fy2025))
        elif abs(pct / 100 - om) > 0.0006:
            mism.append((r.excel_row, r.buyer_id, "op_margin", f"{pct}%", om))
print("  요약문↔열 불일치:", len(mism))
for x in mism:
    print("    ", x)

# ── 6. 숫자 열 관측 범위 (데이터 사전 d1_data_dictionary.md용) ─────────
# 완전 중복 행(B047)을 뺀 150행, 숫자로 저장된 셀만 (글자 셀은 제외)
print("\n## 6. 숫자 열 관측 범위 (완전 중복 제외, 숫자 셀만)")
uniq = df.drop(columns="excel_row").drop_duplicates()
for c in ["ar_balance", "max_dpd_days", "overdue_amount", "pay_score", "oecd_crc"] + fin:
    s = pd.Series([v for v in uniq[c] if num(v) is not None], dtype=float)
    print(f"- {c}: n={len(s)} · 최소 {s.min():,} · 중앙값 {s.median():,} · 최대 {s.max():,}")
