"""3일차 실습 C: hanbit_lunch_log.csv 데이터 진단(읽기 전용).

원본은 고치지 않는다. 엉망인 곳을 종류별로 세어 보고서만 쓴다.
기준: labs/day3/lab-c/lab_c_guide.md 「3. 데이터 진단」
보고서: workbench/day3/outputs/lunch_quality.md

실행: uv run python scripts/lunch_quality.py
"""

import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

SRC = Path("labs/day3/lab-c/hanbit_lunch_log.csv")
OUT = Path("workbench/day3/outputs/lunch_quality.md")

df = pd.read_csv(SRC, encoding="utf-8-sig", dtype=str, keep_default_na=False)  # 원본 글자 그대로
cols = list(df.columns)
df.insert(0, "csv_row", df.index + 2)  # CSV 줄 번호(1행 = 머리글)

# ── 날짜 해석(세기용 — 원본은 바꾸지 않는다) ─────────────────────
DATE_FORMS = [
    ("YYYY-MM-DD", re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")),
    ("YYYY/MM/DD", re.compile(r"^(\d{4})/(\d{2})/(\d{2})$")),
    ("YYYY.M.D", re.compile(r"^(\d{4})\.(\d{1,2})\.(\d{1,2})$")),
    ("M월 D일(연도 없음)", re.compile(r"^(\d{1,2})월 (\d{1,2})일$")),
]


def parse_date(s):
    for name, pat in DATE_FORMS:
        m = pat.match(s.strip())
        if not m:
            continue
        if len(m.groups()) == 2:  # 연도 없음: 10–12월은 2025년, 1–9월은 2026년(R1과 같은 기준)
            mo, d = int(m[1]), int(m[2])
            return name, date(2025 if mo >= 10 else 2026, mo, d)
        return name, date(int(m[1]), int(m[2]), int(m[3]))
    return "알 수 없음", None


parsed = df["날짜"].map(parse_date)
df["p_form"] = parsed.map(lambda t: t[0])
df["p_date"] = parsed.map(lambda t: t[1])

KO_DAYS = "월화수목금토일"
DAY_ALIAS = {d: d for d in KO_DAYS} | {d + "요일": d for d in KO_DAYS}
DAY_ALIAS |= dict(zip(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], KO_DAYS))
df["p_dow_written"] = df["요일"].str.strip().map(DAY_ALIAS)
df["p_dow_actual"] = df["p_date"].map(lambda d: KO_DAYS[d.weekday()] if d else None)

closed = df["비고"].str.strip() == "휴무"
blank = lambda c: df[c].str.strip() == ""  # noqa: E731


def to_int(s):
    s = s.strip()
    return int(s) if re.fullmatch(r"-?\d+", s) else None


att = df["출근예정"].map(to_int)
meals = df["식수"].map(to_int)

# ── 종류별 판정 ────────────────────────────────────────────────
WEATHER_STD = {"맑음", "흐림", "비", "눈"}
MENU_ALT = {"돈까스", "카레라이스", "제육", "치킨마요덮밥", "김치 찌개"}  # R9 목록
EVENT_ALT = {"외부손님", "전사교육"}

m_date = df["p_form"] != "YYYY-MM-DD"
m_dow = ~df["요일"].isin(list("월화수목금"))
m_dow_wrong = df["p_dow_written"].notna() & (df["p_dow_written"] != df["p_dow_actual"])
m_dup = df["p_date"].duplicated(keep=False)
m_closed = closed
m_meal_blank = blank("식수")
ok_num = ~closed & att.notna() & meals.notna()
m_impossible = ok_num & ((meals > att) | (meals < att * 0.2))
m_weather = ~closed & ~blank("날씨") & ~df["날씨"].isin(WEATHER_STD)
m_weather_blank = ~closed & blank("날씨")
m_temp_unit = df["최고기온"].str.contains("℃|°C", regex=True)
m_temp_blank = ~closed & blank("최고기온")
m_menu = df["메인메뉴"].isin(MENU_ALT)
m_event = df["행사"].isin(EVENT_ALT)
m_att_blank = blank("출근예정")


def ex(mask, col, n=2):
    rows = df[mask].head(n)
    return [f"`{r[col]}` ({r['csv_row']}행)" for _, r in rows.iterrows()]


def ex_meal(mask, n=2):
    rows = df[mask].head(n)
    return [f"출근 `{r['출근예정']}` · 식수 `{r['식수']}` ({r['csv_row']}행)" for _, r in rows.iterrows()]


# 같은 날짜 묶음 정보
dup = df[m_dup].copy()
dup_groups = list(dup.groupby("p_date"))
same_pairs = sum(g[cols[1:]].drop_duplicates().shape[0] == 1 for _, g in dup_groups)  # 날짜 글자 빼고 같음
recount = sum(g["비고"].str.contains("재집계").any() for _, g in dup_groups)
dup_examples = [
    f"`{d}` ({', '.join(f'{r.csv_row}행 식수 `{r.식수}`' for r in g.itertuples())})" for d, g in dup_groups[:2]
]

form_counts = df.loc[m_date, "p_form"].value_counts()
dow_wrong_rows = df[m_dow_wrong]

table = [
    ("날짜 형식 섞임", int(m_date.sum()), ex(m_date, "날짜"),
     " · ".join(f"{k} {v}줄" for k, v in form_counts.items())),
    ("요일 표기 섞임", int(m_dow.sum()), ex(m_dow, "요일"),
     "적힌 요일이 실제와 다른 줄 " + str(len(dow_wrong_rows)) + "줄: "
     + ", ".join(f"`{r.날짜}` `{r.요일}`→실제 {r.p_dow_actual} ({r.csv_row}행)" for r in dow_wrong_rows.itertuples())),
    ("같은 날짜가 두 줄", int(m_dup.sum()), dup_examples,
     f"날짜 {len(dup_groups)}개 · 완전히 같은 줄 {same_pairs}쌍 · `재집계` 든 쌍 {recount}개"),
    ("휴무 줄", int(m_closed.sum()), ex(m_closed, "날짜"), "출근예정 · 식수 0"),
    ("식수 빈칸", int(m_meal_blank.sum()), ex(m_meal_blank, "날짜"), ""),
    ("불가능해 보이는 식수", int(m_impossible.sum()), ex_meal(m_impossible),
     f"출근예정보다 많음 {int((m_impossible & (meals > att)).sum())}줄 · "
     f"출근예정의 20% 미만 {int((m_impossible & (meals < att * 0.2)).sum())}줄 (휴무 · 빈칸 제외)"),
    ("날씨 표기 섞임", int(m_weather.sum()), ex(m_weather, "날씨"),
     " · ".join(f"`{k}` {v}" for k, v in df.loc[m_weather, "날씨"].value_counts().items())
     + f" — 이 밖에 날씨 빈칸 {int(m_weather_blank.sum())}줄(휴무 제외)"),
    ("최고기온 단위(℃ · °C)와 빈칸", int((m_temp_unit | m_temp_blank).sum()),
     ex(m_temp_unit, "최고기온", 1) + ["빈칸 — " + e for e in ex(m_temp_blank, "날짜", 1)],
     f"단위 붙음 {int(m_temp_unit.sum())}줄 · 빈칸 {int(m_temp_blank.sum())}줄(휴무 제외)"),
    ("메뉴 · 행사 이름 섞임", int((m_menu | m_event).sum()), ex(m_menu, "메인메뉴", 1) + ex(m_event, "행사", 1),
     f"메뉴 {int(m_menu.sum())}줄 · 행사 {int(m_event.sum())}줄 (둘 다인 줄 {int((m_menu & m_event).sum())}) — "
     + " · ".join(f"`{k}` {v}" for k, v in pd.concat([df.loc[m_menu, '메인메뉴'], df.loc[m_event, '행사']])
                  .value_counts().items())),
    ("출근예정 빈칸", int(m_att_blank.sum()), ex(m_att_blank, "날짜"), ""),
]

# ── 비고 · 사람이 정할 줄 ──────────────────────────────────────
notes = df.loc[~blank("비고"), "비고"].value_counts()
decide = df[m_impossible]

dates = df["p_date"].dropna()
d_min, d_max = dates.min(), dates.max()

# ── 보고서 쓰기 ────────────────────────────────────────────────
L = []
L.append("# 한빛식당(가상) 점심 기록 — 데이터 진단\n")
L.append(f"원본: `{SRC.as_posix()}` (읽기만 함) · 코드: `scripts/lunch_quality.py` · 숫자는 모두 코드 계산값\n")
L.append("## 1. 줄 수 · 열 이름 · 날짜 범위\n")
L.append(f"- 줄 수: **{len(df)}줄** (머리글 제외)")
L.append(f"- 열 {len(cols)}개: " + " · ".join(f"`{c}`" for c in cols))
L.append(f"- 날짜 범위: **{d_min} – {d_max}** (형식을 해석해서 셈 · 해석 못 한 줄 {int(df['p_date'].isna().sum())}개)\n")

L.append("## 2. 엉망인 곳 — 종류별\n")
L.append("예시는 원본 글자 그대로, 괄호는 CSV 줄 번호(머리글 = 1행).\n")
L.append("| 종류 | 줄 수 | 예시 1 | 예시 2 | 세부 |")
L.append("|---|---:|---|---|---|")
for name, n, exs, detail in table:
    exs = (exs + ["", ""])[:2]
    L.append(f"| {name} | {n} | {exs[0]} | {exs[1]} | {detail} |")
L.append("")

L.append("## 3. 비고 열\n")
L.append("| 비고 글 | 줄 수 |")
L.append("|---|---:|")
for k, v in notes.items():
    L.append(f"| {k} | {v} |")
L.append(f"\n비고가 빈칸인 줄: {int(blank('비고').sum())}줄\n")

L.append("## 4. 사람이 정해야 할 줄\n")
L.append("식수가 출근예정보다 많거나 출근예정의 20% 미만인 줄. 지울지 고칠지 사람이 정한다.\n")
L.append("| CSV 줄 | 날짜 | 출근예정 | 식수 | 비고 | 판단할 것 |")
L.append("|---:|---|---:|---:|---|---|")
for r in decide.itertuples():
    if "수기 집계" in r.비고:
        why = "정제 R6에서 수강생이 `뺀다` / `×10 보정` 중 결정"
    elif meals[r.Index] > att[r.Index]:
        why = "출근예정보다 많음 — R6 규칙대로면 뺀다"
    else:
        why = "출근예정의 20% 미만 — R6 규칙대로면 뺀다"
    L.append(f"| {r.csv_row} | `{r.날짜}` | {r.출근예정} | {r.식수} | {r.비고 or '(빈칸)'} | {why} |")
L.append("")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(L), encoding="utf-8")

# ── 끝나면 보여 줄 것 ──────────────────────────────────────────
print(f"보고서: {OUT.as_posix()}\n")
print(f"1) 줄 수 {len(df)} · 날짜 범위 {d_min} – {d_max}")
print("2) " + " · ".join(f"{name} {n}" for name, n, _, _ in table))
print("3) 사람이 정할 줄: " + ", ".join(
    f"{r.날짜}(출근 {r.출근예정} · 식수 {r.식수} · 비고 {r.비고 or '빈칸'})" for r in decide.itertuples()))
