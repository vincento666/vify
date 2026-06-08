from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True)
class SopStep:
    step_id: str
    prompt: str
    interruptible: bool
    node_type: str = "QUESTION"


@dataclass(frozen=True)
class KeywordTriggerTemplate:
    template_id: str
    phrases: tuple[str, ...] = ()
    all_terms: tuple[str, ...] = ()
    regexes: tuple[str, ...] = ()
    score: float = 1.0


@dataclass(frozen=True)
class TriggerTemplateMatch:
    template_id: str
    matched_terms: tuple[str, ...]
    score: float


@dataclass(frozen=True)
class SopManifest:
    sop_id: str
    display_name: str
    trigger_keywords: tuple[str, ...]
    strong_trigger_keywords: tuple[str, ...]
    steps: tuple[SopStep, ...]
    interruptible_steps: tuple[str, ...]
    resume_prompt: str
    business_area: str = "CONSULTATION"
    strong_trigger_templates: tuple[KeywordTriggerTemplate, ...] = ()


@dataclass(frozen=True)
class SopTurnResult:
    sop_id: str
    current_step: str
    reply: str
    pending_prompt: str
    collected: dict[str, Any]
    completed: bool
    checkpoint: dict[str, Any]


def match_strong_trigger_template(text: str, manifest: SopManifest) -> TriggerTemplateMatch | None:
    templates = manifest.strong_trigger_templates or _keyword_templates(manifest.sop_id, manifest.strong_trigger_keywords)
    for template in templates:
        matched = _match_template(text, template)
        if matched:
            return TriggerTemplateMatch(template.template_id, matched, template.score)
    return None


class MockSopAdapter:
    def __init__(self, manifests: dict[str, SopManifest] | None = None) -> None:
        self._manifests = manifests or mock_sop_manifests()

    def start(self, sop_id: str) -> SopTurnResult:
        manifest = self._manifest(sop_id)
        prompt = self._step(manifest, "collect_order_no").prompt
        reply = f"已开始{manifest.display_name}，{prompt}"
        return self._result(manifest, "collect_order_no", reply, prompt, {}, completed=False)

    def continue_task(
        self,
        sop_id: str,
        current_step: str,
        message: str,
        collected: dict[str, Any] | None = None,
    ) -> SopTurnResult:
        manifest = self._manifest(sop_id)
        saved = dict(collected or {})
        text = message.strip()
        if current_step == "collect_order_no":
            saved.update(_parse_business_variables(text))
            saved.setdefault("order_no", text)
            saved["last_user_message"] = text
            saved["node_trace"] = _node_trace(manifest)
            prompt = self._step(manifest, "confirm").prompt
            order_no = saved.get("order_no") or text
            phone_note = f"，手机号 {saved['phone']}" if saved.get("phone") else ""
            reply = f"已记录订单号 {order_no}{phone_note}。{_policy_note(manifest)}{prompt}"
            return self._result(manifest, "confirm", reply, prompt, saved, completed=False)
        if current_step == "confirm":
            prompt = self._step(manifest, "confirm").prompt
            if _is_confirm(text):
                reply = f"{manifest.display_name}已完成。"
                return self._result(manifest, "completed", reply, "", saved, completed=True)
            reply = f"当前需要确认。{prompt}"
            return self._result(manifest, "confirm", reply, prompt, saved, completed=False)
        return self._result(manifest, "completed", f"{manifest.display_name}已完成。", "", saved, completed=True)

    def is_interruptible(self, sop_id: str, step_id: str) -> bool:
        manifest = self._manifest(sop_id)
        return step_id in manifest.interruptible_steps

    def _manifest(self, sop_id: str) -> SopManifest:
        manifest = self._manifests.get(sop_id)
        if manifest is None:
            raise KeyError(f"Unknown mock SOP: {sop_id}")
        return manifest

    def _step(self, manifest: SopManifest, step_id: str) -> SopStep:
        for step in manifest.steps:
            if step.step_id == step_id:
                return step
        raise KeyError(f"Unknown mock SOP step: {manifest.sop_id}.{step_id}")

    def _result(
        self,
        manifest: SopManifest,
        current_step: str,
        reply: str,
        pending_prompt: str,
        collected: dict[str, Any],
        completed: bool,
    ) -> SopTurnResult:
        checkpoint_status = "COMPLETED" if completed else "ACTIVE"
        checkpoint = {
            "sop_id": manifest.sop_id,
            "current_step": current_step,
            "pending_prompt": pending_prompt,
            "collected": dict(collected),
            "status": checkpoint_status,
        }
        return SopTurnResult(
            sop_id=manifest.sop_id,
            current_step=current_step,
            reply=reply,
            pending_prompt=pending_prompt,
            collected=dict(collected),
            completed=completed,
            checkpoint=checkpoint,
        )


def mock_sop_manifests() -> dict[str, SopManifest]:
    return {
        "flight_booking": _build_sop_manifest(
            sop_id="flight_booking",
            display_name="机票预订",
            business_area="SALES",
            trigger_keywords=("买票", "买机票", "订机票", "购买航班", "出票", "购票", "可售航班", "订航班", "机票销售"),
            strong_trigger_keywords=("买机票", "订机票", "购买航班", "购票", "机票销售", "订航班"),
            strong_trigger_templates=(
                _phrase_template("flight_booking:phrase", "买机票", "订机票", "购买航班", "购票", "机票销售", "订航班"),
                _all_terms_template("flight_booking:buy_ticket", "买", "机票"),
                _all_terms_template("flight_booking:sales_book", "机票销售", "订"),
                _all_terms_template("flight_booking:need_issue", "需要", "出票"),
                _all_terms_template("flight_booking:book_one_ticket", "订一张", "机票"),
            ),
            branch_step_id="booking_branch",
            resume_prompt="是否继续刚才的机票预订流程？",
        ),
        "fare_quote": _build_sop_manifest(
            sop_id="fare_quote",
            display_name="票价咨询",
            business_area="SALES",
            trigger_keywords=("票价", "报价", "价格", "查价格", "多少钱", "比较价格", "机票价格", "价格趋势"),
            strong_trigger_keywords=("票价", "报价", "查价格", "机票价格", "多少钱"),
            strong_trigger_templates=(
                _phrase_template("fare_quote:phrase", "票价", "报价", "查价格", "机票价格", "多少钱"),
                _all_terms_template("fare_quote:route_price", "飞", "价格"),
                _all_terms_template("fare_quote:not_issue", "不出票", "票价"),
                _regex_template("fare_quote:regex", r"(票价|报价|价格).{0,12}(多少|怎么样|趋势)?"),
            ),
            branch_step_id="fare_branch",
            resume_prompt="是否继续刚才的票价咨询流程？",
        ),
        "group_booking": _build_sop_manifest(
            sop_id="group_booking",
            display_name="团队订票",
            business_area="SALES",
            trigger_keywords=("团队机票", "团队订票", "团体票", "团体购票", "多人订票", "团队票", "集体出行", "团队政策", "团建"),
            strong_trigger_keywords=("团队机票", "团队订票", "团体票", "团体购票", "团队票", "团队政策", "团建"),
            strong_trigger_templates=(
                _phrase_template("group_booking:phrase", "团队机票", "团队订票", "团体票", "团体购票", "团队票", "团队政策", "团建", score=1.15),
                _all_terms_template("group_booking:many_people", "十", "订票", score=1.15),
                _all_terms_template("group_booking:company_group", "公司", "多人", "订票", score=1.15),
                _all_terms_template("group_booking:collective_trip", "集体出行", "订", score=1.15),
                _regex_template("group_booking:regex", r"(团队|团体|多人|集体).{0,12}(机票|订票|购票|出票)", score=1.15),
            ),
            branch_step_id="group_branch",
            resume_prompt="是否继续刚才的团队订票流程？",
        ),
        "ancillary_sales": _build_sop_manifest(
            sop_id="ancillary_sales",
            display_name="增值服务",
            business_area="SALES",
            trigger_keywords=("加购", "贵宾厅", "保险", "餐食", "接送机", "优先登机", "附加服务", "增值服务", "升舱券", "附加产品"),
            strong_trigger_keywords=("贵宾厅", "保险", "餐食", "增值服务", "附加服务", "升舱券", "附加产品"),
            strong_trigger_templates=(
                _phrase_template("ancillary_sales:phrase", "贵宾厅", "保险", "餐食", "增值服务", "附加服务", "升舱券", "附加产品", score=1.1),
                _all_terms_template("ancillary_sales:add_meal", "加", "餐食", score=1.1),
                _all_terms_template("ancillary_sales:add_service", "买", "服务", score=1.1),
                _regex_template("ancillary_sales:regex", r"(加购|购买).{0,12}(餐食|保险|贵宾厅|接送机|增值服务)", score=1.1),
            ),
            branch_step_id="ancillary_branch",
            resume_prompt="是否继续刚才的增值服务购买流程？",
        ),
        "refund_ticket": _build_sop_manifest(
            sop_id="refund_ticket",
            display_name="退票",
            business_area="REFUND",
            trigger_keywords=("退票", "退款", "退机票", "取消行程", "票款", "退费", "退掉航班", "退掉", "不飞"),
            strong_trigger_keywords=("退票", "我要退票", "退款", "取消行程", "退掉"),
            strong_trigger_templates=(
                _all_terms_template("refund_ticket:involuntary_refund", "非自愿", "退票", score=1.2),
                _phrase_template("refund_ticket:phrase", "退票", "我要退票", "退款", "取消行程", "退掉"),
                _all_terms_template("refund_ticket:fare_back", "票款", "退回来"),
                _all_terms_template("refund_ticket:fare_take_back", "票款", "拿回来"),
                _all_terms_template("refund_ticket:not_fly", "不飞", "票款"),
                _regex_template("refund_ticket:regex", r"(非自愿.{0,12}退|取消.{0,12}行程)"),
            ),
            branch_step_id="policy_branch",
            resume_prompt="是否继续刚才的退票流程？",
        ),
        "change_flight": _build_sop_manifest(
            sop_id="change_flight",
            display_name="改签",
            business_area="CHANGE",
            trigger_keywords=("改签", "改航班", "换航班", "改日期", "改时间", "调整航班", "同舱位"),
            strong_trigger_keywords=("我要改签", "换航班", "调整航班", "改签", "改航班"),
            strong_trigger_templates=(
                _phrase_template("change_flight:phrase", "我要改签", "换航班", "调整航班", "改签", "改航班"),
                _all_terms_template("change_flight:change_date", "改", "日期"),
                _all_terms_template("change_flight:change_time", "调整", "航班"),
                _regex_template("change_flight:regex", r"(改签|换).{0,12}(航班|日期|时间)|改.{0,6}(日期|时间)"),
            ),
            branch_step_id="change_branch",
            resume_prompt="是否继续刚才的改签流程？",
        ),
        "passenger_info_change": _build_sop_manifest(
            sop_id="passenger_info_change",
            display_name="资料修改",
            business_area="CHANGE",
            trigger_keywords=("证件号", "修改乘机人信息", "改联系人", "姓名拼音", "更正", "旅客信息", "资料修改", "信息有误", "乘客资料", "改乘机人", "证件有效期"),
            strong_trigger_keywords=("修改乘机人信息", "改证件", "证件号", "改联系人", "资料修改", "乘客资料", "改乘机人", "证件有效期"),
            strong_trigger_templates=(
                _phrase_template(
                    "passenger_info_change:phrase",
                    "修改乘机人信息",
                    "改证件",
                    "证件号",
                    "改联系人",
                    "资料修改",
                    "乘客资料",
                    "改乘机人",
                    "证件有效期",
                    score=1.15,
                ),
                _all_terms_template("passenger_info_change:wrong_document", "证件", "填错", score=1.15),
                _all_terms_template("passenger_info_change:name_fix", "姓名", "更正", score=1.15),
                _regex_template("passenger_info_change:regex", r"(证件|姓名|联系人|旅客信息|乘客资料).{0,12}(错|改|更正|修改|有效期)", score=1.15),
            ),
            branch_step_id="passenger_info_branch",
            resume_prompt="是否继续刚才的资料修改流程？",
        ),
        "invoice_apply": _build_sop_manifest(
            sop_id="invoice_apply",
            display_name="发票申请",
            business_area="CONSULTATION",
            trigger_keywords=("发票", "开票", "报销凭证", "行程单", "电子票据", "抬头", "税号"),
            strong_trigger_keywords=("发票", "开票", "申请发票", "行程单", "报销凭证"),
            strong_trigger_templates=(
                _phrase_template("invoice_apply:phrase", "发票", "开票", "申请发票", "行程单", "报销凭证"),
                _all_terms_template("invoice_apply:company", "公司", "凭证"),
                _all_terms_template("invoice_apply:tax", "抬头", "税号"),
                _regex_template("invoice_apply:regex", r"(开|补开|申请).{0,8}(发票|行程单|票据)"),
            ),
            branch_step_id="invoice_intent",
            branch_node_type="INTENT_RECOGNITION",
            resume_prompt="是否继续刚才的发票申请流程？",
        ),
        "baggage_service": _build_sop_manifest(
            sop_id="baggage_service",
            display_name="行李服务",
            business_area="CONSULTATION",
            trigger_keywords=("行李", "托运行李", "加行李", "行李额", "超重行李", "运动器材", "随身行李"),
            strong_trigger_keywords=("行李服务", "托运行李", "加行李", "购买行李额", "超重"),
            strong_trigger_templates=(
                _phrase_template("baggage_service:phrase", "行李服务", "托运行李", "加行李", "购买行李额", "超重"),
                _all_terms_template("baggage_service:extra_weight", "行李", "超重"),
                _all_terms_template("baggage_service:sports", "运动器材", "托运"),
                _regex_template("baggage_service:regex", r"(行李|箱子).{0,12}(超重|托运|额度|加购)"),
            ),
            branch_step_id="baggage_branch",
            resume_prompt="是否继续刚才的行李服务流程？",
        ),
        "seat_checkin": _build_sop_manifest(
            sop_id="seat_checkin",
            display_name="值机选座",
            business_area="CONSULTATION",
            trigger_keywords=("值机", "选座", "座位", "靠窗", "登机牌", "过道", "安全出口"),
            strong_trigger_keywords=("值机", "选座", "我要值机", "我要选座"),
            strong_trigger_templates=(
                _phrase_template("seat_checkin:phrase", "值机", "选座", "我要值机", "我要选座"),
                _all_terms_template("seat_checkin:boarding_pass", "登机牌", "座位"),
                _all_terms_template("seat_checkin:window", "靠窗", "座位"),
                _regex_template("seat_checkin:regex", r"(值机|选座|座位|登机牌).{0,12}(靠窗|过道|一起|办理)?"),
            ),
            branch_step_id="seat_branch",
            resume_prompt="是否继续刚才的值机选座流程？",
        ),
        "flight_status": _build_sop_manifest(
            sop_id="flight_status",
            display_name="航班动态",
            business_area="CONSULTATION",
            trigger_keywords=("航班动态", "航班状态", "有没有取消", "是否延误", "起飞时间", "到达时间", "登机口"),
            strong_trigger_keywords=("航班动态", "航班状态", "查航班", "有没有取消", "是否延误"),
            strong_trigger_templates=(
                _phrase_template("flight_status:phrase", "航班动态", "航班状态", "查航班", "有没有取消", "是否延误"),
                _all_terms_template("flight_status:delay", "航班", "延误"),
                _all_terms_template("flight_status:time", "起飞", "时间"),
                _regex_template("flight_status:regex", r"(航班|登机口|到达).{0,12}(动态|状态|延误|取消|变了|时间)"),
            ),
            branch_step_id="status_branch",
            resume_prompt="是否继续刚才的航班动态查询？",
        ),
        "special_assistance": _build_sop_manifest(
            sop_id="special_assistance",
            display_name="特殊协助",
            business_area="CONSULTATION",
            trigger_keywords=("轮椅", "特殊协助", "特殊旅客", "特殊服务", "无障碍", "老人", "孕妇", "优先登机"),
            strong_trigger_keywords=("轮椅", "特殊协助", "特殊旅客", "特殊服务", "无障碍"),
            strong_trigger_templates=(
                _phrase_template("special_assistance:phrase", "轮椅", "特殊协助", "特殊旅客", "特殊服务", "无障碍"),
                _all_terms_template("special_assistance:elder", "老人", "协助"),
                _all_terms_template("special_assistance:priority", "优先", "登机"),
                _regex_template("special_assistance:regex", r"(老人|孕妇|行动不便|受伤).{0,12}(轮椅|协助|服务)"),
            ),
            branch_step_id="assist_branch",
            branch_node_type="INTENT_RECOGNITION",
            resume_prompt="是否继续刚才的特殊协助申请？",
        ),
        "pet_cabin": _build_sop_manifest(
            sop_id="pet_cabin",
            display_name="宠物乘机",
            business_area="CONSULTATION",
            trigger_keywords=("宠物", "猫", "小狗", "宠物托运", "客舱", "航空箱", "疫苗证明"),
            strong_trigger_keywords=("宠物", "宠物托运", "宠物乘机", "猫", "小狗"),
            strong_trigger_templates=(
                _phrase_template("pet_cabin:phrase", "宠物", "宠物托运", "宠物乘机", "猫", "小狗"),
                _all_terms_template("pet_cabin:cabin", "宠物", "客舱"),
                _all_terms_template("pet_cabin:docs", "疫苗", "证明"),
                _regex_template("pet_cabin:regex", r"(猫|狗|宠物).{0,12}(托运|客舱|乘机|航空箱)"),
            ),
            branch_step_id="pet_branch",
            resume_prompt="是否继续刚才的宠物乘机服务？",
        ),
        "irregular_flight": _build_sop_manifest(
            sop_id="irregular_flight",
            display_name="异常航班",
            business_area="CONSULTATION",
            trigger_keywords=("不正常航班", "异常航班", "航班取消", "航班延误", "延误四小时", "备降", "签转", "保障方案", "非自愿"),
            strong_trigger_keywords=("不正常航班", "异常航班", "航班取消", "航班延误", "延误四小时", "备降", "签转", "保障方案", "非自愿"),
            strong_trigger_templates=(
                _phrase_template(
                    "irregular_flight:phrase",
                    "不正常航班",
                    "异常航班",
                    "航班取消",
                    "航班延误",
                    "延误四小时",
                    "备降",
                    "签转",
                    "保障方案",
                    "非自愿",
                    score=1.1,
                ),
                _all_terms_template("irregular_flight:delay_guarantee", "延误", "保障", score=1.1),
                _all_terms_template("irregular_flight:diversion", "航班", "备降", score=1.1),
            ),
            branch_step_id="irregular_branch",
            branch_node_type="INTENT_RECOGNITION",
            resume_prompt="是否继续刚才的异常航班协助？",
        ),
        "membership_service": _build_sop_manifest(
            sop_id="membership_service",
            display_name="会员里程",
            business_area="CONSULTATION",
            trigger_keywords=("会员", "里程", "积分", "常旅客", "补登", "补登里程", "升舱券", "会员等级"),
            strong_trigger_keywords=("会员", "里程", "积分", "常旅客", "补登里程"),
            strong_trigger_templates=(
                _phrase_template("membership_service:phrase", "会员", "里程", "积分", "常旅客", "补登里程", score=1.2),
                _all_terms_template("membership_service:mile_missing", "里程", "没到账", score=1.2),
                _all_terms_template("membership_service:points", "积分", "明细", score=1.2),
                _regex_template("membership_service:regex", r"(会员|里程|积分|常旅客).{0,12}(补登|没到账|明细|权益|等级)", score=1.2),
            ),
            branch_step_id="member_branch",
            resume_prompt="是否继续刚才的会员里程服务？",
        ),
    }


def _build_sop_manifest(
    *,
    sop_id: str,
    display_name: str,
    business_area: str,
    trigger_keywords: tuple[str, ...],
    strong_trigger_keywords: tuple[str, ...],
    strong_trigger_templates: tuple[KeywordTriggerTemplate, ...],
    branch_step_id: str,
    resume_prompt: str,
    branch_node_type: str = "CONDITION",
) -> SopManifest:
    return SopManifest(
        sop_id=sop_id,
        display_name=display_name,
        trigger_keywords=trigger_keywords,
        strong_trigger_keywords=strong_trigger_keywords,
        steps=_deep_steps(branch_step_id, branch_node_type=branch_node_type),
        interruptible_steps=("collect_order_no",),
        resume_prompt=resume_prompt,
        business_area=business_area,
        strong_trigger_templates=strong_trigger_templates,
    )


def _phrase_template(template_id: str, *phrases: str, score: float = 1.0) -> KeywordTriggerTemplate:
    return KeywordTriggerTemplate(template_id=template_id, phrases=tuple(phrases), score=score)


def _all_terms_template(template_id: str, *terms: str, score: float = 1.0) -> KeywordTriggerTemplate:
    return KeywordTriggerTemplate(template_id=template_id, all_terms=tuple(terms), score=score)


def _regex_template(template_id: str, *regexes: str, score: float = 1.0) -> KeywordTriggerTemplate:
    return KeywordTriggerTemplate(template_id=template_id, regexes=tuple(regexes), score=score)


def _keyword_templates(sop_id: str, keywords: tuple[str, ...]) -> tuple[KeywordTriggerTemplate, ...]:
    return tuple(
        KeywordTriggerTemplate(template_id=f"{sop_id}:keyword:{index}", phrases=(keyword,))
        for index, keyword in enumerate(keywords)
    )


def _match_template(text: str, template: KeywordTriggerTemplate) -> tuple[str, ...]:
    phrase = next((phrase for phrase in template.phrases if phrase and phrase in text), None)
    if phrase is not None:
        return (phrase,)
    if template.all_terms and all(term in text for term in template.all_terms):
        return template.all_terms
    for pattern in template.regexes:
        match = re.search(pattern, text)
        if match is not None:
            matched_groups = tuple(group for group in match.groups() if group)
            return matched_groups or (match.group(0),)
    return ()


def _deep_steps(branch_step_id: str, branch_node_type: str = "CONDITION") -> tuple[SopStep, ...]:
    return (
        SopStep("collect_order_no", "请提供订单号、手机号和乘机人信息。", True, "INFORMATION_COLLECTION"),
        SopStep("parse_variables", "解析订单、手机号、旅客姓名和航班线索。", True, "VARIABLE_PARSE"),
        SopStep("policy_llm", "生成民航客服政策解释。", True, "LLM"),
        SopStep("business_api", "模拟调用民航订单/航班/会员 API。", True, "API_CALL"),
        SopStep(branch_step_id, "根据业务类型分支。", True, branch_node_type),
        SopStep("aggregate_context", "聚合会话变量和业务查询结果。", True, "VARIABLE_AGGREGATION"),
        SopStep("confirm", "请回复 confirm 或 确认 完成办理。", False, "QUESTION"),
        SopStep("completed", "", False, "END"),
    )


def _parse_business_variables(text: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    order_match = re.search(r"(?:订单号|订单|PNR|票号|编码)\s*[:：]?\s*([A-Z0-9][A-Z0-9-]{3,})", text, re.I)
    if order_match is None:
        order_match = re.search(r"\b([A-Z]{1,4}-?\d{2,})\b", text, re.I)
    if order_match is not None:
        parsed["order_no"] = order_match.group(1).upper()
    phone_match = re.search(r"(1[3-9]\d{9})", text)
    if phone_match is not None:
        parsed["phone"] = phone_match.group(1)
    passenger_match = re.search(r"乘机人\s*([\u4e00-\u9fa5A-Za-z]{2,12})", text)
    if passenger_match is not None:
        parsed["passenger_name"] = passenger_match.group(1)
    return parsed


def _node_trace(manifest: SopManifest) -> list[str]:
    return [step.node_type for step in manifest.steps if step.step_id not in {"completed"}]


def _policy_note(manifest: SopManifest) -> str:
    return f"已完成{manifest.display_name}政策说明、业务查询和变量聚合。"


def _is_confirm(text: str) -> bool:
    normalized = text.strip().lower()
    return normalized == "confirm" or "确认" in normalized
