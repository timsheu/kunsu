---
title: mod：session.send hook 自動補推播定型尾句
type: idea
status: inbox
created: 2026-10-03
tags: [idea, kunsu, mod, claude-code]
---

# mod：session.send hook 自動補推播定型尾句

## 背景 / 動機

handoff add 步驟 6（派發即推播）與 reply 步驟 6（回覆即推播）的定型通知尾句「僅回顯勿開工勿讀檔」靠 SKILL 文字手寫。

## 做法

mod hook `session.send`：收方 session 名稱命中 registry 的 `<軍師>-<角色>` 慣例名時自動補定型尾句，否則放行。SKILL 步驟 6-3 的定型文可降為「由 mod 補句；mod 不存在時手寫」。

## 不做

不用 mod 取代 pretooluse_git_guard.py 與 session hook——python 版 Codex 同份可用（ADR 019），改 mod 等於只剩 Claude Code 有守門。

## 下一步

- [ ] 成形後以 `/ce-brainstorm` 推進至 docs/brainstorms/
