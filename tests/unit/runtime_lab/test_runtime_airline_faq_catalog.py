import unittest

from app.modules.runtime_lab.domain.faq_gate import RUNTIME_AIRLINE_FAQ_ENTRIES, RuntimeAirlineFaqGate


class RuntimeAirlineFaqCatalogTest(unittest.TestCase):
    def test_catalog_contains_100_plus_airline_faqs_across_business_scenes(self) -> None:
        self.assertGreaterEqual(len(RUNTIME_AIRLINE_FAQ_ENTRIES), 100)
        reason_codes = {entry.reason_code for entry in RUNTIME_AIRLINE_FAQ_ENTRIES}
        self.assertGreaterEqual(len(reason_codes), 15)

    def test_first_100_catalog_questions_are_answerable_by_runtime_faq_gate(self) -> None:
        gate = RuntimeAirlineFaqGate()
        for entry in RUNTIME_AIRLINE_FAQ_ENTRIES[:100]:
            with self.subTest(faq_id=entry.faq_id, question=entry.question):
                proposal = gate.propose(entry.question, active_task=None, suspended_tasks=[])
                self.assertIsNotNone(proposal)
                self.assertEqual(proposal.evidence.faq_id, entry.faq_id)
                self.assertEqual(proposal.reason_code, entry.reason_code)

    def test_similar_consultation_and_transaction_wording_split_between_faq_and_sop(self) -> None:
        gate = RuntimeAirlineFaqGate()
        cases = (
            ("轮椅服务怎么申请？需要什么材料", True),
            ("我要申请轮椅服务，订单号CA2234，手机号13515151515，乘机人王五", False),
            ("宠物托运和进客舱的材料一样吗？", True),
            ("帮我办理宠物托运，订单号CA3234，手机号13515151515，乘机人王五", False),
            ("团队票退票手续费怎么算？", True),
            ("我要办理团队票退票，订单号CA5234，手机号13515151515，乘机人王五", False),
        )
        for message, should_answer in cases:
            with self.subTest(message=message):
                proposal = gate.propose(message, active_task=None, suspended_tasks=[])
                if should_answer:
                    self.assertIsNotNone(proposal)
                else:
                    self.assertIsNone(proposal)

    def test_denied_transaction_consultations_stay_in_runtime_faq_lane(self) -> None:
        gate = RuntimeAirlineFaqGate()
        cases = (
            ("先不改签，我只是问改签手续费怎么算？", "CHANGE_FEE_RULE"),
            ("我不办宠物托运，只想知道宠物乘机需要什么材料？", "PET_CABIN_DOCS"),
            ("不是要开发票，想问电子发票多久能开？", "INVOICE_TIMING"),
        )
        for message, reason_code in cases:
            with self.subTest(message=message):
                proposal = gate.propose(message, active_task=None, suspended_tasks=[])

                self.assertIsNotNone(proposal)
                assert proposal is not None
                self.assertEqual(proposal.reason_code, reason_code)

    def test_irregular_insurance_claim_question_defers_to_rag_lane(self) -> None:
        gate = RuntimeAirlineFaqGate()

        proposal = gate.propose("我不办理改签，只想问航班延误超过4小时保险怎么赔？", active_task=None, suspended_tasks=[])

        self.assertIsNone(proposal)
        self.assertIsNotNone(gate.propose("延误证明怎么开？", active_task=None, suspended_tasks=[]))


if __name__ == "__main__":
    unittest.main()
