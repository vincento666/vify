# Five SOP start coverage

| Case | Expected | Actual |
| --- | --- | --- |
| start:refund_ticket | `{'action': 'START_SOP', 'sopId': 'refund_ticket', 'step': 'info_order', 'replyContains': '请提供退票办理手机号。'}` | `{'action': 'START_SOP', 'sopId': 'refund_ticket', 'step': 'info_order', 'resumeSopId': None, 'reply': '请提供退票办理手机号。'}` |
| start:change_flight | `{'action': 'START_SOP', 'sopId': 'change_flight', 'step': 'info_order', 'replyContains': '请提供改签办理手机号。'}` | `{'action': 'START_SOP', 'sopId': 'change_flight', 'step': 'info_order', 'resumeSopId': None, 'reply': '请提供改签办理手机号。'}` |
| start:invoice_apply | `{'action': 'START_SOP', 'sopId': 'invoice_apply', 'step': 'info_order', 'replyContains': '请提供发票申请办理手机号。'}` | `{'action': 'START_SOP', 'sopId': 'invoice_apply', 'step': 'info_order', 'resumeSopId': None, 'reply': '请提供发票申请办理手机号。'}` |
| start:baggage_service | `{'action': 'START_SOP', 'sopId': 'baggage_service', 'step': 'info_order', 'replyContains': '请提供行李服务办理手机号。'}` | `{'action': 'START_SOP', 'sopId': 'baggage_service', 'step': 'info_order', 'resumeSopId': None, 'reply': '请提供行李服务办理手机号。'}` |
| start:seat_checkin | `{'action': 'START_SOP', 'sopId': 'seat_checkin', 'step': 'info_order', 'replyContains': '请提供值机选座办理手机号。'}` | `{'action': 'START_SOP', 'sopId': 'seat_checkin', 'step': 'info_order', 'resumeSopId': None, 'reply': '请提供值机选座办理手机号。'}` |
