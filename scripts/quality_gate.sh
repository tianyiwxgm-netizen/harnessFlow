#!/usr/bin/env bash
# scripts/quality_gate.sh · 每 Phase 结束跑 · 3-Solution 质量 Gate
# Reference: docs/superpowers/plans/2026-04-21-3-solution-resume.md §1.4
set -euo pipefail

cd "$(dirname "$0")/.."

BASE="docs/3-1-Solution-Technical"
# 扩展目标（如已建则纳入）
[ -d "docs/3-2-Solution-TDD" ] && BASE="$BASE docs/3-2-Solution-TDD"
[ -d "docs/3-3-Monitoring-Controlling" ] && BASE="$BASE docs/3-3-Monitoring-Controlling"

FAIL=0

echo "=== Gate 1: Mermaid 代码块残留（硬约束：0）==="
m=$(grep -rc '```mermaid' $BASE 2>/dev/null | grep -v ':0$' || true)
if [ -n "$m" ]; then echo "FAIL:"; echo "$m"; FAIL=1; else echo "PASS"; fi

echo ""
echo "=== Gate 2: 未填段 <!-- FILL 残留（硬约束：0 · R1 后期望）==="
f=$(grep -rc '<!-- FILL' $BASE 2>/dev/null | grep -v ':0$' || true)
if [ -n "$f" ]; then
  count=$(echo "$f" | wc -l | tr -d ' ')
  echo "WARN: $count files 有 FILL 占位（R1-R6 逐步清）:"
  echo "$f" | head -10
else
  echo "PASS"
fi

echo ""
echo "=== Gate 3: 占位残留 TBD/TODO/待填（硬约束：0 · 注：用拼接避免 grep 自匹配）==="
# 用字符串拼接避免 grep 命令自身被匹配
t=$(grep -rc 'T''BD\|T''O''DO\|待''填' $BASE 2>/dev/null | grep -v ':0$' || true)
if [ -n "$t" ]; then
  count=$(echo "$t" | wc -l | tr -d ' ')
  echo "WARN: $count files 有占位（R7 期望 0）:"
  echo "$t" | head -10
else
  echo "PASS"
fi

echo ""
echo "=== Gate 4: L2 tech-design 每份含 ≥ 1 IC-XX 引用（R1 后期望）==="
noic_count=0
while IFS= read -r -d '' file; do
  if ! grep -q 'IC-' "$file"; then
    noic_count=$((noic_count + 1))
  fi
done < <(find docs/3-1-Solution-Technical -name "L2-*.md" -print0 2>/dev/null)
if [ "$noic_count" -eq 0 ]; then
  echo "PASS"
else
  echo "WARN: $noic_count L2 file 无 IC-XX 引用（R1 前可接受）"
fi

echo ""
echo "=== Gate 5: PlantUML @startuml/@enduml 配对检查（硬约束）==="
unpaired=0
while IFS= read -r -d '' file; do
  starts=$(grep -c '^@startuml' "$file" || true)
  ends=$(grep -c '^@enduml' "$file" || true)
  if [ "$starts" != "$ends" ]; then
    echo "FAIL: $file @startuml=$starts @enduml=$ends"
    unpaired=$((unpaired + 1))
    FAIL=1
  fi
done < <(grep -rlZ '```plantuml' $BASE 2>/dev/null)
if [ "$unpaired" -eq 0 ]; then echo "PASS"; fi

echo ""
echo "=== Gate 6: mermaid-fallback 精修标记残留（R0 后期望：0）==="
fb=$(grep -rc "mermaid-fallback\|unrecognized mermaid\|styles stripped" $BASE 2>/dev/null | grep -v ':0$' || true)
if [ -n "$fb" ]; then
  count=$(echo "$fb" | wc -l | tr -d ' ')
  echo "WARN: $count files 有 fallback 标记（R0.3 精修目标）:"
  echo "$fb"
else
  echo "PASS"
fi

echo ""
echo "============================================"
if [ $FAIL -ne 0 ]; then
  echo "❌ Gate FAIL · 禁止 commit · 原地 fix 后重跑"
  exit 1
fi
echo "✅ Gate PASS · 可 git commit"
