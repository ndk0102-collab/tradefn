"""3일차 실습 C: 한빛식당(가상) 밥 예보 페이지 만들기.

입력: workbench/day3/outputs/lunch_clean.csv(깨끗한 표) · labs/day3/lab-c/nutritionist_memo.md(믿음 글)
출력: workbench/day3/outputs/hanbit_lunch.html (파일 하나 · 데이터는 페이지 안 JSON · fetch 없음)
기준: labs/day3/lab-c/lab_c_guide.md 「5. 감 검증」 · 「6. 페이지 규칙」
페이지는 손으로 고치지 않는다 — 이 스크립트가 계산해서 쓴다(같은 입력이면 같은 페이지).

구역 순서: 머리 → 영양사님 감 검증

실행: uv run python scripts/lunch_page.py
"""

import html
import json
import re
import sys
from pathlib import Path

import pandas as pd

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


SECTIONS = [beliefs_html]  # 머리 아래 구역 순서 — 다음 단계에서 앞쪽에 더한다

DATA = {"beliefs": [{"id": f"belief-{i}", "bars": c["bars"]} for i, c in enumerate(cards)]}

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
print(f"월급날 {c['av']:.1f} vs 보통 날 {c['bv']:.1f} (차이 {fmt_diff(c['diff'])})")
