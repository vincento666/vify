# Browser UAT

Date: 2026-06-07

Target: http://127.0.0.1:5173/chatflows/create

Verified:

- Compact in-app browser width hides/collapses the dialog settings panel without losing canvas nodes.
- Opening the chatflow test-run panel keeps Start and End node centers inside the visible canvas area.
- The bottom toolbar stays inside the visible canvas instead of moving to a negative left coordinate.
- Test-run runtime parameters remain available for `sys.conversation_id`, `sys.user_id`, `sys.channel`, and `sys.channel_id`.
- Direct Chatflow `/runs` API normalizes `message`, `conversationId`, `userId`, and `channelId` into `sys.query`, `sys.conversation_id`, `sys.user_id`, `sys.channel`, and `sys.channel_id`.

Geometry:

- Right panel starts at `483.25`.
- Start node center is `98.57`.
- End node center is `376.21`.
- Toolbar left is `17.5`.

Screenshot:

![browser UAT collapse open](screenshots/browser-uat-collapse-open.png)
