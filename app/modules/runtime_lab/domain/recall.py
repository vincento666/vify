from collections.abc import Mapping, Sequence, Set as AbstractSet
import re
from typing import Any

from app.modules.runtime_lab.domain.candidates import CandidateType, RouteCandidate, ScoreBreakdown, select_top_candidates
from app.modules.runtime_lab.domain.sop import SopManifest

SEMANTIC_FIXTURES: dict[str, tuple[str, ...]] = {
    "flight_booking": ("订票", "订一张", "订机票", "订航班", "买票", "买机票", "出票", "可售航班", "一个成人", "经济舱"),
    "refund_ticket": ("退费", "票款", "取消行程", "退掉航班", "不飞了", "不去了", "能不能退", "退回来", "扣费"),
    "change_flight": ("换个航班", "改时间", "调整航班", "改日期"),
    "invoice_apply": ("报销", "凭证", "电子票据", "开票资料", "发票"),
    "baggage_service": ("托运", "行李额", "超重", "随身行李", "运动器材"),
    "seat_checkin": ("登机牌", "座位", "靠窗", "过道", "线上值机"),
    "flight_status": ("航班动态", "航班状态", "起飞时间", "到达时间", "登机口", "接人", "是不是延误"),
    "special_assistance": ("轮椅", "无障碍", "行动不便", "特殊协助", "优先登机"),
    "pet_cabin": ("宠物", "航空箱", "疫苗证明", "猫咪", "小型犬"),
    "irregular_flight": ("异常航班", "不正常航班", "备降", "保障方案", "签转", "非自愿", "延误四小时"),
    "membership_service": ("里程", "积分", "常旅客", "补登", "升舱券"),
}


class MockSemanticCandidateRecall:
    def __init__(self, manifests: dict[str, SopManifest]) -> None:
        self._manifests = manifests

    def recall(
        self,
        message: str,
        active_task: Mapping[str, Any] | None,
        suspended_tasks: Sequence[Mapping[str, Any]],
        enabled_sop_ids: AbstractSet[str] | None = None,
        top_k: int = 5,
    ) -> list[RouteCandidate]:
        candidates: list[RouteCandidate] = []
        if active_task is not None:
            candidates.append(self._active_candidate(active_task, message))
        candidates.extend(self._suspended_candidates(message, suspended_tasks))
        candidates.extend(self._sop_candidates(message, enabled_sop_ids, active_task))
        return select_top_candidates(candidates, top_k)

    def _active_candidate(self, active_task: Mapping[str, Any], message: str) -> RouteCandidate:
        task_id = str(active_task["id"])
        sop_id = str(active_task.get("sop_id") or "")
        score = 0.93 if _looks_like_active_collection_detail(message, sop_id) else 0.55
        matched_terms = ("collection_detail",) if score >= 0.9 else ()
        return RouteCandidate(
            candidate_id=f"active:{task_id}",
            candidate_type=CandidateType.ACTIVE_TASK_CONTINUE,
            target_id=task_id,
            display_name=f"Continue {sop_id}",
            source="mock_semantic_recall",
            score=score,
            score_breakdown=ScoreBreakdown(keyword=0.0, alias=0.0, semantic=score),
            matched_terms=matched_terms,
            risk_level="LOW",
            requires_classifier=True,
            reason="Active task continuation candidate in active context",
        )

    def _suspended_candidates(
        self,
        message: str,
        suspended_tasks: Sequence[Mapping[str, Any]],
    ) -> list[RouteCandidate]:
        candidates: list[RouteCandidate] = []
        for task in suspended_tasks:
            summary = str(task.get("resume_summary") or "")
            sop_id = str(task.get("sop_id") or "")
            manifest = self._manifests.get(sop_id)
            manifest_terms = (
                (manifest.display_name, *manifest.trigger_keywords)
                if manifest is not None
                else ()
            )
            terms = tuple(term for term in (summary, sop_id, *manifest_terms) if term and term in message)
            if not terms:
                if len(suspended_tasks) == 1 and _looks_like_suspended_followup_detail(message):
                    terms = ("implicit_followup_detail",)
                else:
                    continue
            if terms == ("implicit_followup_detail",):
                score = 0.74
            else:
                score = 0.92 if "继续" in message or "resume" in message.lower() else 0.72
            if terms == ("implicit_followup_detail",) and sop_id == "flight_status":
                score = 0.82
            if terms == ("implicit_followup_detail",) and sop_id != "flight_status":
                score = 0.68
            if score < 0.7:
                continue
            task_id = str(task["id"])
            candidates.append(
                RouteCandidate(
                    candidate_id=f"suspended:{task_id}",
                    candidate_type=CandidateType.SUSPENDED_TASK_RESUME,
                    target_id=task_id,
                    display_name=f"Resume {sop_id}",
                    source="mock_semantic_recall",
                    score=score,
                    score_breakdown=ScoreBreakdown(keyword=0.0, alias=0.0, semantic=score),
                    matched_terms=terms,
                    risk_level="LOW",
                    requires_classifier=True,
                    reason="Message overlaps suspended task resume summary",
                )
            )
        return candidates

    def _sop_candidates(
        self,
        message: str,
        enabled_sop_ids: AbstractSet[str] | None,
        active_task: Mapping[str, Any] | None,
    ) -> list[RouteCandidate]:
        if _looks_like_airport_facility_question(message):
            return []
        candidates: list[RouteCandidate] = []
        active_sop_id = str(active_task.get("sop_id") or "") if active_task is not None else ""
        for sop_id, manifest in self._manifests.items():
            if enabled_sop_ids is not None and sop_id not in enabled_sop_ids:
                continue
            if sop_id == active_sop_id and _negates_active_sop_reference(sop_id, message):
                continue
            matched = tuple(term for term in SEMANTIC_FIXTURES.get(sop_id, ()) if term in message)
            weak_matched = _weak_sop_terms(sop_id, message) if not matched else ()
            if not matched:
                if not weak_matched:
                    continue
                matched = weak_matched
            score = 0.78
            candidates.append(
                RouteCandidate(
                    candidate_id=f"sop:{sop_id}",
                    candidate_type=CandidateType.SOP_INTENT,
                    target_id=sop_id,
                    display_name=manifest.display_name,
                    source="mock_semantic_recall",
                    score=score,
                    score_breakdown=ScoreBreakdown(keyword=0.0, alias=0.0, semantic=score),
                    matched_terms=matched,
                    risk_level="LOW",
                    requires_classifier=True,
                    reason="Mock semantic fixture matched SOP intent",
                )
            )
        return candidates


def _weak_sop_terms(sop_id: str, message: str) -> tuple[str, ...]:
    if sop_id == "flight_booking" and _looks_like_booking_request(message):
        return ("weak_booking_request",)
    if sop_id == "refund_ticket" and _looks_like_refund_request(message):
        return ("weak_refund_request",)
    return ()


def _looks_like_booking_request(message: str) -> bool:
    text = message.strip()
    if not text:
        return False
    has_action = any(
        term in text
        for term in (
            "订",
            "预订",
            "订一张",
            "订个",
            "定票",
            "定机票",
            "定航班",
            "预定",
            "买",
            "购买",
            "购票",
            "出票",
            "安排一张",
            "安排个",
            "安排一下",
        )
    )
    has_object = any(term in text for term in ("航班", "机票", "飞机票"))
    if has_action and has_object:
        return True
    if ("票" in text or "航班" in text) and re.search(r"安排[^，。,.]{0,8}(一张|一个|个)", text):
        return True
    return bool(re.search(r"[\u4e00-\u9fff]{2,8}(飞|到|去)[\u4e00-\u9fff]{2,8}", text) and has_action)


def _looks_like_suspended_followup_detail(message: str) -> bool:
    text = message.strip()
    if not text:
        return False
    has_flight_no = any(prefix in text.upper() for prefix in ("CA", "MU", "CZ", "HU", "MF", "3U", "ZH", "SC"))
    has_detail_hint = any(term in text for term in ("刚订", "刚才", "这个", "那班", "航班号", "订单号"))
    return has_flight_no and has_detail_hint


def _looks_like_active_collection_detail(message: str, active_sop_id: str) -> bool:
    text = message.strip()
    if not text:
        return False
    if _mentions_other_business(text, active_sop_id):
        return False
    if re.search(r"(?<!\d)(1[3-9]\d{9})(?!\d)", text):
        return True
    if re.search(r"\d{15,18}[0-9Xx]?", text):
        return True
    if any(term in text for term in ("确认", "好的", "可以", "按这个", "提交", "办理")):
        return True
    return any(term in text for term in ("乘机人", "身份证", "护照", "手机号", "经济舱", "公务舱", "靠窗", "靠过道"))


def _mentions_other_business(text: str, active_sop_id: str) -> bool:
    if active_sop_id != "flight_booking" and _looks_like_booking_request(text):
        return True
    if active_sop_id != "refund_ticket" and _looks_like_refund_request(text):
        return True
    groups = {
        "flight_booking": ("订票", "订机票", "买机票", "出票", "预订", "定机票"),
        "refund_ticket": ("退票", "退费", "退回来", "能不能退", "不飞了"),
        "change_flight": ("改签", "改时间", "换个航班", "调整航班"),
        "invoice_apply": ("发票", "开票", "报销凭证"),
        "flight_status": ("航班动态", "航班状态", "延误", "到达时间", "起飞时间"),
    }
    for sop_id, terms in groups.items():
        if sop_id != active_sop_id and any(term in text for term in terms):
            return True
    return False


def _looks_like_refund_request(text: str) -> bool:
    if any(term in text for term in ("退票", "退款", "退机票", "退费", "取消行程", "不飞了")):
        return True
    return bool(re.search(r"(?:退|取消)[^，。,.]{0,10}(?:票|机票|航班)|(?:票|机票|航班)[^，。,.]{0,10}退", text))


def _negates_active_sop_reference(sop_id: str, text: str) -> bool:
    terms_by_sop = {
        "flight_booking": ("订票", "订机票", "机票预订", "预订", "出票"),
        "refund_ticket": ("退票", "退款", "退费"),
        "change_flight": ("改签", "改航班", "换航班"),
        "invoice_apply": ("发票", "开票"),
        "baggage_service": ("行李", "行李额"),
        "seat_checkin": ("值机", "选座"),
        "pet_cabin": ("宠物",),
    }
    terms = terms_by_sop.get(sop_id, ())
    if not terms:
        return False
    return any(re.search(f"(?:先)?不(?:补|继续|处理|办)?[^，。,.]{{0,8}}{re.escape(term)}", text) for term in terms)


def _looks_like_airport_facility_question(text: str) -> bool:
    facility_terms = ("机场", "候机楼", "柜台", "停车", "酒店", "打印店", "寄存", "WiFi", "wifi", "大巴", "贵宾楼")
    question_terms = ("吗", "么", "怎么", "哪里", "几点", "收费", "旁边", "附近", "有没有")
    return any(term in text for term in facility_terms) and any(term in text for term in question_terms)
