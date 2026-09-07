# 執行追蹤：kunsu 通用化雙部署（計畫 2026-09-06-001）

分支 `feat/codex-agent-neutral-deployment`；不主動 commit，各單元完成後由使用者決定。

- [x] U1 ADR candidate 019＋README 索引補 017／018／019＋origin 目錄改正
- [x] U1 ADR doc review 一輪（3 persona 13 筆：能力類別判準、緊接下一回合、未列 agent 預設、觀測邊界改本地可逆、hooks 索引漂移 N 項、AGENTS.md symlink 取代全域 fallback、Invariant 2 判準句）
- [x] U2 install.sh 第二目標、pre-flight、--adopt、kunsu-dashboard frontmatter／openai.yaml（九場景實跑）
- [x] U3 七份 SKILL.md 字面中性化＋Agent 對應表＋版號（兩副官；3a 依 ADR 修訂為能力類別）
- [x] U4 kunsu-inbox 掛載說明 Codex 段（hooks 順序、config 節含 AGENTS.md symlink 說明、docstring）
- [x] U5 腳本文案中性化＋測試（含 new-handoff.sh 定型文字兩副本同步；pytest 39）
- [x] U6 範本、CLAUDE.md、CONCEPTS、README、kunsu-init ⑥-2 AGENTS.md symlink（Invariant 3 字面與開發狀態條目待 ADR accepted 後補）
- [x] U7 consistency-check L／M／N 項、D 擴、H 大小 WARN（29 PASS；H 鏈「Agent 對應表」字串待 U9）
- [~] U8 scripts/codex-pilot.sh＋playbook：五輪迭代（bash 3.2 兩陷阱、realpath、--stat 縮寫、canary 兩段式）；機制面八個 AE 跨第 3／5 輪全部成立過，但 Codex 免費額度於第五輪用盡（重置 2026-10-06），尚無單輪全綠；已加 turn.failed 早停
- [x] U9 三 live 軍師第九波遷移（使用者裁決接受合併證據；ebook 08d9f12／ivm cd2bb83／px 8894d6f）
- [x] 收尾：pytest 176、consistency-check 29 PASS、install.sh 重佈署、CLAUDE.md 開發狀態條目、docs/README 索引
- [x] Tier 2 code review（sonnet 重派 9 persona）：actionable 10＋residual 3 全數併修（install.sh 懸空 symlink／--adopt 確認、codex-pilot RC 直呼、consistency-check O 項六場景實跑、README 雙 agent 措辭）；pytest 176、consistency-check 30 PASS、install.sh 重佈署
- [ ] 待額度重置（2026-10-06）補跑 `scripts/codex-pilot.sh` 單輪全綠 → ADR 019 生效條件
- [ ] ADR 019 使用者審定 → accepted 後改 CLAUDE.md Invariant 3 字面與「首次實證」措辭
- [ ] 手動核對清單（playbook）：hooks.json 掛載信任、TUI /clear、真實路徑 .git 核准
