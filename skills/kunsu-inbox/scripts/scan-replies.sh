#!/usr/bin/env bash
# scan-replies.sh — 掃描軍師 docs/handoffs/replies/ 中未 commit 的新回覆檔案
# 同時執行 tripwire 核對：docs/handoffs/ 下是否有授權範圍之外的意外變更
#
# 用法：scan-replies.sh <kunsu-root-abs-path>
#
# 輸出（stdout，每行一筆）：
#   NEW_REPLY:<相對路徑>          新回覆（replies/ 頂層 .md 檔案，untracked 或 index 新增）
#   TRIPWIRE:<XY> <相對路徑>      意外變更（授權範圍之外的任何狀態變更）
#   TRIPWIRE:<XY> <src> -> <dst>  意外搬移（rename 形式，路徑欄為雙側複合字串）
#   HISTORY_WARN:<類型> <內容>    歷史夾帶警示（advisory，不影響 exit code；見下方
#                                 「歷史夾帶偵測與統計」段）
#
# exit code：
#   0 — 正常完成（含零回覆、零 tripwire；HISTORY_WARN 不改變 exit code）
#   1 — 參數錯誤或非 git repo 根
#   2 — tripwire 觸發（docs/handoffs/ 下有授權範圍外的未 commit 變更）
#
# 分類規則（if/elif 順序即授權邊界，不可調換）：
#   1. 非 rename 的 docs/handoffs/archive/* 變更一律靜默略過 —— 歸檔區由軍師
#      session 管理（/handoff done 的授權歸檔），不做狀態欄篩選，與
#      scan-applications.sh 對 archive/ 的取捨一致：untracked 檔先 git add 再
#      git mv 後在 porcelain 呈現為 archive/ 下的 A 新增而非 rename，亦涵蓋在
#      此分支。此分支必須最先評估：後方 catch-all `docs/handoffs/*` 會匹配
#      archive/ 下所有路徑，archive 分支必須先行攔截。
#   2. replies/ 頂層 <名稱>.md（名稱不含 /）：?? 或 index A ＝新回覆；其餘
#      狀態（修改／刪除已 commit 的回覆）＝tripwire——回覆檔 append-only、
#      任何人不編輯既有回覆（範本回覆信箱協議明訂），合法搬移僅授權歸檔
#      rename（形狀 b）且不落入本分支。2026-08-12 起與協議字面對齊，取消
#      舊版「靜默忽略」取捨。
#   3. docs/handoffs/ 下的其他路徑（頂層交接檔的新增／修改／刪除、非預期
#      巢狀、非 .md）＝tripwire。
#   rename（XY 含 R/C，格式 old -> new）：雙側核驗，僅以下兩形狀視為
#   /handoff done 的授權歸檔（可攜帶內容修改，如 status: done 的 Edit——
#   git mv 對含未暫存修改的檔案呈現 RM，本豁免僅驗路徑形狀、不看 XY）：
#     a. src 為 docs/handoffs/ 頂層 .md 且 dst 位於 docs/handoffs/archive/
#     b. src 為 docs/handoffs/replies/ 頂層 .md 且 dst 位於
#        docs/handoffs/archive/replies/
#   其餘涉及 docs/handoffs/ 任一側的搬移（含 archive/→頂層、replies/→頂層
#   等反向或越界搬移，以及 archive/ 內部搬移——「靜默略過」僅指非 rename 的
#   路徑變更）＝tripwire，與 scan-applications.sh 行為一致。不驗 src/dst
#   basename 同名（/handoff done 的 git mv 天然同名，與另兩支腳本一致）。
#
# 授權邊界的威脅模型（為何 archive/ 靜默豁免是可接受取捨）：
#   投遞腳本（new-handoff-reply.sh）只往 replies/ 頂層寫；會寫 archive/ 的
#   只有軍師 session 自己執行的 /handoff done 歸檔。豁免 archive/ 等於信任
#   軍師自身的合法寫入，與 scan-applications.sh 已接受並記錄的取捨等價。
#
# 路徑處理：
#   porcelain 輸出含空格或特殊字元時 git 以雙引號括住路徑，腳本會自動去除引號

set -euo pipefail

KUNSU_ROOT="${1:-}"

if [[ -z "$KUNSU_ROOT" ]]; then
  echo "錯誤：缺少軍師根路徑（第一個參數）" >&2
  echo "用法：scan-replies.sh <kunsu-root-abs-path>" >&2
  exit 1
fi

# 驗證是 git 儲存庫
if ! git -C "$KUNSU_ROOT" rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "錯誤：\"$KUNSU_ROOT\" 不是 git 儲存庫" >&2
  exit 1
fi

# 驗證是 git 儲存庫根（而非子目錄）
GIT_ROOT="$(git -C "$KUNSU_ROOT" rev-parse --show-toplevel)"
if [[ "$GIT_ROOT" != "$KUNSU_ROOT" ]]; then
  echo "錯誤：\"$KUNSU_ROOT\" 不是 git 儲存庫根（根為 \"$GIT_ROOT\"）" >&2
  exit 1
fi

HAS_TRIPWIRE=0
TRIPWIRE_LINES=""

# 去除 git 引號（路徑含空格或特殊字元時 git 以雙引號括起）
strip_quotes() {
  local p="$1"
  if [[ "${p:0:1}" == '"' && "${p: -1}" == '"' ]]; then
    printf '%s' "${p:1:${#p}-2}"
  else
    printf '%s' "$p"
  fi
}

# 解析 git status --porcelain 輸出
# 格式：XY <path>  或  XY <old> -> <new>（rename/copy）
# X = index 狀態欄（第一字元）；Y = work tree 狀態欄（第二字元）
while IFS= read -r line; do
  [[ -z "$line" ]] && continue

  XY="${line:0:2}"
  X="${line:0:1}"
  path_raw="${line:3}"

  # rename/copy 格式：XY old -> new（如 git mv 產生的 R 狀態）
  if [[ "$path_raw" == *" -> "* ]]; then
    src_raw="${path_raw%% -> *}"
    dst_raw="${path_raw#* -> }"
    src="$(strip_quotes "$src_raw")"
    dst="$(strip_quotes "$dst_raw")"

    # 與 docs/handoffs/ 無關的搬移：略過
    if [[ "$src" != docs/handoffs/* && "$dst" != docs/handoffs/* ]]; then
      continue
    fi

    # 授權歸檔豁免形狀 a：src 為頂層交接檔 .md 且 dst 位於 archive/，
    # 兩條件缺一即走 tripwire（含 archive/→頂層的反向搬移）。
    src_rel="${src#docs/handoffs/}"
    if [[ "$src" == docs/handoffs/*.md && "$src_rel" != */* \
          && "$dst" == docs/handoffs/archive/* ]]; then
      continue
    fi

    # 授權歸檔豁免形狀 b：src 為 replies/ 頂層回覆檔 .md 且 dst 位於
    # archive/replies/（/handoff done 將交接與其回覆成對歸檔）。
    src_rel_replies="${src#docs/handoffs/replies/}"
    if [[ "$src" == docs/handoffs/replies/*.md && "$src_rel_replies" != */* \
          && "$dst" == docs/handoffs/archive/replies/* ]]; then
      continue
    fi

    HAS_TRIPWIRE=1
    TRIPWIRE_LINES+="TRIPWIRE:$XY $src -> $dst"$'\n'
    echo "TRIPWIRE:$XY $src -> $dst"
    continue
  fi

  path_part="$(strip_quotes "$path_raw")"

  # 分類判斷：archive/ 分支必須最先評估（見檔頭分類規則說明）
  if [[ "$path_part" == docs/handoffs/archive/* ]]; then
    # 歸檔區：軍師 session 管理範圍（含 git add 後搬移產生的 A 新增），靜默略過
    continue
  elif [[ "$path_part" == docs/handoffs/replies/*.md \
          && "${path_part#docs/handoffs/replies/}" != */* ]]; then
    # replies/ 頂層回覆檔：untracked (??) 或 index 新增（X 為 A，涵蓋 A  與 AM）＝新回覆
    if [[ "$XY" == "??" ]] || [[ "$X" == "A" ]]; then
      echo "NEW_REPLY:$path_part"
    else
      # 修改／刪除已 commit 的回覆＝tripwire（append-only 原則之外的形狀）
      HAS_TRIPWIRE=1
      TRIPWIRE_LINES+="TRIPWIRE:$XY $path_part"$'\n'
      echo "TRIPWIRE:$XY $path_part"
    fi
  elif [[ "$path_part" == docs/handoffs/* ]]; then
    # tripwire：頂層交接檔的新增／修改／刪除、非預期巢狀或非 .md 路徑
    HAS_TRIPWIRE=1
    TRIPWIRE_LINES+="TRIPWIRE:$XY $path_part"$'\n'
    echo "TRIPWIRE:$XY $path_part"
  fi

done < <(git -C "$KUNSU_ROOT" -c core.quotepath=false status --porcelain -uall 2>/dev/null)
# -uall：強制逐檔列出 untracked（預設會把整個未追蹤目錄收合為 "dir/" 一行，
# 導致 replies/ 目錄本身未被追蹤時新回覆無法逐檔偵測）

# --- 歷史夾帶偵測與統計（advisory，不影響上方掃描結果與 exit code）---
#
# 逐 commit 檢視上次掃描後新出現的 commit，偵測已 commit 歷史中破壞
# 「未 commit 即未處理」狀態訊號的形狀：
#   HISTORY_WARN:SMUGGLED_REPLY —「docs: 歸檔」開頭的 commit 新增（diff-filter A）
#     了 replies/ 頂層回覆檔。歸檔 commit 只該搬移（rename 至 archive/），頂層
#     新增即夾帶——把未讀回覆靜默轉為已處理（2026-08-29 ebook 軍師 git add -A
#     夾帶 16 份未讀回覆的事故形狀）。
#   HISTORY_WARN:BATCH_REPLY_ADD — 任意單一 commit 新增 ≥6 份頂層回覆
#     （啟發式：批次處理合法，但提示核對是否整批掃入）。
#   HISTORY_WARN:MISDECLARED_ARCHIVE_ADD — 訊息不以白名單前綴（docs: 歸檔、
#     docs: 審核申請）開頭的 commit 新增了任一信箱 archive/（handoffs／reports／
#     applications）檔案——commit 內容超出訊息宣告範圍的形狀（2026-08-31 ebook
#     軍師「建立交接」commit 兩度夾帶上報歸檔的事故形狀，ADR 018）。
# 另記 TRUNCATED 事件（rev-list 滿 200 筆、最舊段未檢視——僅入統計檔不輸出警示）。
# 每筆警示只在事發後的第一次掃描出現（基線 commit 前進即不重報）。
#
# 統計寫入 $KUNSU_SCAN_STATS_FILE（預設 ~/.claude/kunsu-scan-stats.json；機器
# 層級、不進任何 repo，環境變數可覆寫供測試隔離）：各軍師的掃描次數、tripwire
# 次數、歷史警示次數與事件明細。用途是給「未 commit 即未處理」狀態訊號的脆弱度
# 累積數據——警示頻率高到不可接受時才有依據啟動狀態載體重設計的 ADR 討論。
#
# 首次執行僅記錄基線 commit、不回溯歷史；基線 commit 已不在歷史（reset／rebase）
# 時重設基線並記一筆 BASELINE_RESET。任何失敗 fail-open：不影響掃描結果與
# exit code；python3 不可用時整段靜默跳過。
if command -v python3 >/dev/null 2>&1; then
  SCAN_TRIPWIRE_LINES="$TRIPWIRE_LINES" python3 - "$KUNSU_ROOT" "$HAS_TRIPWIRE" <<'PYEOF' || true
import datetime
import json
import os
import subprocess
import sys

try:
    root = sys.argv[1]
    has_tripwire = sys.argv[2] == "1"
    tripwire_lines = os.environ.get("SCAN_TRIPWIRE_LINES", "").strip()
    stats_path = os.environ.get("KUNSU_SCAN_STATS_FILE") or os.path.expanduser(
        "~/.claude/kunsu-scan-stats.json"
    )
    replies_prefix = "docs/handoffs/replies/"

    def git(*args: str) -> "subprocess.CompletedProcess[str]":
        return subprocess.run(
            ["git", "-C", root, "-c", "core.quotepath=false", *args],
            capture_output=True,
            text=True,
        )

    head_proc = git("rev-parse", "HEAD")
    if head_proc.returncode != 0:
        sys.exit(0)  # 空 repo：無歷史可查，本輪不記統計
    head = head_proc.stdout.strip()

    try:
        with open(stats_path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict) or not isinstance(data.get("kunsu"), dict):
            data = {"version": 1, "kunsu": {}}
    except Exception:
        data = {"version": 1, "kunsu": {}}

    kunsu_map = data["kunsu"]
    ent = kunsu_map.setdefault(root, {})
    events = ent.setdefault("events", [])
    if not isinstance(events, list):
        events = ent["events"] = []
    now = datetime.datetime.now().isoformat(timespec="seconds")
    warns: list[str] = []

    last = ent.get("last_checked_commit")
    if last and git("cat-file", "-e", str(last)).returncode != 0:
        events.append(
            {
                "ts": now,
                "type": "BASELINE_RESET",
                "detail": f"基線 {str(last)[:12]} 已不在歷史（reset/rebase），重設為 {head[:12]}",
            }
        )
        last = None

    if last and last != head:
        revs = git(
            "rev-list", "--reverse", "--max-count=200", f"{last}..{head}"
        ).stdout.split()
        # 三信箱 archive/ 前綴與正當歸檔訊息白名單（MISDECLARED_ARCHIVE_ADD，
        # ADR 018）——startswith 前綴比對，不採「任意位置含詞」（標題含「歸檔」的
        # 建立交接 commit 正是事故吞噬者形狀，含詞判準會豁免它）；新增正當歸檔
        # 訊息形狀時須同步擴列（ADR 018 修訂事項）
        archive_prefixes = (
            "docs/handoffs/archive/",
            "docs/reports/archive/",
            "docs/applications/archive/",
        )
        whitelist_prefixes = ("docs: 歸檔", "docs: 審核申請")
        if len(revs) == 200:
            # rev-list --max-count 先限量（取最新 N 筆）再反轉：滿載代表最舊段被
            # 靜默跳過，而基線仍會前進至 HEAD——記事件聲明本輪數據不完整
            events.append(
                {
                    "ts": now,
                    "type": "TRUNCATED",
                    "detail": f"rev-list 滿 200 筆（{last[:12]}..{head[:12]}），"
                    "最舊段未檢視，本輪歷史偵測數據不完整",
                }
            )
        for sha in revs:
            subject = git("log", "-1", "--format=%s", sha).stdout.strip()
            # 夾帶偵測（置於下方 replies 零新增 continue 之前——事故形狀「建立
            # 交接夾帶 archive 新增」正是 replies 零新增的 commit）
            arch_out = git(
                "diff-tree",
                "-r",
                "--no-commit-id",
                "--diff-filter=A",
                "--name-only",
                sha,
                "--",
                *archive_prefixes,
            ).stdout
            arch_added = [
                p
                for p in arch_out.splitlines()
                if p.startswith(archive_prefixes) and p.endswith(".md")
            ]
            if arch_added and not subject.startswith(whitelist_prefixes):
                shown = "、".join(arch_added[:5]) + (
                    f"（另 {len(arch_added) - 5} 份）" if len(arch_added) > 5 else ""
                )
                warns.append(
                    f"HISTORY_WARN:MISDECLARED_ARCHIVE_ADD {sha[:12]} 非歸檔訊息的 "
                    f"commit 新增 {len(arch_added)} 份信箱 archive/ 檔案"
                    f"（{subject[:60]}）——commit 內容疑似超出訊息宣告範圍：{shown}"
                )
                events.append(
                    {
                        "ts": now,
                        "type": "MISDECLARED_ARCHIVE_ADD",
                        "detail": f"{sha[:12]} {subject}：{len(arch_added)} 份——"
                        + "、".join(arch_added),
                    }
                )
            name_out = git(
                "diff-tree",
                "-r",
                "--no-commit-id",
                "--diff-filter=A",
                "--name-only",
                sha,
                "--",
                replies_prefix,
            ).stdout
            added = [
                p
                for p in name_out.splitlines()
                if p.startswith(replies_prefix)
                and p.endswith(".md")
                and "/" not in p[len(replies_prefix):]
            ]
            if not added:
                continue
            if subject.startswith("docs: 歸檔"):
                shown = "、".join(added[:5]) + (
                    f"（另 {len(added) - 5} 份）" if len(added) > 5 else ""
                )
                warns.append(
                    f"HISTORY_WARN:SMUGGLED_REPLY {sha[:12]} 歸檔 commit 新增 "
                    f"{len(added)} 份頂層回覆（歸檔只該搬移；頂層新增＝未讀回覆被"
                    f"靜默轉為已處理）：{shown}"
                )
                events.append(
                    {
                        "ts": now,
                        "type": "SMUGGLED_REPLY",
                        "detail": f"{sha[:12]} {subject}：{len(added)} 份——"
                        + "、".join(added),
                    }
                )
            elif len(added) >= 6:
                warns.append(
                    f"HISTORY_WARN:BATCH_REPLY_ADD {sha[:12]} 單一 commit 新增 "
                    f"{len(added)} 份頂層回覆（{subject[:60]}）——請確認各份確已"
                    f"閱讀處理、非整批掃入"
                )
                events.append(
                    {
                        "ts": now,
                        "type": "BATCH_REPLY_ADD",
                        "detail": f"{sha[:12]} {subject}：{len(added)} 份",
                    }
                )

    ent["last_checked_commit"] = head
    ent["total_runs"] = int(ent.get("total_runs", 0) or 0) + 1
    if has_tripwire:
        ent["runs_with_tripwire"] = int(ent.get("runs_with_tripwire", 0) or 0) + 1
        events.append(
            {
                "ts": now,
                "type": "TRIPWIRE",
                "detail": tripwire_lines[:2000] or "exit 2（無明細行）",
            }
        )
    if warns:
        ent["runs_with_history_warn"] = (
            int(ent.get("runs_with_history_warn", 0) or 0) + 1
        )
    ent["events"] = events[-500:]

    # 自清：登記路徑已不存在的軍師條目移除（比照 stale 偵測精神，統計不留殭屍鍵）
    for stale in [p for p in list(kunsu_map) if not os.path.isdir(p)]:
        del kunsu_map[stale]

    os.makedirs(os.path.dirname(stats_path), exist_ok=True)
    tmp_path = stats_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    os.replace(tmp_path, stats_path)

    for line in warns:
        print(line)
except SystemExit:
    raise
except Exception as exc:  # fail-open：統計層任何失敗不得影響掃描
    print(f"ℹ 歷史夾帶偵測／統計未完成（fail-open 跳過）：{exc}", file=sys.stderr)
    sys.exit(0)
PYEOF
fi

if [[ "$HAS_TRIPWIRE" -eq 1 ]]; then
  exit 2
fi

exit 0
