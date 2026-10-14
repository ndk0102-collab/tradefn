"""1일차: d1_buyers_raw.xlsx 열의 값 목록(읽기 전용, 판단 없이 목록만).

실행: uv run python scripts/d1_value_list.py 열이름 [열이름 ...]
숫자 열 여부는 data/data_dictionary.xlsx `columns` 시트 dtype(number · integer)으로 정한다.
값은 repr로 찍어 앞뒤 공백이 보이게 한다. 행 번호는 엑셀 행(1행 = 머리글).
"""

import sys

import pandas as pd

SRC = "data/day1/d1_buyers_raw.xlsx"
DICT = "data/data_dictionary.xlsx"

df = pd.read_excel(SRC, sheet_name="buyers", dtype=object)
df.insert(0, "excel_row", df.index + 2)
dic = pd.read_excel(DICT, sheet_name="columns", dtype=object)
dtype = dic[dic["file"].astype(str).str.contains("d1_buyers")].set_index("column")["dtype"]


def is_num(v):
    return isinstance(v, (int, float)) and not pd.isna(v)


def md(rows, head):
    print("| " + " | ".join(head) + " |")
    print("|" + "---|" * len(head))
    for r in rows:
        print("| " + " | ".join(str(x) for x in r) + " |")
    print()


for col in sys.argv[1:]:
    s = df[col]
    vals = s[s.notna()]
    vc = vals.map(repr).value_counts()  # 같은 개수는 처음 나온 순서
    print(f"## {col}  (사전 dtype: {dtype[col]})\n")
    print(f"- 전체 {len(s)}행 · 값 종류 {len(vc)} · 빈칸 {int(s.isna().sum())}\n")
    print("가장 흔한 값 5개")
    md([(v, n) for v, n in vc.head(5).items()], ["값", "개수"])
    print("가장 드문 값 5개")
    md([(v, n) for v, n in vc.sort_values(kind="stable").head(5).items()], ["값", "개수"])
    print(f"(개수 1인 값: {int((vc == 1).sum())}종)\n")

    if dtype[col] in ("number", "integer"):
        bad = df.loc[s.notna() & ~s.map(is_num), ["excel_row", "buyer_id", col]]
        print(f"숫자로 읽히지 않는 값 {len(bad)}개 (빈칸 제외)")
        md([(r.excel_row, r.buyer_id, repr(r[col])) for _, r in bad.iterrows()], ["엑셀 행", "buyer_id", "값"])
        n = df.loc[s.map(is_num), ["excel_row", "buyer_id", col]].copy()
        n[col] = n[col].astype(float)
        n = n.sort_values([col, "excel_row"], kind="stable")
        for title, part in (("가장 작은 값 5개", n.head(5)), ("가장 큰 값 5개", n.tail(5).iloc[::-1])):
            print(title)
            md([(r.excel_row, r.buyer_id, f"{r[col]:,.2f}".rstrip("0").rstrip(".")) for _, r in part.iterrows()],
               ["엑셀 행", "buyer_id", "값"])
        print(f"(숫자 셀 {len(n)}개 · 최소값과 같은 셀 {int((n[col] == n[col].min()).sum())}개)\n")
