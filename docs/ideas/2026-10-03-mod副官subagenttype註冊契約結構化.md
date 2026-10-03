---
title: mod：副官 subagent type 註冊，契約結構化
type: idea
status: inbox
created: 2026-10-03
tags: [idea, kunsu, mod, claude-code]
---

# mod：副官 subagent type 註冊，契約結構化

## 背景 / 動機

範本「副官慣例」的契約（證據原文回傳＋`檔案:行號`、提取逐份清單含零命中明列、判斷不外包）現靠 CLAUDE.md 文字提醒，忙碌 session 可能漏用。

## 做法

以 mod 的 `$.agent.register` 註冊一個「副官」subagent type，把契約寫進 system prompt；軍師派副官時直接選型別。契約從規範變結構，但只是預填、不限能力——符合 harness 不做枷鎖前提。

## 待決

與範本副官慣例小節的關係（mod 存在時範本指路句改指型別；mod 不存在時文字慣例照舊）。

## 下一步

- [ ] 成形後以 `/ce-brainstorm` 推進至 docs/brainstorms/
