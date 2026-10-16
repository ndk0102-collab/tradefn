"""3일차 실습 C: hanbit_lunch_log.csv 정제 — 규칙 10개를 표 순서대로 적용.

원본은 읽기만 한다. 규칙 표: workbench/day3/outputs/lunch_rules.md
결과: workbench/day3/outputs/lunch_clean.csv(UTF-8 BOM) · lunch_clean_log.md(규칙별 고친 줄 수)
순서: R1 → R2 → R3 → R4 → R5 → R10 → R6 → R7 → R8 → R9
'수기 집계' 줄(R6): 뺀다 — 원래 숫자를 알 수 없으니 지어내지 않는다

실행: uv run python scripts/lunch_clean.py
"""

import math
import re
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")

SRC = Path("labs/day3/lab-c/hanbit_lunch_log.csv")
OUT = Path("workbench/day3/outputs/lunch_clean.csv")
LOG = Path("workbench/day3/outputs/lunch_clean_log.md")
HANDWRITTEN = "뺀다"  # '수기 집계' 줄 결정: "뺀다" 또는 "×10 보정"

df = pd.read_csv(SRC, encoding="utf-8-sig", dtype=str, keep_default_na=False)
COLS = list(df.columns)
n_start = len(df)
log = []  # (규칙, 할 일, 고친/뺀 줄 수)


def record(rule, what, n):
    log.append((rule, what, int(n), len(df)))


def half_up(x):  # 반올림(0.5는 올림)
    return math.floor(x + 0.5)


# ── R1 날짜를 YYYY-MM-DD로 ──────────────────────────────────────
def to_iso(s):
    s = s.strip()
    if m := re.fullmatch(r"(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})", s):
        y, mo, d = map(int, m.groups())
    elif m := re.fullmatch(r"(\d{1,2})월 (\d{1,2})일", s):
        mo, d = map(int, m.groups())
        y = 2025 if mo >= 10 else 2026  # 연도 없음: 10–12월은 2025년, 1–9월은 2026년
    else:
        raise ValueError(f"해석 못 한 날짜: {s!r}")
    return date(y, mo, d).isoformat()


new = df["날짜"].map(to_iso)
n = (new != df["날짜"]).sum()
df["날짜"] = new
record("R1", "날짜를 YYYY-MM-DD로", n)

# ── R2 요일을 날짜에서 다시 계산 ────────────────────────────────
KO = "월화수목금토일"
ALIAS = {d: d for d in KO} | {d + "요일": d for d in KO}
ALIAS |= dict(zip(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], KO))
actual = df["날짜"].map(lambda s: KO[date.fromisoformat(s).weekday()])
written = df["요일"].str.strip().map(ALIAS)
n = (written != actual).sum()  # 표기만 다른 줄(월요일 · Mon)은 세지 않는다
df["요일"] = actual
record("R2", "요일을 날짜에서 다시 계산(실제와 달랐던 줄)", n)

# ── R3 휴무 줄 빼기 ─────────────────────────────────────────────
drop = df["비고"].str.strip() == "휴무"
df = df[~drop]
record("R3", "비고 `휴무` 줄 빼기", drop.sum())

# ── R4 같은 날짜 두 줄 → 재집계 줄, 없으면 나중 줄 ─────────────────
keep = []
for _, g in df.groupby("날짜", sort=False):
    re_rows = g[g["비고"].str.contains("재집계")]
    keep.append((re_rows if len(re_rows) else g).index[-1])
n = len(df) - len(keep)
df = df.loc[sorted(keep)]
record("R4", "같은 날짜 두 줄 → 재집계 줄(없으면 나중 줄)만 남기기", n)

# ── R5 식수 빈칸 줄 빼기 ────────────────────────────────────────
drop = df["식수"].str.strip() == ""
df = df[~drop]
record("R5", "식수 빈칸 줄 빼기", drop.sum())

# ── R10 출근예정 빈칸 → 같은 요일 바로 앞 4개의 가운데 값 ─────────
df = df.sort_values("날짜", kind="stable")
filled = []
for i in df.index[df["출근예정"].str.strip() == ""]:
    prev = df[(df["요일"] == df.at[i, "요일"]) & (df["날짜"] < df.at[i, "날짜"]) & (df["출근예정"].str.strip() != "")]
    last4 = prev["출근예정"].astype(int).tail(4)
    if len(last4) < 4:
        raise ValueError(f"{df.at[i, '날짜']}: 같은 요일 앞 기록이 4개보다 적음")
    df.at[i, "출근예정"] = str(half_up(last4.median()))
    filled.append((df.at[i, "날짜"], df.at[i, "요일"], list(last4), df.at[i, "출근예정"]))
record("R10", "출근예정 빈칸 → 같은 요일 앞 4개 median(반올림)", len(filled))

# ── R6 불가능한 식수 빼기 · '수기 집계' 줄은 결정대로 ─────────────
att = df["출근예정"].astype(int)
meal = df["식수"].astype(int)
hand = df["비고"].str.contains("수기 집계")
bad = (meal > att) | (meal < att * 0.2)
if HANDWRITTEN == "×10 보정":
    df.loc[hand, "식수"] = (meal[hand] * 10).astype(str)
    drop = bad & ~hand
    what = "식수 > 출근예정 또는 < 20% 빼기 · 수기 집계 ×10 보정"
    n = drop.sum() + hand.sum()
else:
    drop = bad | hand
    what = "식수 > 출근예정 또는 < 20% 빼기 · 수기 집계 줄 뺀다"
    n = drop.sum()
r6_rows = df[drop | hand][["날짜", "출근예정", "식수", "비고"]].copy()
df = df[~drop]
record("R6", what, n)

# ── R7 날씨 넷으로 ──────────────────────────────────────────────
WEATHER = {"맑": "맑음", "sunny": "맑음", "구름많음": "흐림", "cloudy": "흐림",
           "rain": "비", "우천": "비", "소나기": "비", "흐리고 비": "비", "snow": "눈", "": "모름"}
new = df["날씨"].str.strip().map(lambda w: WEATHER.get(w, w))
n = (new != df["날씨"]).sum()
df["날씨"] = new
assert set(df["날씨"]) <= {"맑음", "흐림", "비", "눈", "모름"}, set(df["날씨"])
record("R7", "날씨를 맑음 · 흐림 · 비 · 눈(빈칸 → 모름)으로", n)

# ── R8 최고기온 단위 · 공백 떼기 ────────────────────────────────
new = df["최고기온"].str.replace(r"℃|°C|\s", "", regex=True)
n = (new != df["최고기온"]).sum()
df["최고기온"] = new
pd.to_numeric(df.loc[df["최고기온"] != "", "최고기온"])  # 숫자만 남았는지 확인(아니면 오류)
record("R8", "최고기온 ℃ · °C · 공백 떼기", n)

# ── R9 메뉴 · 행사 이름 통일 ────────────────────────────────────
MENU = {"돈까스": "돈가스", "카레라이스": "카레", "제육": "제육볶음", "치킨마요덮밥": "치킨마요", "김치 찌개": "김치찌개"}
EVENT = {"외부손님": "외부 손님 방문", "전사교육": "전사 교육"}
n_menu = df["메인메뉴"].isin(MENU).sum()
n_event = df["행사"].isin(EVENT).sum()
df["메인메뉴"] = df["메인메뉴"].replace(MENU)
df["행사"] = df["행사"].replace(EVENT)
record("R9", f"메뉴 · 행사 이름 통일(메뉴 {n_menu} + 행사 {n_event})", n_menu + n_event)

# ── 마무리: 형 바꾸기 · 날짜순 저장 ─────────────────────────────
assert set(df["월급날"]) <= {"Y", ""}, set(df["월급날"])
df["월급날"] = (df["월급날"] == "Y").astype(int)
df["출근예정"] = df["출근예정"].astype(int)
df["식수"] = df["식수"].astype(int)
df = df.sort_values("날짜", kind="stable")[COLS]
assert not df["날짜"].duplicated().any()
OUT.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT, index=False, encoding="utf-8-sig")

# ── 로그 쓰기 ───────────────────────────────────────────────────
L = ["# 한빛식당(가상) 점심 기록 — 정제 로그\n",
     f"원본 `{SRC.as_posix()}` → `{OUT.as_posix()}` · 규칙 표 `lunch_rules.md` · 코드 `scripts/lunch_clean.py`\n",
     f"- 처음 줄 수: **{n_start}** → 남은 줄 수: **{len(df)}** (날짜 {df['날짜'].min()} – {df['날짜'].max()})",
     f"- '수기 집계' 줄: **{HANDWRITTEN}** — 원래 숫자를 알 수 없으니 지어내지 않는다",
     "- 세는 법: 그 규칙을 적용할 때 남아 있는 줄에서 셈. R2는 실제 요일과 달랐던 줄만, R9는 메뉴와 행사를 따로 세어 더함\n",
     "| 순서 | 규칙 | 할 일 | 고친(뺀) 줄 | 적용 뒤 남은 줄 |",
     "|---:|---|---|---:|---:|"]
for k, (rule, what, cnt, left) in enumerate(log, 1):
    L.append(f"| {k} | {rule} | {what} | {cnt} | {left} |")
L.append("\n## R10으로 채운 출근예정\n")
L.append("| 날짜 | 요일 | 앞 4개(오래된 순) | 채운 값 |")
L.append("|---|---|---|---:|")
for d, w, vals, v in filled:
    L.append(f"| {d} | {w} | {' · '.join(map(str, vals))} | {v} |")
L.append("\n## R6으로 처리한 줄\n")
L.append("| 날짜 | 출근예정 | 식수 | 비고 | 처리 |")
L.append("|---|---:|---:|---|---|")
for r in r6_rows.itertuples():
    how = HANDWRITTEN if "수기 집계" in r.비고 else "뺀다"
    L.append(f"| {r.날짜} | {r.출근예정} | {r.식수} | {r.비고 or '(빈칸)'} | {how} |")
LOG.write_text("\n".join(L) + "\n", encoding="utf-8")

# ── 끝나면 보여 줄 것 ──────────────────────────────────────────
print(f"결과: {OUT.as_posix()} · 로그: {LOG.as_posix()}\n")
print(f"1) 처음 {n_start}줄 → 남은 {len(df)}줄")
print("2) " + " · ".join(f"{rule} {cnt}" for rule, _, cnt, _ in log))
print(f"3) '수기 집계' 줄: {HANDWRITTEN} — 원래 숫자를 알 수 없으니 지어내지 않는다")
