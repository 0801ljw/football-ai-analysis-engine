from __future__ import annotations

from app.compliance import assert_compliant


def render_content_copy(
    match: dict,
    probabilities: dict[str, float],
    score_candidates: list[dict],
    market_notes: list[str],
    risk_flags: list[str],
) -> dict:
    """Create compliant Xiaohongshu-style Chinese copy for research content."""

    home = match["home"]
    away = match["away"]
    top_score = score_candidates[0]["score"]
    title = f"{home} vs {away}：一份赛前概率推演笔记"
    body_lines = [
        f"这场 {match['stage']} 的核心看点，是三项结果概率是否足够分散。",
        f"demo 模型给出的主胜/平局/客胜观察值为 {probabilities['home']:.0%} / {probabilities['draw']:.0%} / {probabilities['away']:.0%}。",
        f"比分候选 Top1 是 {top_score}，只代表当前样例参数下的高频区间，不代表确定结果。",
        "内容定位：概率推演、数据观察、娱乐研究。",
        "风险提示：demo 数据不是实时盘口，也不构成任何行动建议；后续接入真实引擎后仍需标注来源和更新时间。",
        "观察点：",
    ]
    body_lines.extend(f"- {note}" for note in market_notes)
    body_lines.append("风险项：")
    body_lines.extend(f"- {flag}" for flag in risk_flags)

    copy = {
        "title": title,
        "body": "\n".join(body_lines),
        "hashtags": ["世界杯", "足球数据", "概率推演", "数据观察", "娱乐研究"],
    }
    compliance = assert_compliant(" ".join([copy["title"], copy["body"], " ".join(copy["hashtags"])]))
    if not compliance["passed"]:
        copy["body"] += "\n\n合规提示：当前文案需要人工复核后再发布。"
    return copy
