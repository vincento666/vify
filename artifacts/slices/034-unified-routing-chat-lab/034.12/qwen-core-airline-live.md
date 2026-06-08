# RuntimeLab Live Qwen Core Airline Scenarios

- Slice: 034.12 live natural core airline gate
- Scope: booking/refund/change/consultation, 10 natural scenarios each
- Journey: A start -> B switch -> B complete -> resume A -> A complete -> C start -> C complete
- Base URL: `https://openrouter.ai/api/v1`
- Arbitrator model: `qwen/qwen3.5-9b`
- High-intelligence optional model: `deepseek/deepseek-v4-flash`
- Chatflow SOP LLM model: `qwen/qwen3.5-9b`
- Scenario count: 4
- LLM arbitrator attempts: 7
- API key: runtime environment only, not recorded

## Results

| # | A | B | C | Switch | Resume | Completed | Primary utterance |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | `flight_booking` | `refund_ticket` | `change_flight` | `SUSPEND_AND_START` | `RESUME_TASK` | 3 | 周五早上从北京去深圳，差旅审批说需要出票，想先看可售航班 |
| 1 | `refund_ticket` | `change_flight` | `flight_status` | `SUSPEND_AND_START` | `RESUME_TASK` | 3 | 临时被通知会议取消，明天那段不飞了，票款想处理回来 |
| 2 | `change_flight` | `flight_status` | `flight_booking` | `SUSPEND_AND_START` | `RESUME_TASK` | 3 | 原来的落地安排赶不上会议，需要改签到晚一点 |
| 3 | `flight_status` | `flight_booking` | `refund_ticket` | `SUSPEND_AND_START` | `RESUME_TASK` | 3 | 我去机场接人，想确认那班实际到达时间和登机口 |
