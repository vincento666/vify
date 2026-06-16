from collections.abc import Mapping, Sequence, Set as AbstractSet
import math
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
    "flight_status": (
        "航班动态",
        "航班状态",
        "起飞时间",
        "到达时间",
        "登机口",
        "接人",
        "是不是延误",
        "查航班",
        "航班现在",
        "到哪了",
        "到哪",
    ),
    "special_assistance": ("轮椅", "无障碍", "行动不便", "特殊协助", "优先登机"),
    "pet_cabin": ("宠物", "航空箱", "疫苗证明", "猫咪", "小型犬"),
    "irregular_flight": ("异常航班", "不正常航班", "备降", "保障方案", "签转", "非自愿", "延误四小时"),
    "membership_service": ("里程", "积分", "常旅客", "补登", "升舱券"),
}

HYBRID_SOP_PROFILES: dict[str, tuple[str, ...]] = {
    "flight_booking": (
        "航班",
        "机票",
        "飞机票",
        "出行",
        "合适航班",
        "可飞",
        "开会",
        "出差",
        "乘机人",
        "手机号",
        "联系方式",
    ),
    "fare_quote": ("票价", "价格", "多少钱", "报价", "预算", "贵", "便宜", "比价", "看看", "合适"),
    "group_booking": ("团队", "团体", "多人", "集体", "公司", "统一出票", "一起出行", "十个人", "二十个人"),
    "ancillary_sales": ("加购", "附加", "增值", "保险", "餐食", "贵宾厅", "接送机", "升舱"),
    "refund_ticket": ("退", "退回", "扣费", "手续费", "不飞", "取消", "退掉"),
    "change_flight": ("改", "换", "提前", "延后", "来不及", "改时间", "调整"),
    "passenger_info_change": ("填错", "写错", "更正", "改资料", "改信息", "证件", "姓名", "联系人"),
    "invoice_apply": ("报销", "凭证", "发票", "票据", "抬头", "税号", "行程单"),
    "baggage_service": ("箱子", "行李", "托运", "超重", "额度", "婴儿车", "运动器材"),
    "seat_checkin": ("座位", "坐一起", "靠窗", "过道", "登机牌", "线上办", "值机"),
    "flight_status": ("动态", "状态", "延误", "取消", "起飞", "到达", "登机口", "接人", "查航班", "到哪"),
    "special_assistance": ("老人", "孕妇", "轮椅", "受伤", "无障碍", "协助", "特殊服务"),
    "pet_cabin": ("宠物", "猫", "狗", "航空箱", "疫苗", "托运", "进客舱"),
    "irregular_flight": ("不正常", "异常", "延误", "取消", "备降", "非自愿", "保障", "补偿"),
    "membership_service": ("会员", "里程", "积分", "常旅客", "补登", "权益", "等级"),
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
        if _explicitly_denies_transaction(message):
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
            if matched or weak_matched:
                matched = matched or weak_matched
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
                continue
            hybrid = _hybrid_sop_candidate(sop_id, manifest, message)
            if hybrid is not None:
                candidates.append(hybrid)
        return candidates


def _hybrid_sop_candidate(sop_id: str, manifest: SopManifest, text: str) -> RouteCandidate | None:
    terms = _hybrid_profile_terms(sop_id, manifest)
    keyword_hits = tuple(term for term in terms if term and term in text)
    bm25_score = _bm25_lite_score(text, terms)
    vector_score = _char_vector_score(text, _hybrid_document(sop_id, manifest, terms))
    business_score, business_terms = _business_reference_score(sop_id, text)
    if not keyword_hits and business_score <= 0 and vector_score < 0.08:
        return None
    score = min(
        0.88,
        0.48
        + bm25_score * 0.16
        + vector_score * 0.22
        + business_score * 0.36
        + min(len(keyword_hits), 3) * 0.015,
    )
    if score < 0.62:
        return None
    matched_terms = tuple(dict.fromkeys((*business_terms, *keyword_hits[:4])))
    return RouteCandidate(
        candidate_id=f"sop:{sop_id}",
        candidate_type=CandidateType.SOP_INTENT,
        target_id=sop_id,
        display_name=manifest.display_name,
        source="sop_hybrid_recall",
        score=score,
        score_breakdown=ScoreBreakdown(
            keyword=round(bm25_score, 3),
            alias=round(business_score, 3),
            semantic=round(vector_score, 3),
        ),
        matched_terms=matched_terms,
        risk_level="MEDIUM",
        requires_classifier=True,
        reason="Hybrid SOP recall using keyword, BM25-lite, char-vector and business-reference signals",
        payload={
            "retrieval": {
                "mode": "keyword_bm25_char_vector_business_ref",
                "keywordScore": round(bm25_score, 4),
                "vectorScore": round(vector_score, 4),
                "businessReferenceScore": round(business_score, 4),
                "pool": "enabled_sop_manifests",
            }
        },
    )


def _hybrid_profile_terms(sop_id: str, manifest: SopManifest) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            (
                manifest.display_name,
                manifest.business_area,
                *manifest.trigger_keywords,
                *manifest.strong_trigger_keywords,
                *SEMANTIC_FIXTURES.get(sop_id, ()),
                *HYBRID_SOP_PROFILES.get(sop_id, ()),
            )
        )
    )


def _hybrid_document(sop_id: str, manifest: SopManifest, terms: Sequence[str]) -> str:
    return " ".join((sop_id, manifest.display_name, manifest.business_area, *terms))


def _bm25_lite_score(text: str, terms: Sequence[str]) -> float:
    if not text or not terms:
        return 0.0
    hits = [term for term in terms if term and term in text]
    if not hits:
        return 0.0
    normalizer = max(3, min(8, len(terms) // 4 or 3))
    return min(1.0, len(set(hits)) / normalizer)


def _char_vector_score(text: str, document: str) -> float:
    query = _char_ngram_counts(text)
    doc = _char_ngram_counts(document)
    if not query or not doc:
        return 0.0
    dot = sum(value * doc.get(key, 0) for key, value in query.items())
    query_norm = math.sqrt(sum(value * value for value in query.values()))
    doc_norm = math.sqrt(sum(value * value for value in doc.values()))
    if query_norm == 0 or doc_norm == 0:
        return 0.0
    return min(1.0, dot / (query_norm * doc_norm))


def _char_ngram_counts(text: str, n: int = 2) -> dict[str, int]:
    normalized = "".join(re.findall(r"[\w\u4e00-\u9fff]+", text.lower()))
    if len(normalized) < n:
        return {}
    counts: dict[str, int] = {}
    for index in range(0, len(normalized) - n + 1):
        gram = normalized[index : index + n]
        counts[gram] = counts.get(gram, 0) + 1
    return counts


def _business_reference_score(sop_id: str, text: str) -> tuple[float, tuple[str, ...]]:
    terms: list[str] = []
    score = 0.0

    has_route = _has_route_reference(text)
    has_time = _has_travel_time_reference(text)
    has_contact = _has_contact_or_passenger_reference(text)
    has_order = _has_order_reference(text)
    has_flight_object = any(term in text for term in ("航班", "机票", "飞机票"))

    def add(amount: float, term: str) -> None:
        nonlocal score
        score += amount
        terms.append(term)

    if sop_id == "flight_booking":
        if has_route:
            add(0.18, "business_ref:route")
        if has_time:
            add(0.10, "business_ref:travel_time")
        if has_contact:
            add(0.22, "business_ref:contact")
        if has_flight_object:
            add(0.10, "business_ref:flight_object")
        if any(term in text for term in ("出差", "开会", "旅行", "回家", "出行")):
            add(0.08, "business_ref:travel_purpose")
        if any(term in text for term in ("合适的航班", "有没有合适", "看下航班", "看看航班")):
            add(0.08, "business_ref:availability")
    elif sop_id == "fare_quote":
        if has_route:
            add(0.12, "business_ref:route")
        if has_time:
            add(0.06, "business_ref:travel_time")
        if any(term in text for term in ("票价", "价格", "多少钱", "预算", "贵", "便宜", "报价", "比价")):
            add(0.34, "business_ref:price")
    elif sop_id == "group_booking":
        if has_route:
            add(0.10, "business_ref:route")
        if has_time:
            add(0.06, "business_ref:travel_time")
        if re.search(r"(?:\d+|[一二三四五六七八九十两]{1,3})个?人", text) or any(
            term in text for term in ("团队", "团体", "多人", "集体", "公司")
        ):
            add(0.34, "business_ref:party_size")
    elif sop_id in {"refund_ticket", "change_flight", "invoice_apply", "baggage_service", "seat_checkin"}:
        if has_order:
            add(0.18, "business_ref:order")
        if has_contact:
            add(0.08, "business_ref:contact")
    elif sop_id == "flight_status":
        if any(term in text for term in ("延误", "取消", "到达", "起飞", "登机口", "动态", "状态", "晚点", "到哪", "查航班")):
            add(0.32, "business_ref:flight_status")
        if "航班现在" in text:
            add(0.14, "business_ref:flight_tracking")
        if has_route:
            add(0.08, "business_ref:route")
    elif sop_id == "special_assistance" and has_contact:
        add(0.06, "business_ref:passenger")
    elif sop_id == "pet_cabin" and has_flight_object:
        add(0.06, "business_ref:flight_object")
    return min(1.0, score), tuple(dict.fromkeys(terms))


def _has_route_reference(text: str) -> bool:
    city = r"[\u4e00-\u9fff]{2,8}"
    return bool(re.search(rf"{city}(?:飞|到|去|至){city}", text))


def _has_travel_time_reference(text: str) -> bool:
    return bool(
        re.search(r"(今天|明天|后天|大后天|下周|周[一二三四五六日天]|星期[一二三四五六日天]|上午|下午|晚上|早上|中午|凌晨)", text)
    )


def _has_contact_or_passenger_reference(text: str) -> bool:
    return bool(re.search(r"(?<!\d)1[3-9]\d{9}(?!\d)", text)) or any(term in text for term in ("乘机人", "旅客", "手机号", "联系人"))


def _has_order_reference(text: str) -> bool:
    return bool(re.search(r"[A-Z]{2}\d{3,}[-\d]*", text.upper())) or any(term in text for term in ("订单", "票号", "刚才那张票", "刚订"))


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


def _explicitly_denies_transaction(text: str) -> bool:
    if _looks_like_price_quote_request(text):
        return False
    denial_terms = ("不是要办理", "不是办理", "不办理", "不是要办", "不办", "先不", "现在不")
    consultation_terms = ("只是问", "只想问", "就想问", "想问", "咨询", "了解")
    return any(term in text for term in denial_terms) and any(term in text for term in consultation_terms)


def _looks_like_price_quote_request(text: str) -> bool:
    return any(term in text for term in ("票价", "价格", "多少钱", "报价", "预算", "贵不贵", "便宜"))
