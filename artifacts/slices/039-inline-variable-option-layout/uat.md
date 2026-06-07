# 039 Inline Variable Option Layout UAT

- Page: `http://127.0.0.1:5173/chatflows/create`
- Flow: select END node -> clear response content -> type `{` -> inline variable picker opens.
- Result: variable option renders as compact `output` + `String`; variable name is not ellipsized and the type badge no longer stretches across the row.
- Screenshot: `screenshots/browser-uat-inline-picker.png`
- Browser metric: `nameScrollWidth=38`, `nameClientWidth=38`, `badgeWidth=38.3046875`.
