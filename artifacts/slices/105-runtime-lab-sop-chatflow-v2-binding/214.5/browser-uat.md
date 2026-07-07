# Browser UAT: Runtime Lab SOP Chatflow V2 Binding

- URL: http://127.0.0.1:15177/runtime-lab/chat
- Session: #1504
- Journey: refund_ticket starts through Chatflow runtime v2, invoice_apply interrupts as a second bound SOP, refund_ticket resumes through runtime v2
- Observed refund trace events: workflow_run_started, user_message, workflow_node_started, node_status_changed, workflow_node_waiting, node_status_changed, workflow_run_interrupted, workflow_run_resumed, workflow_node_started, node_status_changed, workflow_node_waiting, node_status_changed, workflow_run_interrupted, workflow_run_resumed, workflow_node_started, node_status_changed, workflow_node_completed, node_status_changed, workflow_node_started, node_status_changed, workflow_node_completed, node_status_changed, workflow_node_started, node_status_changed, workflow_node_waiting, node_status_changed, workflow_run_interrupted, workflow_run_resumed, workflow_node_started, node_status_changed, workflow_node_completed, node_status_changed, workflow_node_started, node_status_changed, workflow_node_completed, node_status_changed, workflow_node_started, node_status_changed, workflow_node_completed, node_status_changed, workflow_run_completed
- Screenshot: /private/tmp/hify-213-verify3.uX7Jpk/artifacts/slices/105-runtime-lab-sop-chatflow-v2-binding/214.5/screenshots/runtime-lab-sop-v2-binding.png
- Console errors: none
- Failed API responses: none
