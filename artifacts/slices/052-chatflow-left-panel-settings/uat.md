## Browser UAT

- URL: http://127.0.0.1:5173/chatflows/create
- Viewport: current in-app browser compact canvas width.
- Verified dialog settings side panel renders on compact viewports instead of disappearing.
- Verified collapsing the side panel keeps the canvas stage at normal width and leaves the bottom toolbar clickable.
- Verified expanding the side panel restores the dialog settings panel.
- Verified guide question rows expose semantic labels, Chinese delete labels, lightweight icons, and placeholder text.
- Verified adding a guide question creates `引导问题 4`, accepts text input, and can be removed without leaving stale UI.
- Screenshot: `screenshots/browser-uat-left-panel-settings.png`
