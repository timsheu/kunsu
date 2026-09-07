---
title: 大範圍字面替換的正確性後檢查——完整性檢查看不見的那一半，與語言審查工具的分流判準
date: 2026-09-07
category: workflow-issues
module: kunsu-docs-consistency
problem_type: workflow_issue
component: development_workflow
severity: high
root_cause: missing_workflow_step
resolution_type: documentation_update
applies_when:
  - "對多份文件做大範圍字面替換（術語改名、指令形改寫、品牌遷移），且替換前後的語法角色不同"
  - "被替換的字面帶有語法功能字元（空格作參數分隔、量詞作修飾），改寫後該字元失去原語意"
  - "既有機械檢查只驗「舊字面是否已清空」，未驗「新字面讀不讀得通」"
  - "專案有「範本 → 實例」複製鏈，母體的字面缺陷會隨遷移波次複製到多個 live repo"
  - "以語言審查工具（linter、zhtw MCP）審稿，工具無法分辨 repo 既有慣例術語與本輪新增字面"
symptoms:
  - "替換後中文與中文之間多出半形空格，渲染與純文字檢視皆難以目視察覺"
  - "「reply 子指令 指令回覆」等重複詞——舊句尾的量詞與新字面自帶的詞性重疊"
  - "consistency-check 全項 PASS、pytest 全過，缺陷仍存在且已 commit 並擴散至三個 live repo"
  - "語言審查工具報 32 warning，絕大多數是本輪 diff 未動、僅因同行其他改動被算成新增行的既有慣例術語"
  - "perl 替換全部失敗但 exit 0、無錯誤訊息、檔案零改動——依 exit code 判定成功即產生假修復"
related_components: [tooling, documentation]
tags: [literal-migration, formatting-residue, consistency-check, completeness-vs-correctness, linter-triage, template-propagation, silent-failure, batch-replacement]
---

# 大範圍字面替換的正確性後檢查——完整性檢查看不見的那一半，與語言審查工具的分流判準

## Context

commit `438e176`（ADR 019 kunsu 通用化）把七份 SKILL.md 與周邊文件做字面中性化：把 Claude Code 專屬的斜線指令形改寫成 agent 中立的 skill 名，例如 `/handoff reply` 改寫為「handoff skill 的 reply 子指令」。

該輪已有機械把關：`scripts/consistency-check.sh` 的 L 項（九檔去 frontmatter、Agent 對應表與 code fence 後，內文不得再有裸斜線形）與 M 項（七份 Agent 對應表逐字一致），當時 30 項全 PASS。改動並隨第九波遷移複製到 ebook、ivm、px 三個 live 軍師 repo。

隔日（2026-09-07）在 commit 前以 zhtw MCP 工具審稿，抓到 L 項完全看不見的兩類殘留。

**（a）參數分隔空格變成中文之間的多餘半形空格。** 原字面 `/todo add ` 尾端那個空格是 shell 意義上的參數分隔符；替換後尾詞變成中文「子指令」，這個空格失去語法角色，只剩排版瑕疵：

```
用 todo skill 的 add 子指令 記成一檔一項的技術債
                        ↑ 已無分隔語意
```

**（b）重複詞。** 原句「對方可用全域 `/handoff reply` 指令回覆」的「指令」是修飾斜線形的量詞；替換成「子指令」後語意重疊，變成「handoff skill 的 reply 子指令 指令回覆」。

兩類共九處，且都在 `438e176` 就已 commit，並隨第九波遷移複製進三個 live 軍師的 CLAUDE.md。母體與 live 同時帶病，一路到下一輪審稿才被抓到——母體以 `409017b` 修復，live 延到第十波（`55ff03f`、`1726308`、`32f4b2c`）才收斂。

**缺口的性質**：L 項驗證的是替換**完整性**——目標字面還在不在，可以用「字串不存在」機械判定。它對替換**正確性**——替換後那句話讀不讀得通——零觀測。這是兩個不同的失效面，完整性 PASS 不蘊含正確性。

同一家族的第二例已記錄於 [assertion-level-discipline-coverage-gap.md](./assertion-level-discipline-coverage-gap.md) 第五節：consistency-check K 項原本比對 shell 腳本的**原始碼字面**，`echo` 雙引號內的反引號會被指令替換，stderr 實際印出殘句，靜態比對卻假 PASS，因而改為實跑比對。K 項治的是「執行期展開盲區」，本次缺口是「替換正確性盲區」，兩者共同的結構是**檢查方法本身有盲區，使失效不可見**。

## Guidance

### 一、批次替換的後檢查清單

替換完成後依序做四件事，不要只看 exit code。

**（1）以零斷言驗證替換真的生效**（perl 的靜默失敗見第四節）：

`grep -c` 算的是行數，行數為零等價於出現次數為零，對零斷言足夠：

```bash
before=$(grep -cF '/handoff reply' "$f" || true)   # || true：grep 命中 0 時 exit 1
# ...執行替換...
if grep -qF '/handoff reply' "$f"; then
  echo "替換未生效（替換前 ${before} 行仍在）：$f"; exit 1
fi
```

**（2）掃「替換尾詞 ＋ 半形空格 ＋ 中文」。** 這是（a）類的通用形狀：凡替換文字的尾端是中文字，原字面後方的空格就成為瑕疵。此窄形在本 repo 中性化涉及的十四份文件上實測噪訊為零：

```bash
grep -rnE '子指令[[:blank:]]+[^ -~]' --include='*.md' skills docs/playbooks README.md CONCEPTS.md
```

**在 macOS 上務必用 `[[:blank:]]`，不要用 `[ \t]`。** BSD grep（stock `/usr/bin/grep`）的 bracket expression 內，`\t` 是字面的反斜線與 `t`，不是 tab。實測會誤中「子指令t記成」、同時漏抓真正以 tab 分隔的那一行。python 的 `re` 沒有這個問題，`[ \t]` 在 python 側正確。

**（3）掃重複詞。** 替換文字若吸收了原句量詞的語意，量詞會留在後面：`grep -nF '子指令 指令'`，以及順序踩錯後的無空格產物 `grep -nF '子指令指令'`（見第五節）。注意帶空格那一形已被（2）的樣式涵蓋（「指」是非 ASCII），（3）真正獨佔的是無空格形——做成機械檢查時兩者必須互斥，否則同一處會被計兩次。

**（4）把 diff 當散文讀一遍，或送進語言審查工具。** 形狀（2）（3）只覆蓋已知的兩類；語意重疊、語序不順這類問題沒有機械形狀，只能靠讀。

### 二、機械檢查落點建議：consistency-check 新增 P 項（提案，尚未實作）

`409017b` 只修了文件，**沒有動 `scripts/consistency-check.sh`，機制缺口目前仍開著**。以下為貼合該腳本既有風格（python3 heredoc、檔案清單寫死、`ok`／`ng` 兩態、失敗訊息帶系統後果）的提案，現有檢查項字母已用到 O，故取 P：

```bash
  # --- P. 替換正確性（ADR 019 字面中性化的後檢查）---
  # L 項驗替換「完整性」（斜線形還在不在，字串不存在即可判定）；P 項驗「正確性」（替換後讀不讀得通）。
  # 438e176 時 L 全 PASS，仍留下九處「子指令」後的參數分隔空格與一處量詞重複，並隨第九波遷移
  # 複製進三個 live 軍師的 CLAUDE.md。含 frontmatter（description 亦為散文，與 L 刻意不同）。
  # 新增「斜線形 → 中文結尾語」的替換規則時同步增列樣式。
  p_out="$(python3 - <<'PYP'
import re
files = ["skills/handoff/SKILL.md","skills/todo/SKILL.md","skills/kunsu-init/SKILL.md","skills/kunsu-inbox/SKILL.md",
         "skills/kunsu-apply/SKILL.md","skills/kunsu-report/SKILL.md","skills/kunsu-list/SKILL.md",
         "skills/kunsu-init/assets/templates/kunsu-claude.md","skills/kunsu-init/assets/templates/kunsu-concepts.md",
         "docs/playbooks/end-to-end-workflow.md","docs/playbooks/dashboard.md","README.md","CONCEPTS.md"]
bad = []
for f in files:
    try:
        s = open(f, encoding="utf-8").read()
    except Exception as e:
        bad.append(f"{f}: 無法讀取（{e}）"); continue
    s = re.sub(r'^```.*?^```[ \t]*$', '', s, flags=re.S | re.M)   # 同 L 項去 fenced code block
    ns = len(re.findall(r'子指令[ \t]+[^\x00-\x7f]', s))          # 尾詞後殘留的參數分隔空格
    nd = s.count('子指令指令')                                     # 通用規則先跑吃掉空格後的重複詞
    if ns or nd: bad.append(f"{f}: 多餘空格 {ns} 處、重複詞 {nd} 處")
print("\n".join(bad))
PYP
)"
  if [[ -z "${p_out}" ]]; then
    ok "P  替換正確性：中文尾詞後無參數分隔空格殘留、無量詞重複"
  else
    ng "P  替換後文字瑕疵（L 項對此零觀測；範本殘留會隨波次遷移複製進每個 live 軍師的 CLAUDE.md）：$(echo "${p_out}" | tr '\n' '；')"
  fi
```

三個實作要點。**（i）兩個計數必須互斥**：`子指令 指令` 的「指」是非 ASCII，已被空格樣式吃掉，重複詞真正獨佔的只有無空格形，故用純字面 `count('子指令指令')` 而非 regex，否則同一處會被計兩次。**（ii）不要自帶 `command -v python3` 守衛**，要併進 L／M 既有的那個守衛區塊內——自帶守衛且沒有 else 的話，無 python3 的機器上 L／M 會告知略過、P 卻靜默消失，正好違反本文自己主張的「靜默必須單義化」；折進去後把該區塊的 else 訊息改成「L/M/P 需要 python3，略過」。**（iii）別忘了腳本頂部的檢查項清單**（A–O 全數在列）要同步補 P 條目，否則自我說明漏一項。`try/except` 保留，與 L／M 一致，且 P 的清單多了幾個 L 不讀的檔，缺檔要能報。


**刻意不採的更寬形狀**：「中文 ＋ 半形空格 ＋ 中文」的全域掃描。實測在同一批檔案上有四處既有命中（CLAUDE.md 的「status 為 已解決／已封存 但未歸檔」、「已購 快取」搜尋詞引用、todo SKILL 的「＋ 內文 H1」），做成 FAIL 級會製造常態假警報。這個寬形可以留在文件裡當一次性稽核指令，不進常設檢查。

### 三、語言審查工具發現的分流判準

zhtw 兩批共回報 0 error、32 warning、12 info，逐項檢視後**只有三類是本輪真瑕疵**（上述 a、b，加上 CONCEPTS「確認 commit」詞條因插入 Codex 語意而變成連續兩組括號）。其餘幾乎全是 repo 既有慣例術語：協議、原始碼、缺省、查找、前綴、後綴、發送、一次性、只讀——本輪 diff 沒動到那些字，只是它們所在的整行因為別的改動被 diff 算成新增行而已。

**判準：那個字在舊版是否也存在。** 存在即屬既有慣例，不在本輪範圍，記下但不改。

```bash
# 對語言工具回報的每個詞，比對新舊出現次數
f=skills/kunsu-init/assets/templates/kunsu-claude.md
for w in 協議 原始碼 缺省 查找 前綴 後綴 發送 一次性 只讀 子指令; do
  old=$(git show HEAD:"$f" | grep -cF "$w")
  new=$(grep -cF "$w" "$f")
  if [ "$new" -gt "$old" ]; then verdict="← 本輪新增 $((new-old)) 處，逐處檢視"; else verdict="既有慣例，不在本輪範圍"; fi
  printf '%-8s 舊=%-4s 新=%-4s %s\n' "$w" "$old" "$new" "$verdict"
done
```

大段落改寫時改用逐行版本：`git diff -U0 -- "$f" | grep -E '^[+-]' | grep -v '^[+-][+-]' | grep -F "$w"`——若 `-` 側也含該字，即為沿用而非新增。

**本輪確認的誤報**，記下來供下次直接駁回、不重查：

| 工具判定 | 實際 | 說明 |
|---|---|---|
| 「只讀最新回覆」→ read-only ＝ 唯讀 | 誤報 | 是「只有讀」的動詞用法 |
| 「一次性訊息」→ disposable ＝ 拋棄式 | 誤報 | 是 one-time／一次性事件 |
| 「試點單輪通過」→ via/through ＝ 透過 | 誤報 | 是 pass／通過測試 |

### 四、`perl -CSD -Mutf8` 的靜默失敗

第一次只寫 `perl -CSD` 而沒加 `-Mutf8`：`-CD` 讓檔案內容解成 characters，但命令列 `-e` 的原始碼預設不以 utf8 解讀，pattern 裡的中文字面仍是 bytes，兩者不匹配，於是**全部替換失敗、exit 0、無任何錯誤訊息、檔案零改動**。

實測：

```
$ perl -CSD -i -pe 's/子指令 ([^\x00-\x7f])/子指令$1/g' a.md
無 -Mutf8 exit=0 -> 用 todo skill 的 add 子指令 記成一檔一項   ← 沒生效
$ perl -CSD -Mutf8 -i -pe 's/子指令 ([^\x00-\x7f])/子指令$1/g' b.md
有 -Mutf8 exit=0 -> 用 todo skill 的 add 子指令記成一檔一項   ← 生效
```

兩種防法，擇一：

- 一律加 `-Mutf8`，並在替換後跑第一節（1）的零斷言。**exit code 在這裡不是成功訊號，目標字面歸零才是。**
- 直接改用 python3 一次讀寫。這也是本 repo 的既有慣例——consistency-check 與各歸檔腳本都走 python3 heredoc，編碼在 `open(..., encoding='utf-8')` 明示，不存在這個陷阱：

骨架見下方 Examples（d）。

### 五、替換規則的套用順序：特化先於通用

實測兩種順序：

```
通用先跑 -> ...reply 子指令指令回覆     ← 空格被吃掉，重複詞從此無空格分隔
特化先跑 -> ...reply 子指令回覆         ← 正確
```

通用規則會先把「子指令 指令回覆」壓成「子指令指令回覆」，之後第一節（3）的重複詞偵測（依賴空格形狀）就再也抓不到。**規則排序原則：涵蓋範圍窄、修正語意的規則先跑；涵蓋範圍寬、修正排版的規則後跑。** 順序寫進腳本註解，不要靠記憶。

## Why This Matters

**範本瑕疵是廣播，不是排版問題。** `skills/kunsu-init/assets/templates/kunsu-claude.md` 是每個新軍師 CLAUDE.md 的母本，而 CLAUDE.md 是 agent 每個 session 自動載入的憲章。一處未察覺的替換錯誤會複製到未來每一個 scaffold 出來的軍師，並經波次遷移複製進既有 live 軍師——本次實際發生：九處空格與一處重複詞在 `438e176` 隨第九波遷移進了三個 repo 的 CLAUDE.md，母體修完還得再排一次第十波才收斂。**發現得越晚，需要同步的副本越多**，修復成本隨時間單調上升。

**修復動作本身有實害通道。** live 軍師工作區常年帶著未 commit 的 replies 與 reports（本次三個 repo 合計四十筆）——**未 commit 狀態本身就是 kunsu 協議的「新訊息」訊號**。若遷移時圖省事用 `git add -A`，這些未讀回覆會被夾帶進「文件同步」commit，訊號被靜默清除，軍師端從此看不到那些回覆存在。這正是本 repo 已記錄並建了偵測的事故形狀（`HISTORY_WARN:SMUGGLED_REPLY`，以及 ADR 017 的 PreToolUse 守門）。所以每一次跨 live repo 的文字修復，`git add` 與 `git commit` 都必須帶精確 pathspec。

**這類瑕疵的可觀測性為零。** L 項 PASS、M 項 PASS、175 項 pytest PASS、consistency-check 30 項 PASS——沒有任何機械訊號。發現只能靠人眼或語言工具，而範本一旦 commit 就進入複製鏈。補上 P 項的意義，是把「靠下一輪碰巧有人審稿」換成「下一次跑 consistency-check 就攔下」。

**若照單全收語言工具的建議，破壞面更大。** 「協議」是 kunsu 核心術語（三信箱協議、回覆信箱協議），全 repo 數百處，同時是 CONCEPTS 詞條與 consistency-check H 項 live 軍師抽查的比對字串之一。改一半會讓同一份文件出現新舊字面分歧；若改到 H 項依賴的錨句，live 軍師遷移抽查會變成常態假警報，或反向的假 PASS——機械檢查本身失去可信度，比原本不改更糟。

**perl 靜默失敗會產生假修復。** exit 0、無錯誤、檔案未變。若依 exit code 判定成功並直接 commit，得到的是「commit 訊息宣稱已修、檔案實際未修」的狀態，而且後續不會有人再查（已標記完成）。在需要跨多個 live repo 同步的場景，等於把未修的瑕疵標記為已修並廣播出去，下一個發現的人得先推翻 commit 訊息才找得到真相。

**順序踩錯會製造不可再偵測的殘留。** 「子指令指令回覆」看起來像一個有效的中文字串，重複詞偵測（依賴空格）已失效，語言工具對無空格的中文重複也難以判定，這種殘留會永久留在範本裡。

## When to Apply

- 任何跨檔案的字面批次替換：術語統一、指令形改寫、品牌或命名遷移、API 名稱更新
- **特別是**替換文字尾端為中文，或被替換的字面在句中承擔語法角色（shell 參數分隔、量詞修飾、標點）
- 有「範本 → 實例」複製鏈的專案（scaffold 或 template repo），或改動需經波次遷移同步到多個下游 repo
- 中英混排文件——半形與全形交界處是瑕疵高發區
- 既有機械檢查只驗證「目標字面不存在」時：那個檢查蘊含完整性，不蘊含正確性，正確性要另立檢查項

## Examples

**（a）參數分隔空格殘留**

```diff
- 用 /todo add 記成一檔一項的技術債；/todo list 列出、/todo done 標記解決並歸檔
+ 用 todo skill 的 add 子指令 記成一檔一項的技術債；...     ← 438e176 產出，L 項 PASS
+ 用 todo skill 的 add 子指令記成一檔一項的技術債；...      ← 409017b 修正
```

範本 `kunsu-claude.md` 的實際修正（Invariant #5 與工作流程第 7 步）：

```diff
- ...（handoff skill 的 done 子指令 收尾時改 `done` 並與回覆成對 `git mv`...
+ ...（handoff skill 的 done 子指令收尾時改 `done` 並與回覆成對 `git mv`...

- ...收尾無論經 handoff skill 的 done 子指令 或手動執行等效步驟，歸檔前查核清單以...
+ ...收尾無論經 handoff skill 的 done 子指令或手動執行等效步驟，歸檔前查核清單以...
```

**（b）量詞重複**

```diff
- 對方可用全域 /handoff reply 指令回覆
+ 對方可用全域 handoff skill 的 reply 子指令 指令回覆     ← 438e176，「指令」重疊
+ 對方可用全域 handoff skill 的 reply 子指令回覆          ← 409017b
```

**（c）分流判準實際運作**

zhtw 對 `CONCEPTS.md` 回報「只讀最新回覆」的「只讀」應改「唯讀」。查舊版：`git show HEAD:CONCEPTS.md | grep -c 只讀` 與新版同數，代表本輪未動，判為誤報且屬既有慣例，記下不改。同批 32 個 warning 中，僅三類通過此判準。

**（d）正確的替換腳本骨架**

```bash
python3 - <<'PY'
import re, pathlib
FILES = ["skills/kunsu-init/assets/templates/kunsu-claude.md",
         "docs/playbooks/end-to-end-workflow.md"]
for f in FILES:                                                   # 規則順序即優先序
    p = pathlib.Path(f); s = p.read_text(encoding='utf-8'); orig = s
    s = s.replace('子指令 指令回覆', '子指令回覆')                  # 特化先：量詞重疊
    s = re.sub(r'子指令[ \t]+(?=[^\x00-\x7f])', '子指令', s)        # 通用後：參數分隔符殘留
    if s != orig:
        p.write_text(s, encoding='utf-8'); print(f"changed {f}")
    else:
        print(f"NO-OP {f}")                                        # 零改動顯式，不靜默
PY
# 後檢查：範圍限縮到本次替換的目標，預期無殘留
grep -rnE '子指令[[:blank:]]+[^ -~]|子指令指令' --include='*.md' \
  skills docs/playbooks README.md CONCEPTS.md || echo "OK: 無殘留"
bash scripts/consistency-check.sh
```

後檢查那行的路徑範圍必須收窄到本次替換的目標。掃整個 `.` 會連 `docs/plans/` 的歷史快照與這份學習文件自己的示範字串一起命中（實測十六行），`|| echo` 那句永遠不會印，讀者照抄第一次就得到滿螢幕誤報，接著學會忽略它。

**（e）跨 live repo 修復時的 pathspec 紀律**

```bash
# 工作區有四十筆未 commit 的 replies／reports——未 commit 本身即協議的「新訊息」訊號
git -C "$kunsu" add -- CLAUDE.md docs/README.md docs/HOME.md \
  && git -C "$kunsu" commit -m "docs: 第十波遷移——..." -- CLAUDE.md docs/README.md docs/HOME.md
# 絕不 git add -A：會把未讀回覆一起 commit，訊號靜默消失（HISTORY_WARN:SMUGGLED_REPLY 形狀）
```

## Related

- [assertion-level-discipline-coverage-gap.md](./assertion-level-discipline-coverage-gap.md) — 同家族第二例。第五節記載 consistency-check K 項因 `echo` 反引號被指令替換而靜態比對假 PASS，改為實跑比對。K 項治「執行期展開盲區」，本文治「替換正確性盲區」，共同結構是檢查方法本身有盲區使失效不可見；其「靜默必須單義化」原則可推廣到機械檢查層。
- [handoff-done-closure-gap.md](./handoff-done-closure-gap.md) — live 遷移的舊句 grep 核查紀律（`grep -cF` 舊句恰中一次才整句替換、遷移後反向核查、每個目標系統一筆確認 commit）的權威出處。本文打出該套規則的邊界：反向核查只證明舊字面消失、新字面存在，對替換後多出的半形空格與重複詞零覆蓋。其「遷移遺漏一律是第三方 review 才發現，從不是遷移者自己」在本次再度應證——zhtw 審稿即扮演第三方 review。
- [git-porcelain-scan-script-pitfalls.md](../best-practices/git-porcelain-scan-script-pitfalls.md) — 工具層靜默失敗的同家族先例；第四節的 `perl -Mutf8` 陷阱性質相同。
- 驗證狀態：consistency-check 現況 30 PASS、1 WARN（N 項 Codex hook 未掛載，屬預期）。提議的 P 項窄形已在十四份中性化文件上實測零命中（全 repo 僅一處落在 `docs/plans/2026-07-08-001-...` 歷史快照標題，不在檢查範圍）。三個 live 軍師經第十波遷移後現況為零殘留。**P 項本身尚未實作**，機制缺口仍開著。
