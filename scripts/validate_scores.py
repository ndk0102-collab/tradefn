"""2일차: 뉴스 채점 결과(news_scored.jsonl) 형식 검사(읽기 전용).

점수를 매기지 않는다. 규칙(workbench/day2/prompts/news_score_v1.md)대로 썼는지만 본다.
  1. 줄 수가 100인가
  2. news_sent_0_10이 0–10 정수인가
  3. label이 점수 대역과 맞는가 (0–2 severe · 3–4 high · 5 watch · 6–10 low)
  4. evidence가 같은 news_id의 원문 headline · body_short 안에 글자 그대로 있는가

실행: uv run python scripts/validate_scores.py
입력: workbench/day2/outputs/news_scored.jsonl · data/checkpoints/d2_news.csv (읽기만)
위반이 있으면 줄 번호와 이유를 찍고 종료 코드 1.
"""

import csv
import json
import sys

SCORED = "workbench/day2/outputs/news_scored.jsonl"
NEWS = "data/checkpoints/d2_news.csv"
EXPECTED_LINES = 100


def band(score):
    if score <= 2:
        return "severe"
    if score <= 4:
        return "high"
    if score == 5:
        return "watch"
    return "low"


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # Windows 터미널에서 한글이 깨지지 않게

    with open(NEWS, encoding="utf-8-sig", newline="") as f:
        news = {r["news_id"]: r for r in csv.DictReader(f)}
    with open(SCORED, encoding="utf-8") as f:
        lines = [l for l in f.read().splitlines() if l.strip()]

    errors = []  # (줄 번호, news_id, 이유)
    if len(lines) != EXPECTED_LINES:
        errors.append((0, "-", f"줄 수 {len(lines)} (기대 {EXPECTED_LINES})"))

    for no, line in enumerate(lines, 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as e:
            errors.append((no, "-", f"JSON 아님: {e}"))
            continue
        nid = row.get("news_id", "-")

        score = row.get("news_sent_0_10")
        # bool은 int의 하위 타입이라 따로 막는다
        if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 10:
            errors.append((no, nid, f"점수 {score!r} — 0–10 정수가 아님"))
        elif row.get("label") != band(score):
            errors.append((no, nid, f"label {row.get('label')!r} — 점수 {score}는 {band(score)!r}"))

        src, ev = news.get(nid), row.get("evidence")
        if src is None:
            errors.append((no, nid, "원문 CSV에 없는 news_id"))
        elif not ev or (ev not in src["headline"] and ev not in src["body_short"]):
            errors.append((no, nid, f"evidence가 원문에 그대로 없음: {row.get('evidence')!r}"))

    if errors:
        print(f"위반 {len(errors)}건")
        print("| 줄 | news_id | 이유 |")
        print("|---|---|---|")
        for no, nid, why in errors:
            print(f"| {no} | {nid} | {why} |")
        return 1
    print(f"위반 없음 — {len(lines)}줄 모두 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
