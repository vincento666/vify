# 193.5 Browser UAT Final Audit

Date: 2026-06-18
URL: http://127.0.0.1:5173/ai-assistant
Model: OpenRouter `qwen/qwen3.5-27b`

## Journey

1. Opened the AI Assistant page at 1440x900.
2. Expanded model config, set the temporary OpenRouter key, then collapsed the
   config panel before screenshots so the key was not exposed.
3. Cleared current session history.
4. Submitted a complex Chinese harness request requiring model planning,
   `README.md` file read, `tdd` skill intent, and a workspace write requiring
   approval.
5. Observed the ReAct sequence over time:
   - poll 1/2: event cards and one running spinner, no model output yet;
   - poll 3: first assembled model output appeared;
   - poll 5/6: tool events and inspector tool rows appeared;
   - poll 9: write approval appeared;
   - approval click: write completed and approval moved into history.
6. Replayed the persisted run, expanded the run group and tool event cards, and
   verified `调用详情` / `输入` / `输出` detail rows.

## Result

All UAT assertions passed:

- one-screen shell with no body scroll and composer visible;
- model selector and temporary model config available;
- no old `收起回显`, `里程碑`, or `动态事件` copy;
- model stream output observed;
- tool echo observed;
- approval observed and clicked;
- completion observed;
- usage labels include `tokens` and `ms` units;
- task panel content comes from real task/tool/approval data;
- expanded tool detail panels expose input and output sections.

## Evidence

- `browser-uat-final.json`
- `browser-uat-expanded-details.json`
- `screenshots/uat-loaded.png`
- `screenshots/uat-submitted.png`
- `screenshots/uat-approved.png`
- `screenshots/uat-final.png`
- `screenshots/uat-expanded-details.png`
