# Browser UAT: Unified Routing Chat Lab 214.5

- URL: http://127.0.0.1:15177/runtime-lab/chat
- Chatflow-bound refund SOP: yes
- SOP catalog count: 15
- Completed scenario journeys: flight_booking, fare_quote, group_booking, ancillary_sales, refund_ticket, change_flight, passenger_info_change, invoice_apply, baggage_service, seat_checkin, flight_status, special_assistance, pet_cabin, irregular_flight, membership_service
- Switch/resume journeys: refund_ticket->flight_status, change_flight->special_assistance, invoice_apply->membership_service, baggage_service->pet_cabin, seat_checkin->irregular_flight
- Expected actions: START_SOP, SUSPEND_AND_START, CONTINUE_ACTIVE_SOP, COMPLETE_TASK, RESUME_TASK
- Final route action: COMPLETE_TASK
- Screenshot: /private/tmp/hify-213-verify3.uX7Jpk/artifacts/slices/034-unified-routing-chat-lab/214.5/browser-uat-unified-routing-chat-lab-scale.png
- Console errors: none
- Failed API responses: none
