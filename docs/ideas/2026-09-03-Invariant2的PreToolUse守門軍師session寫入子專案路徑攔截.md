---
title: Invariant 2 的 PreToolUse 守門：軍師 session 寫入子專案路徑攔截
type: idea
status: inbox
created: 2026-09-03
tags: [idea, kunsu-inbox, hook, adr-017]
---

# Invariant 2 的 PreToolUse 守門：軍師 session 寫入子專案路徑攔截

Uncle Bob 主張「不能違反的規矩改用後期檢核工具把關」。kunsu 已對 git 側落地（tripwire、ADR 017 git add 守門、MISDECLARED 偵測），但 Invariant 2「不觸碰子專案的檔案系統」仍純靠 CLAUDE.md prose，是唯一還沒有計算載體的核心不變量。

## 背景 / 動機

**ADR 017 四要件檢核**

- 機械可判：Edit／Write／NotebookEdit 的目標路徑，與 `~/.claude/kunsu-registry.json` 中登記於當前軍師底下的子專案路徑做前綴比對即可判定。
- 規則已明文：範本 Invariant 2 與三 live 軍師 CLAUDE.md 皆有。
- 可逆：deny 不改任何狀態。
- 零能力限縮：軍師從無正當寫入子專案的需求。

**疑點**

- Bash 寫入指令（`sed -i`、`tee`、重導向 `>`）的目標路徑解析不如工具參數乾淨，第一版可只攔 Edit／Write／NotebookEdit，Bash 側交由後果面偵測兜底。
- 逃生門比照 `KUNSU_ADD_GUARD_OFF` 環境變數單次放行；deny 事件記入掃描統計檔 `~/.claude/kunsu-scan-stats.json`，與 `GUARD_DENY` 同一觀測體系。
- 身分判定沿用 pretooluse_git_guard.py 的 raw registry 加 git root 比對，fail-open。

屬 ADR 層級（ADR 017 修訂或新 ADR），未經使用者審定不實作。

## 下一步

- [ ] 成形後以 `/ce-brainstorm` 推進至 docs/brainstorms/
