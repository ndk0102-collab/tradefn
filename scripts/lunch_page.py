"""3일차 실습 C: 한빛식당(가상) 밥 예보 페이지 만들기.

입력: workbench/day3/outputs/lunch_clean.csv(깨끗한 표) · labs/day3/lab-c/nutritionist_memo.md(믿음 글) · labs/day3/lab-c/next_week_plan.csv(다음 주 계획)
출력: workbench/day3/outputs/hanbit_lunch.html (파일 하나 · 데이터는 페이지 안 JSON · fetch 없음)
기준: labs/day3/lab-c/lab_c_guide.md 「5. 감 검증」 · 「6. 페이지 규칙」 · 「7. 예보관 시험」 · 「8. 다음 주 예보」
페이지는 손으로 고치지 않는다 — 이 스크립트가 계산해서 쓴다(같은 입력이면 같은 페이지).

구역 순서: 머리 → 다음 주 예보 → 예보 성적표 → 영양사님 감 검증

실행: uv run python scripts/lunch_page.py
"""

import html
import json
import math
import re
import sys
from pathlib import Path

import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.linear_model import LinearRegression

sys.stdout.reconfigure(encoding="utf-8")

CLEAN = Path("workbench/day3/outputs/lunch_clean.csv")
MEMO = Path("labs/day3/lab-c/nutritionist_memo.md")
OUT = Path("workbench/day3/outputs/hanbit_lunch.html")

GAP = 2.0  # 100명당 2명 이상 차이 = '차이 있음'(사람이 정한 선)

df = pd.read_csv(CLEAN, encoding="utf-8-sig", dtype={"행사": str, "비고": str})
df["행사"] = df["행사"].fillna("")
df["rate"] = df["식수"] / df["출근예정"] * 100  # 출근 100명당 식수
base = df[(df["행사"] == "") & (df["월급날"] == 0)]  # 행사 없고 월급날 아닌 날
period = f"{df['날짜'].min()} – {df['날짜'].max()}"


def r1(x):
    return round(float(x), 1)


# ── 영양사님 감 검증: 계산 ───────────────────────────────────────
beliefs_text = {}
for line in MEMO.read_text(encoding="utf-8").splitlines():
    if m := re.match(r"^(\d)\. \*\*(.+?)\*\*\s*(.*)$", line.strip()):
        beliefs_text[int(m[1])] = (m[2], m[3])


def verdict(d):
    """d = 믿음 방향으로 잰 차이(+면 믿음대로)."""
    if d >= GAP:
        return "맞음"
    if d <= -GAP:
        return "틀림"
    return "반만"


def compare(no, a_name, a_mask, b_name, b_mask, sign, src=base, extra=""):
    """두 묶음의 100명당 식수 평균. sign=+1이면 a > b가 믿음, -1이면 a < b가 믿음."""
    a, b = src[a_mask(src)], src[b_mask(src)]
    av, bv = r1(a["rate"].mean()), r1(b["rate"].mean())
    d = r1((av - bv) * sign)
    return {
        "no": no, "a": a_name, "b": b_name, "av": av, "bv": bv, "an": len(a), "bn": len(b),
        "diff": r1(av - bv), "badge": verdict(d), "extra": extra,
        "bars": [{"label": a_name, "value": av, "hl": True}, {"label": b_name, "value": bv, "hl": False}],
    }


cards = []
cards.append(compare(1, "비 오는 날", lambda s: s["날씨"] == "비", "맑은 날", lambda s: s["날씨"] == "맑음", +1))
cards.append(compare(2, "금요일", lambda s: s["요일"] == "금", "월–목", lambda s: s["요일"].isin(list("월화수목")), -1))

# 믿음 3: 메뉴별(높은 순) — 돈가스가 1등이고 2등보다 2명 이상 많으면 맞음, 1등과 2명 안쪽이면 반만
menu = base.groupby("메인메뉴")["rate"].agg(["mean", "size"]).sort_values("mean", ascending=False)
menu["mean"] = menu["mean"].map(r1)
top, top_v = menu.index[0], menu["mean"].iloc[0]
pork_v, pork_rank = menu.loc["돈가스", "mean"], list(menu.index).index("돈가스") + 1
if top == "돈가스":
    other, other_v = menu.index[1], menu["mean"].iloc[1]
    b3 = "맞음" if r1(pork_v - other_v) >= GAP else "반만"
else:
    other, other_v = top, top_v
    b3 = "반만" if r1(top_v - pork_v) < GAP else "틀림"
cards.append({
    "no": 3, "a": "돈가스", "b": f"{other}({'2' if top == '돈가스' else '1'}등)", "av": pork_v, "bv": other_v,
    "an": int(menu.loc["돈가스", "size"]), "bn": int(menu.loc[other, "size"]),
    "diff": r1(pork_v - other_v), "badge": b3, "extra": f"돈가스는 {len(menu)}개 메뉴 중 {pork_rank}등",
    "bars": [{"label": k, "value": v, "hl": k == "돈가스"} for k, v in menu["mean"].items()],
})

# 믿음 4: 31도 이상 vs 25도 이상 31도 미만(최고기온 빈칸은 빼고 셈)
hot = base[base["최고기온"] >= 31]
cards.append(compare(4, "31도 이상", lambda s: s["최고기온"] >= 31, "25도 이상 31도 미만",
                     lambda s: (s["최고기온"] >= 25) & (s["최고기온"] < 31), -1,
                     extra=f"31도 이상인 날 {len(hot)}일"))
cards.append(compare(5, "월요일", lambda s: s["요일"] == "월", "화–목", lambda s: s["요일"].isin(list("화수목")), -1))

# 메모에 없던 규칙: 월급날(월급날인 날 모두) vs 보통 날(행사 없고 월급날 아닌 날)
pay = df[df["월급날"] == 1]
pv, nv = r1(pay["rate"].mean()), r1(base["rate"].mean())
pd_ = r1(pv - nv)
cards.append({
    "no": 0, "a": "월급날", "b": "보통 날", "av": pv, "bv": nv, "an": len(pay), "bn": len(base), "diff": pd_,
    "badge": "메모에 없음", "extra": ("차이 있음 — 월급날이 " + ("더 많이" if pd_ > 0 else "더 적게") + " 옴")
    if abs(pd_) >= GAP else "차이 2명 안쪽",
    "bars": [{"label": "월급날", "value": pv, "hl": True}, {"label": "보통 날", "value": nv, "hl": False}],
})
for c in cards:
    c["title"], c["body"] = beliefs_text.get(c["no"], ("월급날엔 어떨까?", "메모에는 없지만 기록에 '월급날' 열이 있어 함께 견줬습니다."))


# ── 예보 성적표: 계산 ───────────────────────────────────────────
TEST_START = "2026-09-14"  # 이 날부터 시험 기간(배울 때 쓰지 않는다)
TEXT_COLS = ["요일", "날씨", "메인메뉴", "행사"]
NUM_COLS = ["최고기온", "월급날", "출근예정"]
COST = 4500  # 1인분 원가(가정)
MARGIN = 10  # AI 준비 = 예보 + 10
MULT = {"돈가스": 1.1, "카레": 1.1, "샐러드": 0.9}  # 나머지 1.0


def half_up(x):  # 반올림(0.5는 올림)
    return math.floor(x + 0.5)


train = df[df["날짜"] < TEST_START]
test = df[df["날짜"] >= TEST_START]
TEMP_FILL = train["최고기온"].median()  # 최고기온 빈칸은 배우는 기간의 가운데 값


def features(src, columns=None):
    x = src[TEXT_COLS + NUM_COLS].copy()
    x["행사"] = x["행사"].replace("", "없음")
    x["최고기온"] = x["최고기온"].fillna(TEMP_FILL)
    x = pd.get_dummies(x, columns=TEXT_COLS, dtype=int)  # drop_first 없이
    if columns is not None:
        x = x.reindex(columns=columns, fill_value=0)  # 배울 때와 같은 열 · 없는 열은 0
    return x


X_train = features(train)
COLUMNS = list(X_train.columns)
X_test = features(test, COLUMNS)
y_train, y_test = train["식수"], test["식수"].to_numpy()

forecasters = {
    "선형 회귀": LinearRegression(),
    "LightGBM": LGBMRegressor(n_estimators=300, learning_rate=0.05, num_leaves=15, min_child_samples=5,
                              random_state=42, verbose=-1),
}
preds, scores = {}, {}
for name, model in forecasters.items():
    model.fit(X_train, y_train)
    preds[name] = model.predict(X_test)
    scores[name] = float(abs(preds[name] - y_test).mean())  # 하루 평균 몇 인분 차이
OUR = min(scores, key=scores.get)  # 더 작은 쪽이 '우리 예보관'
OUR_MODEL = forecasters[OUR]


def nutri_formula(day, dow, menu_name):
    """그날 전 같은 요일 실제 식수 4개(깨끗한 표에서 가장 가까운 날부터) 평균 × 메뉴 배수."""
    prev = df[(df["요일"] == dow) & (df["날짜"] < day)].sort_values("날짜").tail(4)
    return half_up(prev["식수"].mean() * MULT.get(menu_name, 1.0))


t = test[["날짜", "요일", "메인메뉴", "날씨", "식수"]].copy()
t["ai"] = [half_up(v) for v in preds[OUR]]
t["formula"] = [nutri_formula(r.날짜, r.요일, r.메인메뉴) for r in t.itertuples()]
t["ai_prep"] = t["ai"] + MARGIN
t["f_prep"] = t["formula"]


def outcome(prep, err):
    left = (prep - t["식수"]).clip(lower=0)
    short = (t["식수"] - prep).clip(lower=0)
    return {"mae": r1(err), "left": int(left.sum()), "left_won": int(left.sum()) * COST,
            "short": int(short.sum()), "short_days": int((short > 0).sum())}


res_ai = outcome(t["ai_prep"], scores[OUR])
res_f = outcome(t["f_prep"], (t["formula"] - t["식수"]).abs().mean())

EVENTS = {"2026-09-23": "추석 연휴 전날 · 돈가스", "2026-09-30": "비 오는 수요일 · 카레"}
event_rows = {d: t[t["날짜"] == d].iloc[0] for d in EVENTS}


def md(d):  # 2026-09-23 → 9/23
    return f"{int(d[5:7])}/{int(d[8:10])}"


# ── 다음 주 예보: 계산 ──────────────────────────────────────────
PLAN = Path("labs/day3/lab-c/next_week_plan.csv")
plan = pd.read_csv(PLAN, encoding="utf-8-sig", dtype=str, keep_default_na=False)
nw = pd.DataFrame({
    "날짜": plan["날짜"], "요일": plan["요일"], "메인메뉴": plan["메인메뉴"],
    "날씨": plan["날씨예보"], "최고기온": pd.to_numeric(plan["최고기온예보"], errors="coerce"),
    "행사": plan["행사"], "월급날": (plan["월급날"] == "Y").astype(int), "출근예정": plan["출근예정"].astype(int),
})
nw["예보"] = [half_up(v) for v in OUR_MODEL.predict(features(nw, COLUMNS))]  # 배울 때와 같은 열로
nw["준비"] = nw["예보"] + MARGIN
nw["공식"] = [nutri_formula(r.날짜, r.요일, r.메인메뉴) for r in nw.itertuples()]
MAX_DAY, MIN_DAY = nw.loc[nw["예보"].idxmax(), "날짜"], nw.loc[nw["예보"].idxmin(), "날짜"]

C_RAIN, C_FRI, C_MENU, C_HOT, C_MON, C_PAY = cards  # 감 검증 카드(코드가 계산한 차이)


def josa(word, pair):
    """받침에 맞는 조사 — pair는 '은/는' · '으로/로'."""
    code = ord(word[-1]) - 0xAC00
    jong = code % 28 if 0 <= code < 11172 else 0
    with_b, without_b = pair.split("/")
    if pair == "으로/로":
        return word + (without_b if jong in (0, 8) else with_b)  # ㄹ 받침은 '로'
    return word + (with_b if jong else without_b)


def comment(r):
    """영양사님께 드리는 한 줄 — 그날 조건(기록에서 계산한 차이)과 공식과의 차이를 근거로."""
    why = []
    if r.월급날:
        why.append(f"월급날은 기록상 출근 100명당 {abs(C_PAY['diff']):.1f}명 덜 오셨어요")
    if r.날씨 == "비":
        why.append(f"비 오는 날은 맑은 날보다 100명당 {C_RAIN['diff']:.1f}명 더 오셨어요")
    if r.요일 == "금":
        why.append(f"금요일은 월–목보다 100명당 {abs(C_FRI['diff']):.1f}명 덜 오셨어요")
    if r.요일 == "월":
        why.append(f"월요일이라고 적게 오시진 않았어요(화–목보다 100명당 {C_MON['diff']:+.1f}명)")
    if r.행사:
        why.append(f"{josa(r.행사, '으로/로')} 출근 {r.출근예정}명 예정이에요")
    if r.메인메뉴 in menu.index and len(why) < 2:
        rank = list(menu.index).index(r.메인메뉴) + 1
        why.append(f"{josa(r.메인메뉴, '은/는')} 메뉴 {len(menu)}개 중 {rank}등이에요(100명당 {menu.loc[r.메인메뉴, 'mean']:.1f}명)")
    gap = r.준비 - r.공식
    tail = ("공식과 같은 양이면 돼요" if gap == 0 else
            f"공식({r.공식}인분)보다 {abs(gap)}인분 {'더' if gap > 0 else '덜'} 준비하시길 권해요")
    return " · ".join(why[:2]) + f". {tail}."


nw["코멘트"] = [comment(r) for r in nw.itertuples()]


# ── HTML 조각 ───────────────────────────────────────────────────
E = html.escape
BADGE_CLASS = {"맞음": "ok", "반만": "half", "틀림": "bad", "메모에 없음": "half"}


def fmt_diff(d):
    return f"{d:+.1f}명"


def header_html():
    return f"""
<header class="hero">
  <h1>한빛식당 밥 예보</h1>
  <p class="lead">(가상) 한빛정밀(주) 본사 구내식당 · 기록 기간 {E(period)} · 만든 사람 총무팀 최 대리(가상)</p>
</header>"""


def belief_card(c, i):
    label = f"믿음 {c['no']}" if c["no"] else "메모에 없던 규칙"
    extra = f'<p class="extra">{E(c["extra"])}</p>' if c["extra"] else ""
    h = max(110, 30 * len(c["bars"]) + 30)
    return f"""
  <article class="card">
    <div class="card-top"><span class="kicker">{label}</span><span class="badge {BADGE_CLASS[c['badge']]}">{E(c['badge'])}</span></div>
    <h3>{E(c['title'])}</h3>
    <p class="quote">{E(c['body'])}</p>
    <dl class="nums">
      <div><dt>{E(c['a'])} <small>({c['an']}일)</small></dt><dd>{c['av']:.1f}<span>명</span></dd></div>
      <div><dt>{E(c['b'])} <small>({c['bn']}일)</small></dt><dd>{c['bv']:.1f}<span>명</span></dd></div>
    </dl>
    <p class="diff">차이 {fmt_diff(c['diff'])} (출근 100명당)</p>
    {extra}
    <div class="chart" style="height:{h}px"><canvas id="belief-{i}" aria-label="{E(label)} 막대 그래프"></canvas></div>
  </article>"""


def beliefs_html():
    body = "".join(belief_card(c, i) for i, c in enumerate(cards))
    return f"""
<section id="beliefs">
  <h2>영양사님 감 검증</h2>
  <p class="note">출근 100명당 식수(식수 ÷ 출근예정 × 100)로 견줍니다 · 행사 없고 월급날 아닌 날만({len(base)}일) · 100명당 2명 이상 차이 나면 '차이 있음'(사람이 정한 선)</p>
  <div class="grid">{body}
  </div>
</section>"""


def won(n):
    return f"{n:,}원"


def vs_card(title, ai_main, f_main, ai_sub="", f_sub=""):
    def side(who, main, sub, cls):
        sub_html = f'<span class="sub">{E(sub)}</span>' if sub else ""
        return f'<div class="side {cls}"><span class="who">{who}</span><strong>{E(main)}</strong>{sub_html}</div>'

    return f"""
    <article class="card vs">
      <h3>{E(title)}</h3>
      <div class="pair">{side("AI 예보관", ai_main, ai_sub, "ai")}{side("영양사님 공식", f_main, f_sub, "nf")}</div>
    </article>"""


def scorecard_html():
    tiles = "".join(
        f'<div class="tile{" picked" if n == OUR else ""}"><span class="who">{E(n)}</span>'
        f'<strong>{scores[n]:.1f}<span>인분</span></strong>'
        f'<span class="sub">{"우리 예보관으로 고름" if n == OUR else "시험 성적"}</span></div>'
        for n in forecasters)
    ev_lines = "".join(
        f"<li><b>{md(d)}({r['요일']}) {E(EVENTS[d])}</b> — 실제 {r['식수']}명 · AI 예보 {r['ai']}명 · 영양사님 공식 {r['formula']}인분</li>"
        for d, r in event_rows.items())
    cards3 = (
        vs_card("하루 평균 몇 인분 차이", f"{res_ai['mae']:.1f}인분", f"{res_f['mae']:.1f}인분",
                "예보와 실제의 차이 크기 평균", "공식과 실제의 차이 크기 평균")
        + vs_card("남은 밥", f"{res_ai['left']:,}인분", f"{res_f['left']:,}인분",
                  won(res_ai["left_won"]), won(res_f["left_won"]))
        + vs_card("모자란 밥(컵라면을 드신 분)", f"{res_ai['short']:,}인분", f"{res_f['short']:,}인분",
                  f"모자란 날 {res_ai['short_days']}일", f"모자란 날 {res_f['short_days']}일")
    )
    return f"""
<section id="scorecard">
  <h2>예보 성적표</h2>
  <p class="note">{train['날짜'].min()} – {train['날짜'].max()}을 배우고, 처음 보는 최근 {len(t)}일({test['날짜'].min()} – {test['날짜'].max()})로 시험했습니다 · 성적 = 하루 평균 몇 인분 차이(작을수록 좋음)</p>
  <div class="tiles">{tiles}</div>
  <p class="claim">복잡한 쪽이 늘 이기지는 않는다 — 시험으로 고른다</p>
  <p class="note">예보관 설정은 모두 같은 결과를 보려고 고정</p>
  <article class="card wide">
    <h3>시험 {len(t)}일: 실제 · 우리 예보관({E(OUR)}) · 영양사님 공식</h3>
    <div class="chart" style="height:300px"><canvas id="test-line" aria-label="시험 기간 선 그래프"></canvas></div>
    <ul class="events">{ev_lines}</ul>
  </article>
  <p class="note">AI 준비 = 예보 + {MARGIN}인분 · 영양사님 준비 = 공식 · 1인분 원가 {won(COST)}(가정) · 시험 {len(t)}일 합계</p>
  <div class="grid three">{cards3}
  </div>
</section>"""


def day_card(r):
    mark = ""
    if r.날짜 == MAX_DAY:
        mark = '<span class="mark top">이번 주 가장 많음</span>'
    elif r.날짜 == MIN_DAY:
        mark = '<span class="mark low">이번 주 가장 적음</span>'
    chips = [r.날씨, r.메인메뉴] + ([r.행사] if r.행사 else []) + (["월급날"] if r.월급날 else [])
    chip_html = "".join(f'<span class="chip">{E(c)}</span>' for c in chips)
    return f"""
    <article class="card day{' is-top' if r.날짜 == MAX_DAY else ''}">
      <div class="day-head"><span class="date">{md(r.날짜)}</span><span class="dow">{r.요일}요일</span></div>
      {mark}
      <p class="big">{r.예보}<span>명</span></p>
      <p class="prep">준비 {r.준비}인분</p>
      <p class="formula">영양사님 공식이면 {r.공식}인분</p>
      <div class="chips">{chip_html}</div>
      <p class="comment">{E(r.코멘트)}</p>
    </article>"""


def nextweek_html():
    body = "".join(day_card(r) for r in nw.itertuples())
    return f"""
<section id="next-week">
  <h2>다음 주 예보</h2>
  <p class="note">{md(nw['날짜'].iloc[0])} – {md(nw['날짜'].iloc[-1])} · 우리 예보관({E(OUR)})의 예보 · 준비 = 예보 + {MARGIN}인분 · 계획은 next_week_plan.csv</p>
  <div class="week">{body}
  </div>
</section>"""


SECTIONS = [nextweek_html, scorecard_html, beliefs_html]  # 머리 아래 구역 순서 — 새 구역은 앞쪽에 더한다
SECTION_NAMES = ["다음 주 예보", "예보 성적표", "영양사님 감 검증"]

DATA = {
    "beliefs": [{"id": f"belief-{i}", "bars": c["bars"]} for i, c in enumerate(cards)],
    "test": {"labels": [md(d) for d in t["날짜"]], "actual": t["식수"].tolist(), "ai": t["ai"].tolist(),
             "formula": t["formula"].tolist(), "our": OUR,
             "marks": [{"idx": int(list(t["날짜"]).index(d)), "label": md(d)} for d in EVENTS]},
}

CSS = """
:root{--bg:#f5f6f8;--card:#fff;--ink:#1f2328;--muted:#5b6370;--line:#e3e6ea;--accent:#1d5fd1;--warn:#c2410c;--gray:#6b7280;--bar:#c9ced6}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:'Noto Sans KR',sans-serif;font-size:16px;line-height:1.6;word-break:keep-all;overflow-wrap:break-word}
main{max-width:1080px;margin:0 auto;padding:24px 16px 48px}
.hero{padding:8px 0 20px;border-bottom:1px solid var(--line);margin-bottom:24px}
h1{font-size:30px;margin:0 0 6px}
.lead{margin:0;color:var(--muted);font-size:15px}
h2{font-size:22px;margin:0 0 6px}
.note{color:var(--muted);font-size:14px;margin:0 0 16px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,320px),1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;min-width:0}
.card-top{display:flex;justify-content:space-between;align-items:center;gap:8px}
.kicker{font-size:14px;color:var(--muted);font-weight:700}
.badge{font-size:14px;font-weight:700;color:#fff;padding:2px 10px;border-radius:999px}
.badge.ok{background:var(--accent)}.badge.half{background:var(--gray)}.badge.bad{background:var(--warn)}
h3{font-size:18px;margin:8px 0 4px}
.quote{font-size:14px;color:var(--muted);margin:0 0 12px}
.nums{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:0}
.nums div{background:var(--bg);border-radius:8px;padding:8px 10px}
.nums dt{font-size:14px;color:var(--muted)}
.nums small{font-size:14px}
.nums dd{margin:0;font-size:24px;font-weight:700}
.nums dd span{font-size:14px;font-weight:400;margin-left:2px}
.diff{font-size:14px;margin:10px 0 0}
.extra{font-size:14px;color:var(--muted);margin:2px 0 0}
.chart{position:relative;margin-top:10px}
section{margin-bottom:40px}
.tiles{display:grid;grid-template-columns:1fr 1fr;gap:12px;max-width:560px}
.tile{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px;display:flex;flex-direction:column}
.tile.picked{border:2px solid var(--accent)}
.who{font-size:14px;color:var(--muted);font-weight:700}
.tile strong{font-size:28px}
.tile strong span{font-size:14px;font-weight:400;margin-left:2px}
.sub{font-size:14px;color:var(--muted)}
.tile.picked .sub{color:var(--accent);font-weight:700}
.claim{font-size:17px;font-weight:700;margin:14px 0 2px}
.card.wide{margin:12px 0 16px}
.events{margin:12px 0 0;padding-left:18px;font-size:14px}
.events li{margin-bottom:4px}
.pair{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px}
.side{background:var(--bg);border-radius:8px;padding:10px;display:flex;flex-direction:column;min-width:0}
.side.ai{border-left:4px solid var(--accent)}
.side.nf{border-left:4px solid var(--bar)}
.side strong{font-size:22px}
.week{display:grid;grid-template-columns:1fr;gap:12px}
@media (min-width:900px){.week{grid-template-columns:repeat(5,minmax(0,1fr))}}
.card.day{display:flex;flex-direction:column;gap:2px}
.card.day.is-top{border:2px solid var(--accent)}
.day-head{display:flex;align-items:baseline;gap:8px}
.date{font-size:20px;font-weight:700}
.dow{font-size:15px;color:var(--muted)}
.mark{align-self:flex-start;font-size:14px;font-weight:700;padding:1px 8px;border-radius:999px;margin-top:4px}
.mark.top{background:var(--accent);color:#fff}
.mark.low{border:1px solid var(--ink);color:var(--ink)}
.big{font-size:40px;font-weight:700;margin:4px 0 0;line-height:1.2}
.big span{font-size:18px;font-weight:400;margin-left:2px}
.prep{font-size:17px;font-weight:700;margin:0;color:var(--accent)}
.formula{font-size:14px;color:var(--muted);margin:0}
.chips{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0 4px}
.chip{font-size:14px;border:1px solid var(--line);background:var(--bg);border-radius:6px;padding:0 8px}
.comment{font-size:14px;margin:4px 0 0}
"""

JS = """
const DATA = JSON.parse(document.getElementById('page-data').textContent);
const css = getComputedStyle(document.documentElement);
const ACCENT = css.getPropertyValue('--accent').trim(), BAR = css.getPropertyValue('--bar').trim();
Chart.defaults.font.family = "'Noto Sans KR', sans-serif";
Chart.defaults.font.size = 14;
Chart.defaults.color = '#5b6370';
for (const b of DATA.beliefs) {
  new Chart(document.getElementById(b.id), {
    type: 'bar',
    data: {labels: b.bars.map(x => x.label),
           datasets: [{data: b.bars.map(x => x.value), backgroundColor: b.bars.map(x => x.hl ? ACCENT : BAR),
                       borderRadius: 4, borderSkipped: 'start', barPercentage: 0.8, categoryPercentage: 0.9}]},
    options: {indexAxis: 'y', responsive: true, maintainAspectRatio: false, animation: false,
      plugins: {legend: {display: false},
                tooltip: {callbacks: {label: c => `출근 100명당 ${c.parsed.x.toFixed(1)}명`}}},
      scales: {x: {beginAtZero: true, max: 100, grid: {color: '#eef0f3'}, border: {display: false}},
               y: {grid: {display: false}, border: {display: false}}}}
  });
}
// 시험 20일 선 그래프 — 표시한 날(9/23 · 9/30)에 점선과 날짜 글자
const T = DATA.test, INK = css.getPropertyValue('--ink').trim(), GRAY = '#8a929e';
const markLines = {
  id: 'markLines',
  afterDatasetsDraw(chart) {
    const {ctx, chartArea: a, scales: {x}} = chart;
    ctx.save();
    for (const m of T.marks) {
      const px = x.getPixelForValue(m.idx);
      ctx.strokeStyle = GRAY; ctx.lineWidth = 1; ctx.setLineDash([4, 4]);
      ctx.beginPath(); ctx.moveTo(px, a.top); ctx.lineTo(px, a.bottom); ctx.stroke();
      ctx.setLineDash([]); ctx.fillStyle = INK; ctx.font = "700 14px 'Noto Sans KR', sans-serif";
      ctx.textAlign = 'center'; ctx.fillText(m.label, px, a.top + 14);
    }
    ctx.restore();
  }
};
const big = arr => arr.map((_, i) => T.marks.some(m => m.idx === i) ? 6 : 3);
new Chart(document.getElementById('test-line'), {
  type: 'line',
  data: {labels: T.labels, datasets: [
    {label: '실제', data: T.actual, borderColor: INK, backgroundColor: INK, borderWidth: 2, pointRadius: big(T.actual)},
    {label: `우리 예보관(${T.our})`, data: T.ai, borderColor: ACCENT, backgroundColor: ACCENT, borderWidth: 2, pointRadius: big(T.ai)},
    {label: '영양사님 공식', data: T.formula, borderColor: GRAY, backgroundColor: GRAY, borderWidth: 2, borderDash: [6, 4], pointRadius: big(T.formula)}
  ]},
  options: {responsive: true, maintainAspectRatio: false, animation: false,
    interaction: {mode: 'index', intersect: false},
    layout: {padding: {top: 6}},
    plugins: {legend: {position: 'bottom', labels: {boxWidth: 14, boxHeight: 2}},
              tooltip: {callbacks: {label: c => `${c.dataset.label} ${c.parsed.y}`}}},
    scales: {x: {grid: {display: false}, border: {display: false}, ticks: {autoSkip: true, maxRotation: 0}},
             y: {grid: {color: '#eef0f3'}, border: {display: false}, grace: '8%'}}},
  plugins: [markLines]
});
"""


def page():
    data_json = json.dumps(DATA, ensure_ascii=False).replace("</", "<\\/")
    sections = "".join(f() for f in SECTIONS)
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>한빛식당 밥 예보</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<main>{header_html()}{sections}
</main>
<script type="application/json" id="page-data">{data_json}</script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script>{JS}</script>
</body>
</html>
"""


OUT.write_text(page(), encoding="utf-8")

# ── 끝나면 보여 줄 것 ──────────────────────────────────────────
print(f"페이지: {OUT.as_posix()} ({OUT.stat().st_size:,} bytes)\n")
for c in cards[:-1]:
    print(f"믿음 {c['no']} {c['a']} {c['av']:.1f} vs {c['b']} {c['bv']:.1f} → {c['badge']}"
          + (f" ({c['extra']})" if c["extra"] else ""))
c = cards[-1]
print(f"월급날 {c['av']:.1f} vs 보통 날 {c['bv']:.1f} (차이 {fmt_diff(c['diff'])})\n")
print("예보관 성적(하루 평균 몇 인분 차이): " + " · ".join(f"{n} {s:.1f}" for n, s in scores.items()) + f" → 우리 예보관 {OUR}")
for d, r in event_rows.items():
    print(f"{md(d)} 실제 {r['식수']} · AI 예보 {r['ai']} · 공식 {r['formula']}")
print(f"모자란 날 수: AI {res_ai['short_days']}일 · 공식 {res_f['short_days']}일")
print(f"남은 밥: AI {res_ai['left']}인분({won(res_ai['left_won'])}) · 공식 {res_f['left']}인분({won(res_f['left_won'])}) · "
      f"모자란 밥: AI {res_ai['short']} · 공식 {res_f['short']} · 하루 평균 차이: AI {res_ai['mae']} · 공식 {res_f['mae']}")
print(f"배우는 기간 {len(train)}일 · 시험 기간 {len(t)}일 · 재료 열 {len(COLUMNS)}개\n")
for r in nw.itertuples():
    print(f"{md(r.날짜)}({r.요일}) {r.메인메뉴} · 예보 {r.예보}명 · 준비 {r.준비}인분 · 공식 {r.공식}인분 — {r.코멘트}")
print(f"가장 많은 날 {md(MAX_DAY)} · 가장 적은 날 {md(MIN_DAY)}")
print("구역 순서: 머리 → " + " → ".join(SECTION_NAMES))
