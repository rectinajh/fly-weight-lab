"""Decision surface: turn the evolved champion into one surfaced decision."""

from __future__ import annotations

from dataclasses import dataclass

from .genotype import Fly
from .twin import UserProfile


@dataclass
class Decision:
    headline: str
    action: str
    reason: str


def surface_decision(
    current: Fly | None,
    champion: Fly,
    plateau_detected: bool,
    profile: UserProfile,
) -> Decision:
    actions: list[str] = []
    reasons: list[str] = []

    if current is not None:
        if champion.calorie_target > current.calorie_target:
            actions.append(f"把每日热量目标从 {current.calorie_target} 上调到 {champion.calorie_target} kcal")
            reasons.append("继续压热量会进一步压低坚持度并触发代谢适应")
        if champion.late_night_rule and not current.late_night_rule:
            actions.append("允许一份固定的睡前加餐")
            reasons.append("对容易暴食的人，保留固定深夜加餐能降低暴食风险")
        if champion.refeed_schedule != "none" and current.refeed_schedule == "none":
            actions.append(f"每周安排一次计划内高热量日（{champion.refeed_schedule}）")
            reasons.append("计划内 refeed 能缓解长期节食的反弹压力")
        if champion.sleep_target > current.sleep_target:
            actions.append(f"先把睡眠补到 {champion.sleep_target} 小时")
            reasons.append("睡眠债会同时抬升暴食风险和降低坚持度")
        if champion.meal_window > current.meal_window:
            actions.append(f"把进食窗口放宽到 {champion.meal_window} 小时")
            reasons.append("过窄的进食窗口是暴食的触发源")

    if not actions:
        actions.append(f"锁定这套方案：{champion.describe()}")
        reasons.append("蜂群多代收敛后，这是坚持度与减脂效果综合最优的冠军")

    headline = "平台期已检测到，需要切换方案" if plateau_detected else "本周建议切换到这个方案"
    return Decision(
        headline=headline,
        action="；".join(actions[:2]),
        reason="。".join(reasons[:2]) + "。",
    )
