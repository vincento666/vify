# Browser UAT: Unified Routing Chat Lab 034.6

- URL: http://127.0.0.1:5176/runtime-lab/chat
- Chatflow-bound refund SOP: no
- SOP catalog count: 15
- Completed scenario journeys: flight_booking, fare_quote, group_booking, ancillary_sales, refund_ticket, change_flight, passenger_info_change, invoice_apply, baggage_service, seat_checkin, flight_status, special_assistance, pet_cabin, irregular_flight, membership_service
- Switch/resume journeys: refund_ticket->flight_status, change_flight->special_assistance, invoice_apply->membership_service, baggage_service->pet_cabin, seat_checkin->irregular_flight
- Expected actions: START_SOP, SUSPEND_AND_START, CONTINUE_ACTIVE_SOP, COMPLETE_TASK, RESUME_TASK
- Final route action: COMPLETE_TASK
- Screenshot: /Users/vincento/work/develop/hify/artifacts/slices/034-unified-routing-chat-lab/034.6/browser-uat-unified-routing-chat-lab-scale.png
- Console errors: none
- Failed API responses: none
