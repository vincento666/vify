# 040 Add Node Palette Coze UAT

- Page: `http://127.0.0.1:5173/chatflows/create`
- Bottom add-node flow: click bottom toolbar `添加节点`.
- Edge insert flow: select the START -> END edge, click midpoint `+`.
- Result: both palettes use Coze-like grouped categories `资源`, `业务逻辑`, `输入&输出`, `知识库`; entries render as compact icon + label only, with no description text.
- Bottom screenshot: `screenshots/browser-uat-bottom-palette.png`
- Edge screenshot: `screenshots/browser-uat-edge-palette.png`
- Browser metrics: every group uses 2 grid columns; both palettes reported `smallCount=0`.

Note: the edge insert palette can scroll on the current viewport because its category list is taller than the visible area.
