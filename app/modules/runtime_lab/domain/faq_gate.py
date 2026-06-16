from collections.abc import Sequence
from dataclasses import dataclass
import re
from typing import Any, Protocol

from app.modules.runtime_lab.domain.router import RouteDecision


class FaqAnswerGate(Protocol):
    def propose(
        self,
        message: str,
        *,
        active_task: dict[str, Any] | None,
        suspended_tasks: list[dict[str, Any]],
    ) -> "FaqAnswerProposal | None":
        ...


class FaqKnowledgeFacade(Protocol):
    def search_context(
        self,
        knowledge_base_id: int,
        query: str,
        top_k: int,
        retrieval_mode: str | None = None,
        score_threshold: float | None = None,
        rerank: bool | None = None,
    ) -> Sequence[Any]:
        ...


@dataclass(frozen=True)
class FaqAnswerEvidence:
    faq_id: int
    question: str
    answer: str
    score: float
    match_type: str
    source: str
    matched_terms: tuple[str, ...] = ()
    knowledge_base_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "faqId": self.faq_id,
            "question": self.question,
            "answer": self.answer,
            "score": self.score,
            "matchType": self.match_type,
            "source": self.source,
            "matchedTerms": list(self.matched_terms),
        }
        if self.knowledge_base_id is not None:
            payload["knowledgeBaseId"] = self.knowledge_base_id
        return payload


@dataclass(frozen=True)
class FaqAnswerProposal:
    answer: str
    confidence: float
    margin: float
    evidence: FaqAnswerEvidence
    source_layer: str = "faq_exact"
    reason_code: str = "EXACT_MATCH"

    def to_route_decision(self) -> RouteDecision:
        return RouteDecision(
            action="ANSWER_FAQ",
            reason="Exact FAQ accepted before SOP arbitration",
            faq_answer={
                "sourceLayer": self.source_layer,
                "reasonCode": self.reason_code,
                "answer": self.answer,
                "confidence": self.confidence,
                "margin": self.margin,
                "mutatesSopState": False,
                "evidence": self.evidence.to_dict(),
            },
        )


class FaqExactAnswerGate:
    def __init__(
        self,
        knowledge_facade: FaqKnowledgeFacade,
        knowledge_base_ids: Sequence[int],
        *,
        top_k: int = 3,
        keyword_min_score: float = 1.2,
        keyword_min_margin: float = 0.15,
    ) -> None:
        self._knowledge_facade = knowledge_facade
        self._knowledge_base_ids = tuple(int(knowledge_base_id) for knowledge_base_id in knowledge_base_ids)
        self._top_k = top_k
        self._keyword_min_score = keyword_min_score
        self._keyword_min_margin = keyword_min_margin

    def propose(
        self,
        message: str,
        *,
        active_task: dict[str, Any] | None,
        suspended_tasks: list[dict[str, Any]],
    ) -> FaqAnswerProposal | None:
        del active_task, suspended_tasks
        hits = self._faq_hits(message)
        if not hits:
            return None
        best = hits[0]
        second_score = _score(hits[1]) if len(hits) > 1 else 0.0
        margin = max(0.0, _score(best) - second_score)
        match_type = _match_type(best)
        if match_type == "EXACT":
            confidence = 1.0
            reason_code = "EXACT_MATCH"
        elif _score(best) >= self._keyword_min_score and margin >= self._keyword_min_margin:
            confidence = min(0.99, _score(best) / 2.0)
            reason_code = "KEYWORD_HIGH_CONFIDENCE"
        else:
            return None
        return FaqAnswerProposal(
            answer=_answer(best),
            confidence=confidence,
            margin=margin,
            reason_code=reason_code,
            evidence=FaqAnswerEvidence(
                faq_id=_faq_id(best),
                question=_question(best),
                answer=_answer(best),
                score=_score(best),
                match_type=match_type,
                source="structured_faq",
                matched_terms=(_question(best),),
                knowledge_base_id=_knowledge_base_id(best),
            ),
        )

    def _faq_hits(self, message: str) -> list[Any]:
        hits: list[Any] = []
        for knowledge_base_id in self._knowledge_base_ids:
            for result in self._knowledge_facade.search_context(
                knowledge_base_id,
                message,
                top_k=self._top_k,
                retrieval_mode="keyword",
                score_threshold=None,
                rerank=False,
            ):
                if _source_type(result) != "FAQ":
                    continue
                if _match_type(result) not in {"EXACT", "KEYWORD", "HYBRID"}:
                    continue
                hits.append(_with_knowledge_base_id(result, knowledge_base_id))
        return sorted(hits, key=lambda hit: (-_score(hit), _faq_id(hit)))


class CompositeFaqAnswerGate:
    def __init__(self, gates: Sequence[FaqAnswerGate]) -> None:
        self._gates = tuple(gates)

    def propose(
        self,
        message: str,
        *,
        active_task: dict[str, Any] | None,
        suspended_tasks: list[dict[str, Any]],
    ) -> FaqAnswerProposal | None:
        for gate in self._gates:
            proposal = gate.propose(message, active_task=active_task, suspended_tasks=suspended_tasks)
            if proposal is not None:
                return proposal
        return None


class RuntimeAirlineFaqGate:
    def __init__(self, entries: Sequence["RuntimeAirlineFaqEntry"] | None = None) -> None:
        self._entries = tuple(entries or RUNTIME_AIRLINE_FAQ_ENTRIES)

    def propose(
        self,
        message: str,
        *,
        active_task: dict[str, Any] | None,
        suspended_tasks: list[dict[str, Any]],
    ) -> FaqAnswerProposal | None:
        del active_task, suspended_tasks
        text = message.strip()
        if not _runtime_faq_looks_like_question(text):
            return None
        exact_catalog_match = any(
            _normalize_faq_text(text) == _normalize_faq_text(entry.question)
            for entry in self._entries
        )
        if _runtime_faq_looks_like_irregular_claim_question(text) and not exact_catalog_match:
            return None
        if _runtime_faq_looks_like_document_comparison(text):
            return None
        if _runtime_faq_looks_like_transaction_request(text) and not exact_catalog_match:
            return None
        scored = [
            (entry.score(text), entry)
            for entry in self._entries
        ]
        scored = [(score, entry) for score, entry in scored if score > 0]
        if not scored:
            return None
        scored.sort(key=lambda item: (-item[0], item[1].faq_id))
        best_score, best = scored[0]
        competing_score = next(
            (
                score
                for score, entry in scored[1:]
                if entry.reason_code != best.reason_code
                and not _runtime_faq_more_specific_than(best, entry)
                and not _runtime_faq_same_topic_family(best, entry)
            ),
            0.0,
        )
        margin = max(0.0, best_score - competing_score)
        if best_score < 1.0 or margin < 0.2:
            return None
        return FaqAnswerProposal(
            answer=best.answer,
            confidence=min(0.99, 0.72 + best_score * 0.08),
            margin=margin,
            source_layer="runtime_airline_faq",
            reason_code=best.reason_code,
            evidence=FaqAnswerEvidence(
                faq_id=best.faq_id,
                question=best.question,
                answer=best.answer,
                score=best_score,
                match_type="RUNTIME_KEYWORD",
                source="runtime_airline_faq",
                matched_terms=best.matched_terms(text),
            ),
        )


@dataclass(frozen=True)
class RuntimeAirlineFaqEntry:
    faq_id: int
    reason_code: str
    question: str
    answer: str
    required_terms: tuple[str, ...]
    optional_terms: tuple[str, ...] = ()

    def score(self, message: str) -> float:
        matched_required = self.matched_required(message)
        if len(matched_required) < len(self.required_terms):
            return 0.0
        optional_score = len(self.matched_optional(message)) * 0.25
        question_bonus = 0.2 if _runtime_faq_looks_like_question(message) else 0.0
        exact_bonus = 3.0 if _normalize_faq_text(message) == _normalize_faq_text(self.question) else 0.0
        contains_bonus = 1.0 if _normalize_faq_text(self.question) in _normalize_faq_text(message) else 0.0
        return float(len(matched_required)) + optional_score + question_bonus + exact_bonus + contains_bonus

    def matched_terms(self, message: str) -> tuple[str, ...]:
        return (*self.matched_required(message), *self.matched_optional(message))

    def matched_required(self, message: str) -> tuple[str, ...]:
        return tuple(term for term in self.required_terms if term in message)

    def matched_optional(self, message: str) -> tuple[str, ...]:
        return tuple(term for term in self.optional_terms if term in message)


_BASE_RUNTIME_AIRLINE_FAQ_ENTRIES: tuple[RuntimeAirlineFaqEntry, ...] = (
    RuntimeAirlineFaqEntry(
        34001,
        "CHILD_TICKET_REFUND",
        "儿童票可以退吗？",
        "儿童票如未使用通常可按客票规则申请退票，具体手续费以出票航司和票价规则为准。",
        ("儿童票", "退"),
        ("返钱", "退款", "票款"),
    ),
    RuntimeAirlineFaqEntry(
        34002,
        "REFUND_ARRIVAL_TIME",
        "退票款多久到账？",
        "退票提交后通常会在 7-15 个工作日原路退回，银行或支付渠道处理时间可能略有差异。",
        ("退", "到账"),
        ("退款", "票款", "多久", "几天"),
    ),
    RuntimeAirlineFaqEntry(
        34003,
        "CHANGE_FEE_RULE",
        "改签手续费怎么算？",
        "改签费用一般由票价规则、舱位差价和改签时间共同决定，提交前会展示预计差价和手续费。",
        ("改签", "手续费"),
        ("差价", "费用", "怎么算"),
    ),
    RuntimeAirlineFaqEntry(
        34004,
        "CHECKIN_TIME",
        "值机什么时候开放？",
        "多数国内航班线上值机通常在起飞前 24-48 小时开放，具体以航司和机场规则为准。",
        ("值机", "开放"),
        ("什么时候", "多久", "提前"),
    ),
    RuntimeAirlineFaqEntry(
        34009,
        "CHECKIN_TIME",
        "起飞前多久可以值机？",
        "多数国内航班线上值机通常在起飞前 24-48 小时开放，具体以航司和机场规则为准。",
        ("值机", "多久"),
        ("起飞", "提前", "可以"),
    ),
    RuntimeAirlineFaqEntry(
        34005,
        "BAGGAGE_ALLOWANCE",
        "托运行李额怎么看？",
        "免费托运行李额与航司、航线、舱位和会员等级有关，可提供订单或航班信息后查询。",
        ("行李", "额"),
        ("托运", "免费", "多少", "怎么看"),
    ),
    RuntimeAirlineFaqEntry(
        34006,
        "DELAY_CERTIFICATE",
        "延误证明怎么开？",
        "航班延误证明通常可在航司官方渠道、机场柜台或客服渠道申请，需提供航班号和乘机信息。",
        ("延误", "证明"),
        ("怎么开", "开具", "申请"),
    ),
    RuntimeAirlineFaqEntry(
        34007,
        "INVOICE_TIMING",
        "电子发票多久能开？",
        "电子发票一般在行程完成或票款入账后申请，提交抬头后通常可在较短时间内生成。",
        ("发票", "多久"),
        ("电子", "开票", "报销"),
    ),
    RuntimeAirlineFaqEntry(
        34010,
        "INVOICE_TIMING",
        "发票什么时候能开？",
        "电子发票一般在行程完成或票款入账后申请，提交抬头后通常可在较短时间内生成。",
        ("发票", "什么时候"),
        ("开票", "报销", "能开"),
    ),
    RuntimeAirlineFaqEntry(
        34011,
        "CHANGE_FEE_RULE",
        "改签要补差价吗？",
        "改签费用一般由票价规则、舱位差价和改签时间共同决定，提交前会展示预计差价和手续费。",
        ("改签", "差价"),
        ("补", "费用", "手续费"),
    ),
    RuntimeAirlineFaqEntry(
        34008,
        "PET_CABIN_DOCS",
        "宠物乘机需要什么材料？",
        "宠物乘机通常需要提前申请，并准备检疫证明、疫苗证明、合规航空箱等材料。",
        ("宠物", "材料"),
        ("猫", "狗", "托运", "客舱", "证明"),
    ),
    RuntimeAirlineFaqEntry(
        34012,
        "IRREGULAR_DELAY_COMPENSATION",
        "延误四小时通常怎么赔？",
        "延误补偿需按航司不正常航班政策、延误原因和航线规则判断。",
        ("延误", "赔"),
        ("四小时", "规则", "通常"),
    ),
    RuntimeAirlineFaqEntry(
        34013,
        "GROUP_TICKET_PARTIAL_CHANGE_FEE",
        "团队票临时少一个人手续费怎么算？",
        "团队票临时减少人数需看团队协议、出票状态和剩余人数是否影响整体报价，手续费或补差以协议为准。",
        ("团队票", "少一个人"),
        ("手续费", "规则", "人数", "临时"),
    ),
)


_RUNTIME_AIRLINE_FAQ_SCENE_SPECS: tuple[tuple[str, str, tuple[tuple[str, str, tuple[str, ...], tuple[str, ...]], ...]], ...] = (
    (
        "FLIGHT_BOOKING",
        "预订",
        (
            ("订票需要提前多久？", "国内航班通常可提前数周至数月预订，旺季和热门航线建议尽早锁定价格。", ("订票", "提前"), ("多久", "预订")),
            ("临时买当天机票还能出票吗？", "当天航班只要航司仍有可售舱位并满足截载时间，一般可以出票。", ("当天", "出票"), ("临时", "机票")),
            ("没有身份证能先预订机票吗？", "国内机票通常需要有效身份证件信息，证件不完整会影响出票和安检。", ("身份证", "预订"), ("证件", "出票")),
            ("儿童和成人一起订票有什么规则？", "儿童票需绑定同行成人信息，年龄、证件和票价规则以航司要求为准。", ("儿童", "订票"), ("成人", "规则")),
            ("同一订单可以订多人机票吗？", "同一订单通常可以预订多名乘机人，但人数上限和舱位一致性以渠道规则为准。", ("订单", "多人"), ("机票", "一起")),
            ("预订后多久必须支付？", "支付时限由航司和渠道返回的价格锁定时间决定，超时可能自动取消占位。", ("预订", "支付"), ("多久", "时限")),
            ("航班起飞前多久停止出票？", "停止出票时间受航司截载、渠道和机场保障影响，临近起飞建议尽快确认。", ("停止出票", "起飞"), ("多久", "航班")),
        ),
    ),
    (
        "FARE_QUOTE",
        "票价",
        (
            ("机票价格为什么一直变？", "机票价格会随舱位库存、销售策略、出行日期和退改规则实时变化。", ("价格", "变"), ("票价", "机票")),
            ("票价里包含机场建设费吗？", "国内机票展示价通常会区分票面价、机建燃油等税费，支付前应以明细为准。", ("票价", "机场建设费"), ("税费", "包含")),
            ("儿童票价是成人票的一半吗？", "儿童票价不一定固定为成人票一半，具体以航司儿童票规则和舱位价格为准。", ("儿童", "票价"), ("成人", "一半")),
            ("学生票机票有优惠吗？", "学生机票优惠不是所有航司和航线都有，需看航司活动和证件校验要求。", ("学生", "优惠"), ("机票", "票价")),
            ("往返票一定比单程便宜吗？", "往返票不一定更便宜，价格取决于航线、舱位库存和促销规则。", ("往返", "单程"), ("便宜", "价格")),
            ("同一航班不同舱位价格差在哪？", "不同舱位通常对应不同价格、退改签条件、里程累积和服务权益。", ("舱位", "价格"), ("差", "权益")),
            ("票价查询结果能保留多久？", "票价查询结果一般不保证长期保留，未支付前价格和舱位都可能变化。", ("票价", "保留"), ("多久", "查询")),
        ),
    ),
    (
        "GROUP_BOOKING",
        "团队票",
        (
            ("多少人可以申请团队机票？", "团队机票人数门槛由航司定义，常见为 10 人或以上，具体以航线规则为准。", ("团队", "多少人"), ("申请", "机票")),
            ("团队票可以统一出票吗？", "团队票通常支持统一报价和统一出票，但姓名名单提交时限需按航司要求执行。", ("团队票", "统一出票"), ("名单", "报价")),
            ("团队票能不能部分退票？", "团队票部分退票要看团队协议、出票状态和航司规则，可能影响整体价格。", ("团队票", "部分退票"), ("规则", "价格")),
            ("团队票退票手续费怎么算？", "团队票退票手续费通常按团队协议和航司退票规则计算，可能与散客票不同。", ("团队票", "退票", "手续费"), ("怎么算", "规则")),
            ("团队名单最晚什么时候提交？", "团队名单提交时限由航司给出，逾期可能导致占位取消或价格变化。", ("团队", "名单"), ("什么时候", "提交")),
            ("团队票可以改签几个人吗？", "团队票改签部分成员通常需要看协议是否允许以及剩余舱位情况。", ("团队票", "改签"), ("几个人", "部分")),
            ("团队票付款后还能改人数吗？", "付款后改人数可能触发重新报价、补差或取消规则，需以团队协议为准。", ("团队票", "人数"), ("付款", "改")),
        ),
    ),
    (
        "ANCILLARY",
        "增值服务",
        (
            ("买完票以后还能加购餐食吗？", "多数航司支持出票后加购餐食，但需满足航班、餐食库存和截止时间要求。", ("加购", "餐食"), ("买完票", "还能")),
            ("贵宾厅服务可以单独买吗？", "贵宾厅服务是否可单独购买取决于机场、航司和会员权益。", ("贵宾厅", "单独买"), ("服务", "购买")),
            ("接送机服务取消后能退款吗？", "接送机服务退款规则以服务商条款为准，通常与机票退票规则分开。", ("接送机", "退款"), ("取消", "规则")),
            ("航空保险和机票一起退吗？", "航空保险是否随票退还需看保险产品条款，可能需要单独申请。", ("保险", "退"), ("机票", "一起")),
            ("餐食加购最晚什么时候截止？", "餐食加购截止时间通常早于航班起飞，具体以航司或供应商规则为准。", ("餐食", "截止"), ("最晚", "加购")),
            ("增值服务发票和机票发票一样吗？", "增值服务发票可能由不同服务方开具，抬头和税目以实际服务为准。", ("增值服务", "发票"), ("一样", "机票")),
            ("加购服务未使用可以退吗？", "未使用的加购服务能否退款取决于服务类型和购买条款。", ("加购服务", "退"), ("未使用", "可以")),
        ),
    ),
    (
        "REFUND",
        "退票",
        (
            ("退票手续费怎么算？", "退票手续费由票价规则、起飞前时间和客票使用状态共同决定。", ("退票", "手续费"), ("怎么算", "费用")),
            ("退票款一般多久到账？", "退票款通常会在 7-15 个工作日原路退回，实际时间受支付渠道影响。", ("退票款", "到账"), ("多久", "一般")),
            ("航班取消退票还扣手续费吗？", "航班取消等非自愿原因通常可按非自愿规则处理，是否免手续费以航司判定为准。", ("航班取消", "退票"), ("手续费", "非自愿")),
            ("已经值机还能退票吗？", "已值机客票退票前可能需要先取消值机，能否退票取决于航司规则。", ("值机", "退票"), ("已经", "还能")),
            ("儿童票退票和成人一样吗？", "儿童票退票规则可能与成人票不同，具体以出票航司和票价条件为准。", ("儿童票", "退票"), ("成人", "一样")),
            ("部分航段飞了剩余航段能退吗？", "已使用部分航段后，剩余航段是否可退需按客票顺序使用和票价规则判断。", ("剩余航段", "退"), ("部分", "飞了")),
            ("退票后行程单还能用来报销吗？", "退票后原行程单通常需作废或冲销，报销应以最终有效凭证为准。", ("退票", "行程单"), ("报销", "作废")),
        ),
    ),
    (
        "CHANGE",
        "改签",
        (
            ("改签手续费一般怎么算？", "改签手续费由票价规则、舱位差价和改签时间共同决定。", ("改签", "手续费"), ("怎么算", "差价")),
            ("改签通常要补差价吗？", "如新航班价格高于原票，通常需要补差价；低于原票是否退差取决于规则。", ("改签", "差价"), ("补", "要")),
            ("改签后还能再改一次吗？", "是否允许多次改签取决于票价规则，部分优惠票可能限制次数。", ("改签", "再改"), ("一次", "次数")),
            ("航班延误可以免费改签吗？", "航班延误等非自愿情形可能支持免费改签，需以航司非自愿政策为准。", ("延误", "改签"), ("免费", "航班")),
            ("改签到其他城市可以吗？", "是否可改到其他城市取决于客票航线规则，通常同航线更容易处理。", ("改签", "其他城市"), ("可以", "航线")),
            ("改签和升舱有什么区别？", "改签主要变更航班时间或航段，升舱主要变更舱等和服务权益。", ("改签", "升舱"), ("区别", "舱")),
            ("起飞后还能改签吗？", "起飞后改签限制更严格，需看是否误机、客票规则和航司政策。", ("起飞后", "改签"), ("还能", "误机")),
        ),
    ),
    (
        "PASSENGER_INFO",
        "资料修改",
        (
            ("姓名写错一个字能改吗？", "姓名错误能否修改取决于错误类型、证件一致性和航司规则，可能需重新出票。", ("姓名", "写错"), ("一个字", "修改")),
            ("证件号错了一位怎么办？", "证件号错误需尽快联系出票渠道或航司确认是否可更正。", ("证件号", "错"), ("一位", "怎么办")),
            ("手机号填错会影响登机吗？", "手机号一般不直接影响登机，但会影响通知接收和部分服务办理。", ("手机号", "填错"), ("登机", "影响")),
            ("护照换新后机票信息要改吗？", "国际或地区航班证件更换后通常需确认客票证件信息是否一致。", ("护照", "换新"), ("机票", "信息")),
            ("乘机人可以换成别人吗？", "机票通常实名制，不支持直接换乘机人，需退票重购或按规则处理。", ("乘机人", "换成别人"), ("实名", "可以")),
            ("姓名拼音顺序错了能登机吗？", "姓名拼音顺序错误是否影响登机需看航司和证件核验规则。", ("拼音", "顺序"), ("姓名", "登机")),
            ("联系人信息和乘机人信息一样吗？", "联系人用于通知接收，乘机人信息用于出票和安检，两者用途不同。", ("联系人", "乘机人"), ("一样", "信息")),
        ),
    ),
    (
        "INVOICE",
        "发票",
        (
            ("电子发票一般多久能开？", "电子发票一般在行程完成或票款入账后申请，生成时间以渠道为准。", ("电子发票", "多久"), ("开", "报销")),
            ("机票行程单和发票有什么区别？", "行程单是航空运输电子客票报销凭证，发票则多用于增值服务或其他产品。", ("行程单", "发票"), ("区别", "机票")),
            ("发票抬头写错还能改吗？", "发票抬头错误能否修改取决于开票状态和开票方规则。", ("发票", "抬头"), ("写错", "改")),
            ("退票后发票要作废吗？", "退票后相关发票或行程单可能需要作废、红冲或重新开具。", ("退票", "发票"), ("作废", "红冲")),
            ("国际机票能开电子发票吗？", "国际机票报销凭证类型与国内机票不同，需以出票渠道说明为准。", ("国际机票", "电子发票"), ("能开", "报销")),
            ("公司报销需要哪些凭证？", "常见凭证包括行程单、电子发票或服务发票，具体以公司财务要求为准。", ("报销", "凭证"), ("公司", "哪些")),
            ("发票邮箱收不到怎么办？", "可先检查邮箱地址、垃圾箱和开票状态，仍未收到再联系开票方补发。", ("发票", "收不到"), ("邮箱", "怎么办")),
        ),
    ),
    (
        "BAGGAGE",
        "行李",
        (
            ("托运行李额度在哪里看？", "托运行李额与航司、航线、舱位和会员等级有关，以客票规则为准。", ("行李额", "看"), ("托运", "免费")),
            ("随身行李可以带多重？", "随身行李重量和尺寸由航司规定，机场现场可能再次核验。", ("随身行李", "多重"), ("重量", "可以")),
            ("超重行李怎么收费？", "超重行李收费按航司、航线和超出重量计算，提前购买通常更划算。", ("超重行李", "收费"), ("怎么", "重量")),
            ("婴儿车可以免费托运吗？", "婴儿车是否免费托运取决于航司规则和尺寸重量，建议提前确认。", ("婴儿车", "托运"), ("免费", "可以")),
            ("乐器可以带上飞机吗？", "乐器能否随身携带取决于尺寸、重量和客舱安全要求。", ("乐器", "飞机"), ("带上", "随身")),
            ("锂电池能放托运行李吗？", "备用锂电池通常不得托运，应按民航安全规则随身携带并做好保护。", ("锂电池", "托运行李"), ("备用", "能放")),
            ("行李延误了怎么赔偿？", "行李延误赔偿需按航司行李运输规则和实际损失材料处理。", ("行李", "延误"), ("赔偿", "怎么")),
        ),
    ),
    (
        "CHECKIN_SEAT",
        "值机选座",
        (
            ("值机通常什么时候开放？", "线上值机通常在起飞前 24-48 小时开放，具体以航司规则为准。", ("值机", "开放"), ("什么时候", "线上")),
            ("值机后还能改座位吗？", "值机后是否能改座位取决于航司系统、剩余座位和机场截载状态。", ("值机后", "改座位"), ("还能", "座位")),
            ("靠窗座位需要收费吗？", "靠窗座位是否收费取决于航司座位产品和舱位权益。", ("靠窗", "收费"), ("座位", "需要")),
            ("同行人可以坐一起吗？", "同行人能否坐一起取决于剩余座位、值机时间和座位规则。", ("同行人", "坐一起"), ("可以", "座位")),
            ("办了值机还能退票吗？", "办完值机后退票可能需先取消值机，再按客票规则处理。", ("值机", "退票"), ("办了", "还能")),
            ("登机牌可以重新打印吗？", "登机牌通常可通过线上渠道或机场柜台重新获取，需在截载前完成。", ("登机牌", "重新打印"), ("可以", "柜台")),
            ("选座失败是什么原因？", "选座失败可能因未到开放时间、座位售罄、航班保护或系统限制。", ("选座", "失败"), ("原因", "为什么")),
        ),
    ),
    (
        "FLIGHT_STATUS",
        "航班动态",
        (
            ("航班动态多久更新一次？", "航班动态会随航司、机场和空管信息更新，临近起飞变化更频繁。", ("航班动态", "更新"), ("多久", "一次")),
            ("显示延误但机场没通知怎么办？", "可同时参考航司、机场和短信通知，最终以航司现场保障信息为准。", ("延误", "没通知"), ("机场", "怎么办")),
            ("到达时间和落地时间一样吗？", "到达时间可能包含滑行和靠桥信息，落地时间仅指飞机接地时间。", ("到达时间", "落地时间"), ("一样", "区别")),
            ("航班取消一般什么时候通知？", "航班取消通知时间不固定，取决于天气、空管、机务和航司决策。", ("航班取消", "通知"), ("什么时候", "一般")),
            ("经停航班延误怎么看？", "经停航班需关注前序航段、经停机场和最终目的地到达信息。", ("经停", "延误"), ("怎么看", "航班")),
            ("共享航班按哪个航司查询？", "共享航班可用实际承运航司或出票航司航班号查询，现场以承运航司为准。", ("共享航班", "查询"), ("哪个航司", "承运")),
            ("天气原因延误可以赔偿吗？", "天气原因多属于不可控因素，赔偿或服务安排以航司不正常航班政策为准。", ("天气", "延误"), ("赔偿", "原因")),
        ),
    ),
    (
        "SPECIAL_ASSISTANCE",
        "特殊协助",
        (
            ("轮椅服务怎么申请？需要什么材料", "轮椅服务通常需提前申请并提供航班、乘机人和行动能力信息。", ("轮椅", "材料"), ("申请", "服务")),
            ("老人第一次坐飞机能有人协助吗？", "老人出行可咨询特殊旅客协助，是否安排陪同以航司和机场保障能力为准。", ("老人", "协助"), ("第一次", "坐飞机")),
            ("孕妇乘机需要证明吗？", "孕妇乘机证明要求与孕周、身体状况和航司规则有关。", ("孕妇", "证明"), ("乘机", "需要")),
            ("无成人陪伴儿童怎么坐飞机？", "无陪儿童服务需满足年龄和航线条件，并提前按航司要求申请。", ("无成人陪伴", "儿童"), ("坐飞机", "怎么")),
            ("病患旅客乘机有什么限制？", "病患旅客可能需医疗证明和适航评估，具体以航司特殊旅客规则为准。", ("病患", "限制"), ("乘机", "旅客")),
            ("特殊餐食可以提前多久订？", "特殊餐食通常需在航班起飞前较早时间预订，具体截止时间以航司为准。", ("特殊餐食", "提前"), ("多久", "订")),
            ("带氧气设备上飞机可以吗？", "氧气设备和医疗器械上机需符合航司和安全运输要求，通常要提前申请。", ("氧气", "飞机"), ("设备", "可以")),
        ),
    ),
    (
        "PET_CABIN",
        "宠物",
        (
            ("宠物托运和进客舱的材料一样吗？", "宠物托运和进客舱所需材料相近但限制不同，需看航司宠物运输规则。", ("宠物", "材料"), ("托运", "客舱")),
            ("猫可以带进客舱吗？", "猫能否进客舱取决于航司、航线、机型、名额和航空箱要求。", ("猫", "客舱"), ("可以", "带进")),
            ("宠物托运需要检疫证明吗？", "宠物托运通常需要检疫证明、疫苗证明和合规航空箱。", ("宠物托运", "检疫证明"), ("需要", "疫苗")),
            ("宠物航空箱尺寸有什么要求？", "航空箱尺寸需满足宠物站立转身和航司安全运输标准。", ("航空箱", "尺寸"), ("宠物", "要求")),
            ("短鼻犬可以托运吗？", "短鼻犬等特殊品种托运限制更严格，部分航司或季节可能不承运。", ("短鼻犬", "托运"), ("可以", "品种")),
            ("宠物名额为什么会满？", "宠物名额受机型、舱位、航班和安全限制影响，通常需要提前申请。", ("宠物", "名额"), ("满", "为什么")),
            ("宠物运输失败会退费吗？", "宠物运输失败是否退费需看失败原因和服务条款。", ("宠物运输", "退费"), ("失败", "会")),
        ),
    ),
    (
        "IRREGULAR",
        "异常航班",
        (
            ("航班取消后能免费改签吗？", "航班取消通常可按非自愿规则改签，是否免费以航司政策为准。", ("航班取消", "改签"), ("免费", "能")),
            ("非自愿退票是什么意思？", "非自愿退票指因航班取消、延误等非旅客原因按特殊规则退票。", ("非自愿退票", "意思"), ("什么", "退票")),
            ("延误证明在哪里开？", "延误证明通常可通过航司官方渠道、机场柜台或客服申请。", ("延误证明", "开"), ("申请", "证明")),
            ("备降后后续航班怎么安排？", "备降后的安排取决于航司保障、天气和机场运行情况。", ("备降", "安排"), ("后续", "航班")),
            ("航班取消住宿谁负责？", "住宿安排需看取消原因、航司服务政策和机场现场保障。", ("航班取消", "住宿"), ("负责", "谁")),
            ("延误四小时能补偿吗？", "延误补偿需按航司不正常航班政策、延误原因和航线规则判断。", ("延误", "补偿"), ("四小时", "能")),
            ("非自愿改签后还能退票吗？", "非自愿改签后退票规则需结合新客票状态和航司政策确认。", ("非自愿改签", "退票"), ("还能", "规则")),
        ),
    ),
    (
        "MEMBERSHIP",
        "会员",
        (
            ("里程多久到账？", "里程到账时间受航司、舱位和合作方数据同步影响，通常需等待数日。", ("里程", "到账"), ("多久", "积分")),
            ("里程补登需要什么材料？", "里程补登通常需要客票、登机牌、会员号和乘机信息。", ("里程补登", "材料"), ("需要", "登机牌")),
            ("会员等级权益有哪些？", "会员等级权益通常包括里程累积、优先服务、行李额或休息室等，具体以航司为准。", ("会员等级", "权益"), ("哪些", "里程")),
            ("积分和里程是一回事吗？", "积分和里程的叫法、用途和有效期可能不同，需看航司会员体系。", ("积分", "里程"), ("一回事", "区别")),
            ("里程会过期吗？", "里程是否过期取决于航司会员规则和账户活动。", ("里程", "过期"), ("会", "会员")),
            ("家庭账户可以合并里程吗？", "家庭账户或里程共享需看航司是否开放及成员绑定规则。", ("家庭账户", "里程"), ("合并", "共享")),
            ("用里程兑换机票还能退吗？", "里程票退改规则与现金票不同，手续费和里程退回以航司规则为准。", ("里程", "兑换机票"), ("退", "规则")),
        ),
    ),
)


def _generated_runtime_airline_faq_entries() -> tuple[RuntimeAirlineFaqEntry, ...]:
    entries: list[RuntimeAirlineFaqEntry] = []
    faq_id = 34100
    for reason_code, _scene_name, items in _RUNTIME_AIRLINE_FAQ_SCENE_SPECS:
        for question, answer, required_terms, optional_terms in items:
            entries.append(
                RuntimeAirlineFaqEntry(
                    faq_id,
                    reason_code,
                    question,
                    answer,
                    required_terms,
                    optional_terms,
                )
            )
            faq_id += 1
    return tuple(entries)


RUNTIME_AIRLINE_FAQ_ENTRIES: tuple[RuntimeAirlineFaqEntry, ...] = (
    *_BASE_RUNTIME_AIRLINE_FAQ_ENTRIES,
    *_generated_runtime_airline_faq_entries(),
)


def _runtime_faq_looks_like_question(message: str) -> bool:
    text = message.strip()
    if not text:
        return False
    return "?" in text or "？" in text or any(
        term in text for term in ("吗", "么", "怎么", "如何", "多少", "多久", "什么时候", "能不能", "可以")
    )


def _runtime_faq_more_specific_than(best: RuntimeAirlineFaqEntry, competing: RuntimeAirlineFaqEntry) -> bool:
    best_terms = set(best.required_terms)
    competing_terms = set(competing.required_terms)
    return competing_terms < best_terms


def _runtime_faq_same_topic_family(best: RuntimeAirlineFaqEntry, competing: RuntimeAirlineFaqEntry) -> bool:
    if set(best.required_terms) != set(competing.required_terms):
        return False
    if best.answer == competing.answer:
        return True
    return bool(set(best.optional_terms) & set(competing.optional_terms))


def _runtime_faq_looks_like_transaction_request(message: str) -> bool:
    text = message.strip()
    if _runtime_faq_explicitly_denies_transaction(text):
        return False
    if _runtime_faq_looks_like_question(text) and not _runtime_faq_has_execution_intent(text):
        return False
    action_terms = (
        "办理",
        "申请",
        "提交",
        "加购",
        "购买",
        "买一点",
        "买些",
        "买个",
        "买一份",
        "提前买",
        "帮我买",
        "帮我办",
        "帮我处理",
        "走流程",
        "进入流程",
    )
    if not any(term in text for term in action_terms):
        return False
    business_terms = (
        "额度",
        "行李",
        "餐食",
        "保险",
        "贵宾厅",
        "退票",
        "改签",
        "发票",
        "宠物",
        "轮椅",
        "选座",
        "值机",
        "里程",
        "团队票",
        "机票",
    )
    return any(term in text for term in business_terms)


def _runtime_faq_has_execution_intent(message: str) -> bool:
    execution_prefixes = (
        "我要",
        "我想办",
        "我想办理",
        "我想申请",
        "帮我",
        "给我",
        "替我",
        "为我",
        "麻烦你",
        "麻烦帮",
        "现在办",
        "直接办",
        "马上办",
        "买一点",
        "买些",
        "买个",
        "买一份",
        "提前买",
        "加购",
    )
    return any(term in message for term in execution_prefixes)


def _runtime_faq_explicitly_denies_transaction(message: str) -> bool:
    denial_terms = (
        "不是要办理",
        "不是办理",
        "不办理",
        "不是要办",
        "不办",
        "先不办",
        "现在不办",
    )
    consultation_terms = ("只是问", "只想问", "就想问", "想问", "想知道", "咨询一下")
    return any(term in message for term in denial_terms) and any(term in message for term in consultation_terms)


def _runtime_faq_looks_like_document_comparison(message: str) -> bool:
    comparison_terms = ("区别", "差别", "不同", "差异")
    long_tail_terms = ("理赔", "赔付", "补偿", "条款", "保险", "凭证")
    if any(term in message for term in ("宠物", "托运", "客舱", "行李")):
        return False
    return any(term in message for term in comparison_terms) and any(term in message for term in long_tail_terms)


def _runtime_faq_looks_like_irregular_claim_question(message: str) -> bool:
    irregular_terms = ("延误", "取消", "备降", "签转", "非自愿")
    claim_terms = ("保险", "延误险", "理赔", "赔付", "赔偿", "补偿", "凭证", "资料", "材料")
    return any(term in message for term in irregular_terms) and any(term in message for term in claim_terms)


def _normalize_faq_text(message: str) -> str:
    return re.sub(r"[\s,，。.?？!！:：;；、]+", "", message.strip())


class FaqSemanticAnswerGate:
    def __init__(
        self,
        knowledge_facade: FaqKnowledgeFacade,
        knowledge_base_ids: Sequence[int],
        *,
        top_k: int = 5,
        rerank: bool = True,
        min_score: float = 0.85,
        min_margin: float = 0.12,
    ) -> None:
        self._knowledge_facade = knowledge_facade
        self._knowledge_base_ids = tuple(int(knowledge_base_id) for knowledge_base_id in knowledge_base_ids)
        self._top_k = top_k
        self._rerank = rerank
        self._min_score = min_score
        self._min_margin = min_margin

    def decide(
        self,
        message: str,
        *,
        active_task: dict[str, Any] | None,
        suspended_tasks: list[dict[str, Any]],
    ) -> RouteDecision | None:
        del suspended_tasks
        hits = self._semantic_hits(message)
        if not hits:
            return None
        best = hits[0]
        second_score = _score(hits[1]) if len(hits) > 1 else 0.0
        margin = max(0.0, _score(best) - second_score)
        if _score(best) < self._min_score:
            return None
        if active_task is not None and not _semantic_looks_like_question(message):
            return None
        if active_task is not None and _semantic_active_ambiguous_input(message):
            return RouteDecision(
                action="CLARIFY",
                reason="Active SOP semantic FAQ input is ambiguous with slot collection",
                faq_answer={
                    "sourceLayer": "faq_semantic",
                    "reasonCode": "SEMANTIC_ACTIVE_AMBIGUOUS",
                    "answer": _answer(best),
                    "confidence": min(0.99, _score(best)),
                    "margin": margin,
                    "mutatesSopState": False,
                    "evidence": _semantic_evidence(best, hits, retrieval_mode="faq", rerank_used=self._rerank),
                },
            )
        if margin < self._min_margin:
            return RouteDecision(
                action="CLARIFY",
                reason="Semantic FAQ candidates are too close to answer safely",
                faq_answer={
                    "sourceLayer": "faq_semantic",
                    "reasonCode": "SEMANTIC_LOW_MARGIN",
                    "answer": _answer(best),
                    "confidence": min(0.99, _score(best)),
                    "margin": margin,
                    "mutatesSopState": False,
                    "evidence": _semantic_evidence(best, hits, retrieval_mode="faq", rerank_used=self._rerank),
                },
            )
        return RouteDecision(
            action="ANSWER_FAQ",
            reason="Semantic FAQ accepted before SOP arbitration",
            faq_answer={
                "sourceLayer": "faq_semantic",
                "reasonCode": "SEMANTIC_HIGH_CONFIDENCE",
                "answer": _answer(best),
                "confidence": min(0.99, _score(best)),
                "margin": margin,
                "mutatesSopState": False,
                "evidence": _semantic_evidence(best, hits, retrieval_mode="faq", rerank_used=self._rerank),
            },
        )

    def _semantic_hits(self, message: str) -> list[Any]:
        hits: list[Any] = []
        for knowledge_base_id in self._knowledge_base_ids:
            for result in self._knowledge_facade.search_context(
                knowledge_base_id,
                message,
                top_k=self._top_k,
                retrieval_mode="faq",
                score_threshold=None,
                rerank=self._rerank,
            ):
                if _source_type(result) != "FAQ":
                    continue
                if _match_type(result) not in {"VECTOR", "HYBRID"}:
                    continue
                hits.append(_with_knowledge_base_id(result, knowledge_base_id))
        return sorted(hits, key=lambda hit: (-_score(hit), _faq_id(hit)))


def _source_type(result: Any) -> str:
    return str(_field(result, "source_type") or _field(result, "sourceType") or "")


def _match_type(result: Any) -> str:
    return str(_field(result, "match_type") or _field(result, "matchType") or "").upper()


def _score(result: Any) -> float:
    return float(_field(result, "score") or 0.0)


def _question(result: Any) -> str:
    return str(_field(result, "title") or _field(result, "content") or "")


def _answer(result: Any) -> str:
    return str(_field(result, "answer") or _field(result, "content") or "")


def _faq_id(result: Any) -> int:
    return int(_field(result, "faq_id") or _field(result, "faqId") or 0)


def _knowledge_base_id(result: Any) -> int | None:
    raw = _field(result, "_runtime_lab_knowledge_base_id") or _field(result, "knowledge_base_id") or _field(result, "knowledgeBaseId")
    return int(raw) if raw is not None else None


def _with_knowledge_base_id(result: Any, knowledge_base_id: int) -> Any:
    if isinstance(result, dict):
        copied = dict(result)
        copied["_runtime_lab_knowledge_base_id"] = knowledge_base_id
        return copied
    try:
        setattr(result, "_runtime_lab_knowledge_base_id", knowledge_base_id)
    except Exception:
        return result
    return result


def _semantic_evidence(
    result: Any,
    hits: Sequence[Any],
    *,
    retrieval_mode: str,
    rerank_used: bool,
) -> dict[str, Any]:
    evidence = FaqAnswerEvidence(
        faq_id=_faq_id(result),
        question=_question(result),
        answer=_answer(result),
        score=_score(result),
        match_type=_match_type(result),
        source="structured_faq",
        matched_terms=(),
        knowledge_base_id=_knowledge_base_id(result),
    ).to_dict()
    evidence["retrievalMode"] = retrieval_mode
    evidence["rerankUsed"] = rerank_used
    evidence["topCandidates"] = [
        {
            "faqId": _faq_id(hit),
            "question": _question(hit),
            "score": _score(hit),
            "matchType": _match_type(hit),
            "knowledgeBaseId": _knowledge_base_id(hit),
        }
        for hit in hits
    ]
    return evidence


def _semantic_active_ambiguous_input(message: str) -> bool:
    return _semantic_looks_like_question(message) and _semantic_looks_like_slot_payload(message)


def _semantic_looks_like_question(message: str) -> bool:
    text = message.strip()
    return "?" in text or "？" in text or any(term in text for term in ("可以", "能", "怎么", "如何", "吗", "规则"))


def _semantic_looks_like_slot_payload(message: str) -> bool:
    slot_terms = ("订单", "票号", "手机号", "电话", "证件", "身份证", "护照", "乘机人")
    if any(term in message for term in slot_terms):
        return True
    return re.search(r"[A-Za-z]{1,6}-?\d{2,}|\d{6,}", message.strip()) is not None


def _field(result: Any, name: str) -> Any:
    if isinstance(result, dict):
        return result.get(name)
    return getattr(result, name, None)
