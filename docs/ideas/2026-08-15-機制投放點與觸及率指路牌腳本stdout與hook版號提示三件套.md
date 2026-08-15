---
title: 機制投放點與觸及率指路牌腳本stdout與hook版號提示三件套
type: idea
status: promoted
brainstorm: docs/brainstorms/2026-08-15-mechanism-reach-signpost-requirements.md
created: 2026-08-15
tags: [idea, idea, kunsu, skill, reach]
---

# 機制投放點與觸及率指路牌腳本stdout與hook版號提示三件套

源自 ebook 軍師審計系列第五份（`docs/todos/機制的投放點決定觸及率skill內部指引在手動執行時靜默失效.md`，第四份觀察五獨立成篇）：kunsu 流程改良有兩個投放點——skill 流程步驟只在 skill 被實際呼叫時生效、軍師 CLAUDE.md 每 session 自動載入——而熟練軍師傾向手動執行等效步驟（產物完全相同、指引完全未觸及），skill 內部指引靜默失效且不留痕跡。量化證據：十項機制中六項（斷言層級紀律、done 斷言自查、檔名權威、沉澱訊號、反向路由、殘項清點）只在 skill 內、軍師 CLAUDE.md 零命中；ebook 8/14 全日 8 建立＋6 收尾全手動，v0.10.0 起三道 done 查核可能一次未跑——文件一「部分處置」評估失去資料基礎，R10 判別機制在 done 流程整條被繞過時連輸出機會都沒有（adversarial「判別器與被測現象共用失效通道」在更高層級應驗）。結構定調：攔截點教訓的一般化——必經路徑是動態的，熟練 session 的必經只剩 CLAUDE.md（自動載入）、腳本本身（reply 生效不是指引好、是腳本計算複雜度逼人走 skill）、仍被呼叫的入口（kunsu-inbox／SessionStart hook）；觸及率由手動繞道成本決定。新張力：單一副本教訓與觸及率互相衝突——六項 0 命中是依多副本教訓刻意為之，解法不能是搬內容。候選三件套：(1) **指路牌**——範本＋三軍師 CLAUDE.md／CONCEPTS 補「done 收尾」詞條形狀的一行（母體 CONCEPTS 該詞條已是正確形狀但範本與 live 皆無）：點名各查核＋「手動等效執行不豁免、細節以 SKILL.md 為準」，名字可知、細節單一副本；(2) **腳本 stdout 指路**——new-handoff.sh 等產檔輸出尾端一行「未經 skill 執行時請回讀 SKILL 對應步驟」，手動路徑上唯一倖存載體、零摩擦精準投放（done 無腳本，靠指路牌與 hook 補）；(3) **SessionStart hook 版號變動提示**——比對部署 skill 版號與狀態檔（機器層級，同 hook 掛載層），變動時一行「handoff 已更新至 vX，本輪收尾建議經 skill 執行」，事件驅動零輪詢。否決：提高手動摩擦（反 harness 不做枷鎖前提，且傷害正當手動情境）、查核細節全文搬 CLAUDE.md（副本漂移回歸＋載入成本）。第四份 Q1「沒有下游會查的斷言」已由副官查證慣例部分回應。待評估：hook 狀態檔落點、指路牌是否納入 done 收尾外的流程（add 斷言紀律同樣 0 命中）、audit 系列第五份 Q5 的自指問題（審計文件自身成為中介層）。

## 背景 / 動機


## 下一步

- [ ] 成形後以 `/ce-brainstorm` 推進至 docs/brainstorms/
