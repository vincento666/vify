from collections.abc import Mapping, Sequence, Set as AbstractSet
from typing import Any

from app.modules.runtime_lab.domain.candidates import CandidateType, RouteCandidate, ScoreBreakdown, select_top_candidates
from app.modules.runtime_lab.domain.sop import SopManifest, match_strong_trigger_template

RESUME_PHRASES = {"continue", "resume", "继续", "继续刚才", "继续第一个"}
REFUSAL_PHRASES = {"不用了", "不用", "不了", "先这样"}
HANDOFF_TRIGGER_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("USER_REQUEST", ("转人工", "人工客服", "找人工", "人工处理", "接人工", "转接客服", "客服人员")),
    ("COMPLAINT", ("投诉", "主管", "升级处理", "不满意")),
    ("COMPLIANCE", ("监管", "民航局")),
    ("SAFETY", ("报警", "安全事故")),
    ("UNSUPPORTED", ("这个机器人处理不了", "机器人无法处理", "无法办理", "不要机器人", "别机器人", "不是机器人")),
)


class ExplicitSignalDetector:
    def __init__(self, manifests: dict[str, SopManifest]) -> None:
        self._manifests = manifests

    def detect(
        self,
        message: str,
        active_task: Mapping[str, Any] | None,
        suspended_tasks: Sequence[Mapping[str, Any]],
        enabled_sop_ids: AbstractSet[str] | None = None,
        top_k: int = 5,
    ) -> list[RouteCandidate]:
        text = message.strip()
        candidates: list[RouteCandidate] = []
        handoff = self._handoff_candidate(text)
        if handoff is not None:
            candidates.append(handoff)
        refusal = self._refusal_candidate(text)
        if refusal is not None:
            candidates.append(refusal)
        candidates.extend(self._resume_candidates(text, suspended_tasks))
        candidates.extend(self._sop_candidates(text, active_task, enabled_sop_ids))
        return select_top_candidates(candidates, top_k)

    def _handoff_candidate(self, text: str) -> RouteCandidate | None:
        for reason_code, terms in HANDOFF_TRIGGER_GROUPS:
            matched_terms = tuple(term for term in terms if term in text)
            if not matched_terms:
                continue
            return RouteCandidate(
                candidate_id=f"handoff:{reason_code}",
                candidate_type=CandidateType.HANDOFF_TO_HUMAN,
                target_id=reason_code,
                display_name="Human handoff",
                source="explicit_signal",
                score=1.0,
                score_breakdown=ScoreBreakdown(keyword=1.0, alias=0.0, semantic=0.0),
                matched_terms=matched_terms,
                risk_level="HIGH",
                requires_classifier=False,
                reason=f"Explicit handoff trigger: {reason_code}",
            )
        return None

    def _refusal_candidate(self, text: str) -> RouteCandidate | None:
        matched = next((phrase for phrase in REFUSAL_PHRASES if phrase in text), None)
        if matched is None:
            return None
        if _is_embedded_business_negation(text):
            return None
        return RouteCandidate(
            candidate_id="clarify:no_op",
            candidate_type=CandidateType.CLARIFY,
            target_id="clarify:no_op",
            display_name="No-op clarification",
            source="explicit_signal",
            score=1.0,
            score_breakdown=ScoreBreakdown(keyword=1.0, alias=0.0, semantic=0.0),
            matched_terms=(matched,),
            risk_level="LOW",
            requires_classifier=False,
            reason="User sent explicit no-op or refusal phrase",
        )

    def _resume_candidates(
        self,
        text: str,
        suspended_tasks: Sequence[Mapping[str, Any]],
    ) -> list[RouteCandidate]:
        normalized = text.lower()
        if len(suspended_tasks) != 1:
            return []
        task = suspended_tasks[0]
        sop_id = str(task.get("sop_id") or "")
        described_resume = self._looks_like_single_suspended_resume(text, sop_id)
        if normalized not in RESUME_PHRASES and not described_resume:
            return []
        task_id = str(task["id"])
        return [
            RouteCandidate(
                candidate_id=f"suspended:{task_id}",
                candidate_type=CandidateType.SUSPENDED_TASK_RESUME,
                target_id=task_id,
                display_name=f"Resume {sop_id}",
                source="explicit_signal",
                score=1.1 if described_resume else 0.9,
                score_breakdown=ScoreBreakdown(keyword=1.1 if described_resume else 0.9, alias=0.0, semantic=0.0),
                matched_terms=(text,),
                risk_level="LOW",
                requires_classifier=False,
                reason="Explicit resume phrase resolved to the single suspended task",
            )
        ]

    def _looks_like_single_suspended_resume(self, text: str, sop_id: str) -> bool:
        if "继续" not in text and "resume" not in text.lower():
            return False
        if not any(term in text for term in ("刚才", "刚刚", "之前", "中断", "暂停", "上一个")):
            return False
        manifest = self._manifests.get(sop_id)
        if manifest is None:
            return True
        terms = (manifest.display_name, *manifest.trigger_keywords, *manifest.strong_trigger_keywords)
        return any(term and term in text for term in terms) or len(text) <= 12

    def _sop_candidates(
        self,
        text: str,
        active_task: Mapping[str, Any] | None,
        enabled_sop_ids: AbstractSet[str] | None,
    ) -> list[RouteCandidate]:
        if _looks_like_airport_facility_question(text):
            return []
        candidates: list[RouteCandidate] = []
        for manifest in self._manifests.values():
            if enabled_sop_ids is not None and manifest.sop_id not in enabled_sop_ids:
                continue
            strong = match_strong_trigger_template(text, manifest)
            if strong is not None:
                score = _boost_transactional_sop_score(text, manifest.sop_id, strong.score)
                candidates.append(
                    self._sop_candidate(
                        manifest,
                        score=score,
                        breakdown=ScoreBreakdown(keyword=score, alias=0.0, semantic=0.0),
                        matched_terms=strong.matched_terms,
                        reason=f"Matched strong trigger template: {strong.template_id}",
                        requires_classifier=active_task is not None,
                    )
                )
                continue
            aliases = tuple(term for term in manifest.trigger_keywords if term not in manifest.strong_trigger_keywords)
            alias = self._matched_term(text, aliases)
            if alias is not None:
                candidates.append(
                    self._sop_candidate(
                        manifest,
                        score=0.85,
                        breakdown=ScoreBreakdown(keyword=0.0, alias=0.85, semantic=0.0),
                        matched_terms=(alias,),
                        reason="Configured SOP alias",
                        requires_classifier=True,
                    )
                )
        return candidates

    def _sop_candidate(
        self,
        manifest: SopManifest,
        score: float,
        breakdown: ScoreBreakdown,
        matched_terms: tuple[str, ...],
        reason: str,
        requires_classifier: bool,
    ) -> RouteCandidate:
        return RouteCandidate(
            candidate_id=f"sop:{manifest.sop_id}",
            candidate_type=CandidateType.SOP_INTENT,
            target_id=manifest.sop_id,
            display_name=manifest.display_name,
            source="explicit_signal",
            score=score,
            score_breakdown=breakdown,
            matched_terms=matched_terms,
            risk_level="LOW",
            requires_classifier=requires_classifier,
            reason=reason,
        )

    def _matched_term(self, text: str, terms: Sequence[str]) -> str | None:
        return next((term for term in terms if term and term in text), None)


def _is_embedded_business_negation(text: str) -> bool:
    return any(phrase in text for phrase in ("不用买票", "不用出票", "暂时不用买票", "先不用买票", "先不出票"))


def _looks_like_airport_facility_question(text: str) -> bool:
    facility_terms = ("机场", "候机楼", "柜台", "停车", "酒店", "打印店", "寄存", "WiFi", "wifi", "大巴", "贵宾楼")
    question_terms = ("吗", "么", "怎么", "哪里", "几点", "收费", "旁边", "附近", "有没有")
    return any(term in text for term in facility_terms) and any(term in text for term in question_terms)


def _boost_transactional_sop_score(text: str, sop_id: str, score: float) -> float:
    if not _message_requests_transaction(text):
        return score
    if sop_id == "flight_booking" and (
        _looks_like_group_booking_context(text)
        or _looks_like_ancillary_context(text)
        or _explicitly_denies_booking(text)
    ):
        return score
    if sop_id in {"ancillary_sales", "seat_checkin"} and _looks_like_membership_context(text):
        return score
    terms_by_sop = {
        "flight_booking": ("订", "定", "买票", "购票", "出票", "机票"),
        "refund_ticket": ("退票", "退款", "退费", "取消行程"),
        "change_flight": ("改签", "换航班", "改航班", "改日期", "改时间"),
        "ancillary_sales": ("加购", "增值服务", "附加服务", "附加产品", "贵宾厅", "保险", "餐食", "接送机", "升舱券"),
        "invoice_apply": ("开发票", "开票", "发票", "报销凭证"),
        "baggage_service": ("加购", "购买行李", "加行李", "托运行李", "行李额"),
        "seat_checkin": ("值机", "选座", "登机牌"),
        "pet_cabin": ("宠物乘机", "宠物托运", "猫", "狗", "宠物"),
        "special_assistance": ("轮椅", "特殊协助", "无障碍"),
        "membership_service": ("里程", "积分", "会员", "补登"),
    }
    terms = terms_by_sop.get(sop_id, ())
    if terms and any(term in text for term in terms):
        return max(score, 1.2)
    return score


def _looks_like_group_booking_context(text: str) -> bool:
    group_terms = ("团队", "团体", "多人", "集体", "团建", "人数比较多", "十个人", "二十个人")
    return any(term in text for term in group_terms)


def _looks_like_ancillary_context(text: str) -> bool:
    ancillary_terms = ("加购", "增值服务", "附加服务", "附加产品", "贵宾厅", "保险", "餐食", "接送机", "升舱券")
    return any(term in text for term in ancillary_terms)


def _looks_like_membership_context(text: str) -> bool:
    membership_terms = ("会员", "里程", "积分", "常旅客", "补登", "会员等级", "会员服务")
    return any(term in text for term in membership_terms)


def _explicitly_denies_booking(text: str) -> bool:
    return any(term in text for term in ("不出票", "不用买票", "暂时不用买票", "先不用买票", "先不出票"))


def _message_requests_transaction(text: str) -> bool:
    if _explicitly_denies_transaction(text):
        return False
    action_terms = ("帮我", "我要", "我想", "办理", "申请", "提交", "现在就", "直接")
    return any(term in text for term in action_terms)


def _explicitly_denies_transaction(text: str) -> bool:
    denial_terms = ("不是要办理", "不是办理", "不办理", "不是要办", "不办", "先不", "现在不")
    consultation_terms = ("只是问", "只想问", "就想问", "想问", "咨询", "了解")
    return any(term in text for term in denial_terms) and any(term in text for term in consultation_terms)
