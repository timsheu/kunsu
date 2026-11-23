#!/usr/bin/env bash
# session-cost.sh — 分析一個 Claude Code session transcript 的 token 流向與等值費用
#
# 沉澱自 2026-10-10 ebook 軍師 session 成本評估（詳見 docs/history 同日條目）。
# 回答三個問題：主線程的費用花在哪（快取讀／寫／輸出）、工具回傳文字由哪些工具貢獻、
# 副官若改跑較低階模型能省多少。據此檢核範本「Context 成本紀律」四條有沒有被遵守。
#
# 用法：bash scripts/session-cost.sh <session.jsonl>
#   transcript 位於 ~/.claude/projects/<編碼後的專案路徑>/<session-id>.jsonl；
#   副官 transcript 於同名目錄下 subagents/agent-*.jsonl，存在時一併統計。
# 費用為 Claude API 牌價（2026-10）換算，訂閱制下額度消耗比例相同。
set -euo pipefail
[ $# -eq 1 ] && [ -f "$1" ] || { echo "用法：bash scripts/session-cost.sh <session.jsonl>" >&2; exit 1; }
python3 -I - "$1" <<'PY'
import collections, glob, json, os, sys

# 牌價：input / output / cache 寫入 / cache 讀取（USD per MTok）
PRICE = {"opus": (4, 20, 5, 0.20), "sonnet": (2, 10, 2.5, 0.20), "haiku": (0.10, 0.50, 0.125, 0.01)}
KEYS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def cost(u, tier):
    i, o, w, r = PRICE[tier]
    return (u["input_tokens"] * i + u["output_tokens"] * o + u["cache_creation_input_tokens"] * w + u["cache_read_input_tokens"] * r) / 1e6


def load(path):
    for line in open(path, encoding="utf-8", errors="ignore"):
        try:
            yield json.loads(line)
        except ValueError:
            continue


def analyze(path):
    usage = collections.Counter(); turns = 0; models = collections.Counter()
    id2name = {}; result_chars = collections.Counter(); agents = []
    counted = set()   # 同一次模型回應（同 message id）會依 content block 拆成多行寫入，每行都帶同一份 usage，只計一次
    for e in load(path):
        m = e.get("message") or {}; c = m.get("content")
        if e.get("type") == "assistant":
            mid = m.get("id") or id(m)
            if mid not in counted:
                counted.add(mid)
                turns += 1; models[m.get("model", "?")] += 1
                for k in KEYS:
                    usage[k] += (m.get("usage") or {}).get(k, 0) or 0
            for b in c or []:
                if b.get("type") == "tool_use":
                    id2name[b["id"]] = b["name"]
                    if b["name"] == "Agent":
                        i = b.get("input", {}); agents.append((i.get("subagent_type"), i.get("model"), (i.get("description") or "")[:36]))
        elif e.get("type") == "user" and isinstance(c, list):
            for b in c:
                if b.get("type") == "tool_result":
                    rc = b.get("content")
                    s = rc if isinstance(rc, str) else "".join(x.get("text", "") for x in (rc or []) if isinstance(x, dict))
                    result_chars[id2name.get(b.get("tool_use_id"), "?")] += len(s)
    return usage, turns, models, result_chars, agents


main = sys.argv[1]
u, turns, models, result_chars, agents = analyze(main)
print(f"主線程：{turns} 回合，模型 {dict(models)}")
print(f"  cache 讀取 {u['cache_read_input_tokens']:>12,} tok  ≈ 每回合重讀 {u['cache_read_input_tokens'] // max(turns, 1):,} tok")
print(f"  cache 寫入 {u['cache_creation_input_tokens']:>12,} tok")
print(f"  輸出       {u['output_tokens']:>12,} tok")
tier = next((t for t in PRICE if t in "".join(models)), "opus")
main_cost = cost(u, tier)
print(f"  等值費用（{tier}）${main_cost:.2f}：cache 讀 ${u['cache_read_input_tokens'] * PRICE[tier][3] / 1e6:.2f}、cache 寫 ${u['cache_creation_input_tokens'] * PRICE[tier][2] / 1e6:.2f}、輸出 ${u['output_tokens'] * PRICE[tier][1] / 1e6:.2f}")
tot = sum(result_chars.values()) or 1
print(f"工具回傳文字 {tot:,} 字元：")
for name, n in result_chars.most_common(6):
    print(f"  {name:<16} {n:>9,} ({n * 100 // tot}%)")

sub_dir = os.path.join(os.path.splitext(main)[0], "subagents")
subs = sorted(glob.glob(os.path.join(sub_dir, "agent-*.jsonl")))
if subs:
    total = collections.Counter(); sub_models = collections.Counter()
    for p in subs:
        su, _, sm, _, _ = analyze(p)
        total.update(su); sub_models.update(sm)
    sub_cost = cost(total, tier)
    print(f"副官：{len(subs)} 個，模型 {dict(sub_models)}")
    print(f"  等值費用 opus ${cost(total, 'opus'):.2f} ／ sonnet ${cost(total, 'sonnet'):.2f} ／ haiku ${cost(total, 'haiku'):.2f}")
    print(f"  副官佔整個 session：{sub_cost * 100 / (main_cost + sub_cost):.0f}%")
if agents:
    unset = sum(1 for a in agents if not a[1])
    print(f"Agent 派發 {len(agents)} 次，其中 {unset} 次未指定 model（可被路由器填入）")
PY
