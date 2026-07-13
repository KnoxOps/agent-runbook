# Loop Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite loop.py render() to produce orchestrator instructions where the main agent schedules body steps and dispatches independent sub-agents, instead of executing everything inline.

**Architecture:** Render-only change — loop.py generates dispatch instructions per body step type (script→Bash, inline→self, agent→Agent tool), appends a goal-check sub-agent prompt template, and adds iteration state management instructions. No new runtime modules.

**Tech Stack:** Python 3, Pydantic schema, pytest

**Spec:** `docs/superpowers/specs/2026-07-13-loop-orchestrator-design.md`

## Global Constraints

- Only modify rendering layer — no new Python runtime or executor modules
- Body step is full `Step` object; preserve all capabilities (input/output/parallel/quality_check/checkpoint/condition)
- Nested loops in body emit `logging.warning` and skip, don't block generation
- i18n covers 8 languages: en, zh, ja, ko, es, pt, fr, de, ru
- Goal-check sub-agent prompt is rendered in English (LLM-facing, not user-facing)
- Keep Chinese translation natural and professional

---

## File Structure

| File | Role |
|---|---|
| `agent_runbook/i18n.py` | New keys for orchestrator labels + updated loop control text |
| `agent_runbook/strategies/loop.py` | Rewritten render() → orchestrator dispatch instructions |
| `agent_runbook/tests/test_strategies/test_loop.py` | Updated assertions + new tests for dispatch output |

---

### Task 1: Add i18n keys for loop orchestrator

**Files:**
- Modify: `agent_runbook/i18n.py`

**Interfaces:**
- Produces: i18n keys consumed by `LoopStepStrategy.render()` in Task 2

Below each language's loop block, insert new keys AFTER the last existing `loop_*` key (before the closing `},`). Also update the text of existing keys `loop_done`, `loop_continue`, `loop_max_reached`.

- [ ] **Step 1: Add new keys to English block**

In `agent_runbook/i18n.py`, in the `"en"` dict, replace the existing loop keys block from `"loop_done"` through `"loop_iteration_history"` and append new keys. The complete English loop block becomes:

```python
"loop_header": "Iteration Loop",
"loop_goal_label": "Goal",
"loop_max_label": "Max Iterations",
"loop_intro": "This step executes as a loop. The body steps repeat until the goal is met or max iterations reached.",
"loop_body_header": "Loop Body (repeats each iteration)",
"loop_goal_check": "Goal Evaluation",
"loop_goal_check_desc": "After all body steps complete, evaluate:",
"loop_done": "If goal IS met → mark this step completed, proceed to next step.",
"loop_continue": "If goal NOT met and iterations remain → reset body steps, start next iteration.",
"loop_max_reached": "If max iterations reached → mark step completed with status \"max_iterations_reached\", report what remains.",
"loop_iteration_history": "Append a summary to `iteration_history` after each iteration.",
"loop_orchestrator_intro": "You are the loop scheduler. Execute the following loop:",
"loop_body_script_via_bash": "Execute via Bash:",
"loop_body_agent_dispatch": "Dispatch an independent sub-agent via Agent tool with the following prompt:",
"loop_body_inline_handle": "Handle this step yourself:",
"loop_after_each_header": "After Each Iteration",
"loop_goal_check_dispatch": "Dispatch a **goal-check sub-agent** with the following prompt:",
"loop_goal_check_schema": 'Return a JSON object: {"goal_met": true|false, "confidence": "high"|"medium"|"low", "summary": "...", "remaining": "...", "evidence": "..."}',
"loop_state_header": "State Management",
"loop_state_init": "Before first iteration: create/overwrite `iteration_history.json` with `{\"loop_step_id\": \"<id>\", \"goal\": \"<goal>\", \"max_iterations\": <N>, \"current_iteration\": 0, \"history\": []}`",
"loop_state_inject": "When dispatching body steps: inject the latest iteration summaries into sub-agent prompts as context",
"loop_state_append": "After goal-check: append the goal-check result to `iteration_history.json` history array",
"loop_state_keep": "After loop ends: keep `iteration_history.json` — downstream steps may read it",
"loop_goal_met_action": "If goal_met == true → mark this step completed, proceed to next step",
"loop_goal_not_met_action": "If goal_met == false and iterations remain → start next iteration",
"loop_max_reached_action": "If max iterations reached → mark step \"max_iterations_reached\", report remaining issues",
```

- [ ] **Step 2: Add Chinese (zh) translations**

In the `"zh"` dict, replace the loop block with:

```python
"loop_header": "迭代循环",
"loop_goal_label": "目标",
"loop_max_label": "最大迭代次数",
"loop_intro": "此步骤以循环方式执行。循环体步骤重复执行，直到目标达成或达到最大迭代次数。",
"loop_body_header": "循环体（每次迭代重复）",
"loop_goal_check": "目标评估",
"loop_goal_check_desc": "所有循环体步骤完成后，评估：",
"loop_done": "如果目标已达成 → 标记此步骤为已完成，继续下一步。",
"loop_continue": "如果目标未达成且迭代次数未用完 → 重置循环体步骤，开始下一次迭代。",
"loop_max_reached": "如果达到最大迭代次数 → 标记步骤为 \"max_iterations_reached\"，报告未完成的内容。",
"loop_iteration_history": "每次迭代后追加摘要到 `iteration_history`。",
"loop_orchestrator_intro": "你是循环调度器。按以下规则执行循环：",
"loop_body_script_via_bash": "通过 Bash 执行：",
"loop_body_agent_dispatch": "通过 Agent tool 分派独立子 agent，prompt 如下：",
"loop_body_inline_handle": "你自己处理此步骤：",
"loop_after_each_header": "每次迭代后",
"loop_goal_check_dispatch": "分派一个 **goal-check 子 agent**，prompt 如下：",
"loop_goal_check_schema": '返回 JSON 对象：{"goal_met": true|false, "confidence": "high"|"medium"|"low", "summary": "...", "remaining": "...", "evidence": "..."}',
"loop_state_header": "状态管理",
"loop_state_init": "首次迭代前：创建/覆盖 `iteration_history.json`，内容为 `{\"loop_step_id\": \"<id>\", \"goal\": \"<goal>\", \"max_iterations\": <N>, \"current_iteration\": 0, \"history\": []}`",
"loop_state_inject": "分派 body step 时：将之前迭代的摘要注入子 agent 的 prompt 作为上下文",
"loop_state_append": "goal-check 完成后：将 goal-check 结果追加到 `iteration_history.json` 的 history 数组",
"loop_state_keep": "循环结束后：保留 `iteration_history.json` — 后续步骤可能会读取",
"loop_goal_met_action": "如果 goal_met == true → 标记此步骤为已完成，继续下一步",
"loop_goal_not_met_action": "如果 goal_met == false 且迭代次数未用完 → 开始下一次迭代",
"loop_max_reached_action": "如果达到最大迭代次数 → 标记步骤为 \"max_iterations_reached\"，报告剩余问题",
```

- [ ] **Step 3: Add Japanese (ja) translations**

```python
"loop_header": "反復ループ",
"loop_goal_label": "目標",
"loop_max_label": "最大反復回数",
"loop_intro": "このステップはループとして実行されます。目標が達成されるか最大反復回数に達するまで、本体ステップが繰り返されます。",
"loop_body_header": "ループ本体（各反復で繰り返し）",
"loop_goal_check": "目標評価",
"loop_goal_check_desc": "すべての本体ステップ完了後、評価：",
"loop_done": "目標が達成された場合 → このステップを完了とし、次のステップに進む。",
"loop_continue": "目標が未達成で反復回数が残っている場合 → 本体ステップをリセットし、次の反復を開始。",
"loop_max_reached": "最大反復回数に達した場合 → ステップを \"max_iterations_reached\" として完了とし、残りを報告。",
"loop_iteration_history": "各反復後に `iteration_history` にサマリーを追加。",
"loop_orchestrator_intro": "あなたはループスケジューラです。以下のループを実行してください：",
"loop_body_script_via_bash": "Bashで実行：",
"loop_body_agent_dispatch": "Agent toolで独立サブエージェントをディスパッチ、プロンプト：",
"loop_body_inline_handle": "このステップを自身で処理：",
"loop_after_each_header": "各反復後",
"loop_goal_check_dispatch": "**goal-checkサブエージェント**をディスパッチ、プロンプト：",
"loop_goal_check_schema": 'JSONオブジェクトを返す：{"goal_met": true|false, "confidence": "high"|"medium"|"low", "summary": "...", "remaining": "...", "evidence": "..."}',
"loop_state_header": "状態管理",
"loop_state_init": "初回反復前：`iteration_history.json` を作成/上書き、内容は `{\"loop_step_id\": \"<id>\", \"goal\": \"<goal>\", \"max_iterations\": <N>, \"current_iteration\": 0, \"history\": []}`",
"loop_state_inject": "ボディステップディスパッチ時：前回までの反復サマリーをサブエージェントのプロンプトにコンテキストとして注入",
"loop_state_append": "goal-check後：goal-check結果を `iteration_history.json` のhistory配列に追加",
"loop_state_keep": "ループ終了後：`iteration_history.json` を保持 — 後続ステップが読み取る可能性あり",
"loop_goal_met_action": "goal_met == true の場合 → このステップを完了とし、次のステップに進む",
"loop_goal_not_met_action": "goal_met == false かつ反復回数が残っている場合 → 次の反復を開始",
"loop_max_reached_action": "最大反復回数に達した場合 → ステップを \"max_iterations_reached\" とし、残りの問題を報告",
```

- [ ] **Step 4: Add Korean (ko) translations**

```python
"loop_header": "반복 루프",
"loop_goal_label": "목표",
"loop_max_label": "최대 반복 횟수",
"loop_intro": "이 단계는 루프로 실행됩니다. 목표가 달성되거나 최대 반복 횟수에 도달할 때까지 본문 단계가 반복됩니다.",
"loop_body_header": "루프 본문 (각 반복마다 실행)",
"loop_goal_check": "목표 평가",
"loop_goal_check_desc": "모든 본문 단계 완료 후 평가:",
"loop_done": "목표가 달성된 경우 → 이 단계를 완료로 표시하고 다음 단계로 진행.",
"loop_continue": "목표가 미달성이고 반복 횟수가 남아있는 경우 → 본문 단계를 리셋하고 다음 반복 시작.",
"loop_max_reached": "최대 반복 횟수에 도달한 경우 → 단계를 \"max_iterations_reached\"로 완료 표시하고 남은 내용 보고.",
"loop_iteration_history": "각 반복 후 `iteration_history`에 요약 추가.",
"loop_orchestrator_intro": "당신은 루프 스케줄러입니다. 다음 루프를 실행하세요:",
"loop_body_script_via_bash": "Bash로 실행:",
"loop_body_agent_dispatch": "Agent tool로 독립 서브 에이전트 디스패치, 프롬프트:",
"loop_body_inline_handle": "이 단계를 직접 처리:",
"loop_after_each_header": "각 반복 후",
"loop_goal_check_dispatch": "**goal-check 서브 에이전트** 디스패치, 프롬프트:",
"loop_goal_check_schema": 'JSON 객체 반환: {"goal_met": true|false, "confidence": "high"|"medium"|"low", "summary": "...", "remaining": "...", "evidence": "..."}',
"loop_state_header": "상태 관리",
"loop_state_init": "첫 반복 전: `iteration_history.json` 생성/덮어쓰기, 내용 `{\"loop_step_id\": \"<id>\", \"goal\": \"<goal>\", \"max_iterations\": <N>, \"current_iteration\": 0, \"history\": []}`",
"loop_state_inject": "바디 단계 디스패치 시: 이전 반복 요약을 서브 에이전트 프롬프트에 컨텍스트로 주입",
"loop_state_append": "goal-check 후: goal-check 결과를 `iteration_history.json` history 배열에 추가",
"loop_state_keep": "루프 종료 후: `iteration_history.json` 유지 — 후속 단계에서 읽을 수 있음",
"loop_goal_met_action": "goal_met == true → 이 단계를 완료로 표시, 다음 단계로 진행",
"loop_goal_not_met_action": "goal_met == false이고 반복 횟수가 남아있는 경우 → 다음 반복 시작",
"loop_max_reached_action": "최대 반복 횟수 도달 → 단계를 \"max_iterations_reached\"로 표시, 남은 문제 보고",
```

- [ ] **Step 5: Add remaining 4 languages (es, pt, fr, de, ru)**

```python
# Spanish (es)
"loop_header": "Bucle Iterativo",
"loop_goal_label": "Objetivo",
"loop_max_label": "Iteraciones Máximas",
"loop_intro": "Este paso se ejecuta como un bucle. Los pasos del cuerpo se repiten hasta que se alcance el objetivo o el máximo de iteraciones.",
"loop_body_header": "Cuerpo del Bucle (se repite cada iteración)",
"loop_goal_check": "Evaluación del Objetivo",
"loop_goal_check_desc": "Después de completar todos los pasos del cuerpo, evaluar:",
"loop_done": "Si el objetivo SE cumple → marcar este paso como completado, proceder al siguiente paso.",
"loop_continue": "Si el objetivo NO se cumple y quedan iteraciones → reiniciar pasos del cuerpo, iniciar siguiente iteración.",
"loop_max_reached": "Si se alcanza el máximo de iteraciones → marcar paso como \"max_iterations_reached\", reportar lo pendiente.",
"loop_iteration_history": "Agregar un resumen a `iteration_history` después de cada iteración.",
"loop_orchestrator_intro": "Eres el programador del bucle. Ejecuta el siguiente bucle:",
"loop_body_script_via_bash": "Ejecutar vía Bash:",
"loop_body_agent_dispatch": "Despachar un sub-agente independiente vía Agent tool con el prompt:",
"loop_body_inline_handle": "Maneja este paso tú mismo:",
"loop_after_each_header": "Después de Cada Iteración",
"loop_goal_check_dispatch": "Despachar un **sub-agente goal-check** con el siguiente prompt:",
"loop_goal_check_schema": 'Devuelve un objeto JSON: {"goal_met": true|false, "confidence": "high"|"medium"|"low", "summary": "...", "remaining": "...", "evidence": "..."}',
"loop_state_header": "Gestión de Estado",
"loop_state_init": "Antes de la primera iteración: crea/sobrescribe `iteration_history.json` con `{\"loop_step_id\": \"<id>\", \"goal\": \"<goal>\", \"max_iterations\": <N>, \"current_iteration\": 0, \"history\": []}`",
"loop_state_inject": "Al despachar pasos del cuerpo: inyecta los resúmenes de iteraciones anteriores en el prompt del sub-agente como contexto",
"loop_state_append": "Después del goal-check: añade el resultado a `iteration_history.json`",
"loop_state_keep": "Después del bucle: conserva `iteration_history.json` — pasos posteriores pueden leerlo",
"loop_goal_met_action": "Si goal_met == true → marcar completado, continuar al siguiente paso",
"loop_goal_not_met_action": "Si goal_met == false y quedan iteraciones → iniciar siguiente iteración",
"loop_max_reached_action": "Si máximo de iteraciones alcanzado → marcar \"max_iterations_reached\", reportar problemas restantes",

# Portuguese (pt)
"loop_header": "Loop Iterativo",
"loop_goal_label": "Objetivo",
"loop_max_label": "Iterações Máximas",
"loop_intro": "Esta etapa é executada como um loop. As etapas do corpo se repetem até que o objetivo seja atingido ou o máximo de iterações seja alcançado.",
"loop_body_header": "Corpo do Loop (repete a cada iteração)",
"loop_goal_check": "Avaliação do Objetivo",
"loop_goal_check_desc": "Após completar todas as etapas do corpo, avaliar:",
"loop_done": "Se o objetivo FOI atingido → marcar esta etapa como concluída, prosseguir para a próxima etapa.",
"loop_continue": "Se o objetivo NÃO foi atingido e restam iterações → reiniciar etapas do corpo, iniciar próxima iteração.",
"loop_max_reached": "Se o máximo de iterações foi atingido → marcar etapa como \"max_iterations_reached\", reportar o que resta.",
"loop_iteration_history": "Adicionar um resumo ao `iteration_history` após cada iteração.",
"loop_orchestrator_intro": "Você é o agendador do loop. Execute o seguinte loop:",
"loop_body_script_via_bash": "Executar via Bash:",
"loop_body_agent_dispatch": "Despachar um sub-agente independente via Agent tool com o prompt:",
"loop_body_inline_handle": "Resolva este passo você mesmo:",
"loop_after_each_header": "Após Cada Iteração",
"loop_goal_check_dispatch": "Despachar um **sub-agente goal-check** com o prompt:",
"loop_goal_check_schema": 'Retorne um objeto JSON: {"goal_met": true|false, "confidence": "high"|"medium"|"low", "summary": "...", "remaining": "...", "evidence": "..."}',
"loop_state_header": "Gestão de Estado",
"loop_state_init": "Antes da primeira iteração: criar/sobrescrever `iteration_history.json` com `{\"loop_step_id\": \"<id>\", \"goal\": \"<goal>\", \"max_iterations\": <N>, \"current_iteration\": 0, \"history\": []}`",
"loop_state_inject": "Ao despachar etapas do corpo: injetar resumos de iterações anteriores no prompt do sub-agente como contexto",
"loop_state_append": "Após goal-check: anexar o resultado ao array history de `iteration_history.json`",
"loop_state_keep": "Após o loop: manter `iteration_history.json` — etapas posteriores podem lê-lo",
"loop_goal_met_action": "Se goal_met == true → marcar concluído, prosseguir para a próxima etapa",
"loop_goal_not_met_action": "Se goal_met == false e iterações restantes → iniciar próxima iteração",
"loop_max_reached_action": "Se máximo de iterações atingido → marcar \"max_iterations_reached\", relatar problemas restantes",

# French (fr)
"loop_header": "Boucle Itérative",
"loop_goal_label": "Objectif",
"loop_max_label": "Itérations Maximum",
"loop_intro": "Cette étape s'exécute en boucle. Les étapes du corps se répètent jusqu'à ce que l'objectif soit atteint ou que le maximum d'itérations soit atteint.",
"loop_body_header": "Corps de la Boucle (répété à chaque itération)",
"loop_goal_check": "Évaluation de l'Objectif",
"loop_goal_check_desc": "Après l'achèvement de toutes les étapes du corps, évaluer :",
"loop_done": "Si l'objectif EST atteint → marquer cette étape comme terminée, passer à l'étape suivante.",
"loop_continue": "Si l'objectif N'EST PAS atteint et qu'il reste des itérations → réinitialiser les étapes du corps, commencer l'itération suivante.",
"loop_max_reached": "Si le maximum d'itérations est atteint → marquer l'étape comme \"max_iterations_reached\", signaler ce qui reste.",
"loop_iteration_history": "Ajouter un résumé à `iteration_history` après chaque itération.",
"loop_orchestrator_intro": "Vous êtes le planificateur de boucle. Exécutez la boucle suivante :",
"loop_body_script_via_bash": "Exécuter via Bash :",
"loop_body_agent_dispatch": "Dépêcher un sous-agent indépendant via Agent tool avec le prompt :",
"loop_body_inline_handle": "Gérez cette étape vous-même :",
"loop_after_each_header": "Après Chaque Itération",
"loop_goal_check_dispatch": "Dépêcher un **sous-agent goal-check** avec le prompt :",
"loop_goal_check_schema": 'Retourner un objet JSON : {"goal_met": true|false, "confidence": "high"|"medium"|"low", "summary": "...", "remaining": "...", "evidence": "..."}',
"loop_state_header": "Gestion d'État",
"loop_state_init": "Avant la première itération : créer/écraser `iteration_history.json` avec `{\"loop_step_id\": \"<id>\", \"goal\": \"<goal>\", \"max_iterations\": <N>, \"current_iteration\": 0, \"history\": []}`",
"loop_state_inject": "Lors du dispatch des étapes du corps : injecter les résumés des itérations précédentes dans le prompt du sous-agent",
"loop_state_append": "Après goal-check : ajouter le résultat au tableau history de `iteration_history.json`",
"loop_state_keep": "Après la boucle : conserver `iteration_history.json` — les étapes suivantes peuvent le lire",
"loop_goal_met_action": "Si goal_met == true → marquer comme terminé, passer à l'étape suivante",
"loop_goal_not_met_action": "Si goal_met == false et itérations restantes → commencer l'itération suivante",
"loop_max_reached_action": "Si max itérations atteint → marquer \"max_iterations_reached\", signaler les problèmes restants",

# German (de)
"loop_header": "Iterationsschleife",
"loop_goal_label": "Ziel",
"loop_max_label": "Maximale Iterationen",
"loop_intro": "Dieser Schritt wird als Schleife ausgeführt. Die Körperschritte wiederholen sich, bis das Ziel erreicht ist oder die maximale Iterationszahl erreicht wird.",
"loop_body_header": "Schleifenkörper (wiederholt sich jede Iteration)",
"loop_goal_check": "Zielbewertung",
"loop_goal_check_desc": "Nach Abschluss aller Körperschritte bewerten:",
"loop_done": "Wenn das Ziel erreicht IST → diesen Schritt als abgeschlossen markieren, zum nächsten Schritt übergehen.",
"loop_continue": "Wenn das Ziel NICHT erreicht ist und Iterationen verbleiben → Körperschritte zurücksetzen, nächste Iteration starten.",
"loop_max_reached": "Wenn maximale Iterationen erreicht → Schritt als \"max_iterations_reached\" markieren, verbleibende Probleme melden.",
"loop_iteration_history": "Nach jeder Iteration eine Zusammenfassung zu `iteration_history` hinzufügen.",
"loop_orchestrator_intro": "Sie sind der Schleifen-Scheduler. Führen Sie die folgende Schleife aus:",
"loop_body_script_via_bash": "Ausführen via Bash:",
"loop_body_agent_dispatch": "Unabhängigen Sub-Agent per Agent tool dispatchen mit Prompt:",
"loop_body_inline_handle": "Diesen Schritt selbst bearbeiten:",
"loop_after_each_header": "Nach Jeder Iteration",
"loop_goal_check_dispatch": "Einen **goal-check Sub-Agent** dispatchen mit folgendem Prompt:",
"loop_goal_check_schema": 'JSON-Objekt zurückgeben: {"goal_met": true|false, "confidence": "high"|"medium"|"low", "summary": "...", "remaining": "...", "evidence": "..."}',
"loop_state_header": "Zustandsverwaltung",
"loop_state_init": "Vor der ersten Iteration: `iteration_history.json` erstellen/überschreiben mit `{\"loop_step_id\": \"<id>\", \"goal\": \"<goal>\", \"max_iterations\": <N>, \"current_iteration\": 0, \"history\": []}`",
"loop_state_inject": "Beim Dispatch von Körperschritten: Zusammenfassungen vorheriger Iterationen als Kontext in Sub-Agent-Prompts einfügen",
"loop_state_append": "Nach goal-check: Ergebnis an `iteration_history.json` history-Array anhängen",
"loop_state_keep": "Nach Schleifenende: `iteration_history.json` behalten — nachfolgende Schritte können es lesen",
"loop_goal_met_action": "Wenn goal_met == true → als abgeschlossen markieren, zum nächsten Schritt",
"loop_goal_not_met_action": "Wenn goal_met == false und Iterationen übrig → nächste Iteration starten",
"loop_max_reached_action": "Wenn max Iterationen erreicht → als \"max_iterations_reached\" markieren, verbleibende Probleme melden",

# Russian (ru)
"loop_header": "Итерационный Цикл",
"loop_goal_label": "Цель",
"loop_max_label": "Максимум Итераций",
"loop_intro": "Этот шаг выполняется как цикл. Шаги тела повторяются до достижения цели или максимального числа итераций.",
"loop_body_header": "Тело Цикла (повторяется каждую итерацию)",
"loop_goal_check": "Оценка Цели",
"loop_goal_check_desc": "После завершения всех шагов тела, оценить:",
"loop_done": "Если цель достигнута → отметить этот шаг как завершённый, перейти к следующему шагу.",
"loop_continue": "Если цель НЕ достигнута и итерации остались → сбросить шаги тела, начать следующую итерацию.",
"loop_max_reached": "Если достигнуто максимальное число итераций → отметить шаг как \"max_iterations_reached\", сообщить о нерешённом.",
"loop_iteration_history": "Добавлять сводку в `iteration_history` после каждой итерации.",
"loop_orchestrator_intro": "Вы планировщик цикла. Выполните следующий цикл:",
"loop_body_script_via_bash": "Выполнить через Bash:",
"loop_body_agent_dispatch": "Отправить независимого под-агента через Agent tool с промптом:",
"loop_body_inline_handle": "Обработайте этот шаг самостоятельно:",
"loop_after_each_header": "После Каждой Итерации",
"loop_goal_check_dispatch": "Отправить **goal-check под-агента** со следующим промптом:",
"loop_goal_check_schema": 'Вернуть JSON-объект: {"goal_met": true|false, "confidence": "high"|"medium"|"low", "summary": "...", "remaining": "...", "evidence": "..."}',
"loop_state_header": "Управление Состоянием",
"loop_state_init": "Перед первой итерацией: создать/перезаписать `iteration_history.json` с `{\"loop_step_id\": \"<id>\", \"goal\": \"<goal>\", \"max_iterations\": <N>, \"current_iteration\": 0, \"history\": []}`",
"loop_state_inject": "При отправке шагов тела: внедрять сводки предыдущих итераций в промпты под-агентов как контекст",
"loop_state_append": "После goal-check: добавить результат в массив history файла `iteration_history.json`",
"loop_state_keep": "После завершения цикла: сохранить `iteration_history.json` — последующие шаги могут его читать",
"loop_goal_met_action": "Если goal_met == true → отметить как завершённый, перейти к следующему шагу",
"loop_goal_not_met_action": "Если goal_met == false и есть оставшиеся итерации → начать следующую итерацию",
"loop_max_reached_action": "Если достигнут максимум итераций → отметить \"max_iterations_reached\", сообщить об оставшихся проблемах",
```

- [ ] **Step 6: Verify i18n syntax**

```bash
cd /Users/hzp/github/agent-runbook && python3 -c "from agent_runbook.i18n import t; print(t('loop_orchestrator_intro', 'en')); print(t('loop_orchestrator_intro', 'zh'))"
```

Expected: prints English and Chinese versions of the orchestrator intro text.

- [ ] **Step 7: Commit**

```bash
git add agent_runbook/i18n.py
git commit -m "feat(i18n): add loop orchestrator translation keys for 8 languages

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: Rewrite loop.py render() as orchestrator

**Files:**
- Modify: `agent_runbook/strategies/loop.py`

**Interfaces:**
- Consumes: i18n keys from Task 1, `Step` model from `schema.py`, `topological_sort` from `dag.py`, `RenderContext` from `context.py`
- Produces: `render(step, ctx) -> str` — orchestrator markdown output

- [ ] **Step 1: Write the new loop.py**

Replace entire file content:

```python
"""Strategy for rendering loop steps as orchestrator dispatch instructions."""

from __future__ import annotations

import logging

from agent_runbook.context import RenderContext
from agent_runbook.dag import topological_sort
from agent_runbook.i18n import t
from agent_runbook.schema import Step, StepType
from agent_runbook.strategies.base import StepStrategy

logger = logging.getLogger(__name__)


class LoopStepStrategy(StepStrategy):
    """Strategy for rendering loop steps as orchestrator instructions.

    The main agent acts as scheduler: it iterates over body steps
    and dispatches each one according to its type (script→Bash,
    inline→self, agent→Agent tool). A goal-check sub-agent is
    dispatched after each iteration to evaluate the loop goal.
    """

    def render(self, step: Step, ctx: RenderContext) -> str:
        """Render a loop step as orchestrator dispatch instructions."""
        lang = ctx.lang
        parts: list[str] = []

        # Header metadata
        parts.append(self._render_header(step, ctx))

        # Orchestrator intro
        parts.append(self._render_orchestrator_intro(step, lang))

        # Body steps dispatch
        parts.append(self._render_body_dispatch(step, ctx))

        # After each iteration
        parts.append(self._render_post_iteration(step, ctx))

        # State management
        parts.append(self._render_state_management(step, lang))

        # Progress tracking
        parts.append(self._render_progress_tracking(step, lang))

        return "\n\n".join(parts)

    # -- Section renderers --

    def _render_orchestrator_intro(self, step: Step, lang: str) -> str:
        """Render the orchestrator role and loop config."""
        lines = [
            "## Loop Orchestrator",
            "",
            t("loop_orchestrator_intro", lang),
            "",
            "### Loop Config",
            "",
            f"**{t('loop_goal_label', lang)}:** {step.goal}",
            f"**{t('loop_max_label', lang)}:** {step.max_iterations}",
        ]
        return "\n".join(lines)

    def _render_body_dispatch(self, step: Step, ctx: RenderContext) -> str:
        """Render body steps as dispatch instructions, sorted by depends_on."""
        lang = ctx.lang
        lines: list[str] = []

        if not step.body:
            return ""

        body_sorted = topological_sort(step.body)

        lines.append("### Body Steps")
        lines.append("")
        lines.append(
            "Execute the following steps in order each iteration. "
            "Steps with the same dependencies may run in parallel."
        )
        lines.append("")

        for i, body_step in enumerate(body_sorted, 1):
            lines.append(
                f"#### Body Step {i}: {body_step.id} ({body_step.type.value})"
            )
            lines.append("")
            if body_step.description:
                lines.append(f"**{t('description_label', lang)}** {body_step.description}")
                lines.append("")

            # Input files
            lines.append(self._render_body_step_input(body_step, lang))

            # Type-specific dispatch
            lines.append(self._render_body_step_dispatch(body_step, lang))

            # Output
            lines.append(self._render_body_step_output(body_step, lang))

            # Quality check (for agent steps)
            if body_step.quality_check:
                lines.append(self._render_body_step_quality_check(body_step, lang))

            # Parallel note
            if body_step.parallel and body_step.parallel.enabled:
                lines.append(
                    f"> **{t('note_label', lang)}:** "
                    f"This step may run in parallel with up to "
                    f"{body_step.parallel.max_instances} instances."
                )
                lines.append("")

            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def _render_body_step_input(self, step: Step, lang: str) -> str:
        """Render input files for a body step."""
        if not step.input:
            return ""
        lines = [f"**{t('input_files', lang)}**"]
        for input_ref in step.input:
            if input_ref.file:
                lines.append(f"- `{input_ref.file}`")
            elif input_ref.schema:
                lines.append(f"- schema: {input_ref.schema}")
        lines.append("")
        return "\n".join(lines)

    def _render_body_step_dispatch(self, step: Step, lang: str) -> str:
        """Render dispatch instruction based on step type."""
        if step.type == StepType.SCRIPT:
            lines = [f"**{t('loop_body_script_via_bash', lang)}**", ""]
            if step.command:
                lines.append(f"```bash\n{step.command}\n```")
            lines.append("")
            return "\n".join(lines)

        elif step.type == StepType.AGENT:
            lines = [f"**{t('loop_body_agent_dispatch', lang)}**", ""]
            if step.prompt_file:
                lines.append(f"Prompt file: `{step.prompt_file}`")
            elif step.prompt:
                lines.append(step.prompt)
            lines.append("")
            return "\n".join(lines)

        elif step.type == StepType.INLINE:
            lines = [f"**{t('loop_body_inline_handle', lang)}**", ""]
            if step.prompt_file:
                lines.append(f"Follow instructions in: `{step.prompt_file}`")
            elif step.prompt:
                lines.append(step.prompt)
            lines.append("")
            return "\n".join(lines)

        elif step.type == StepType.LOOP:
            logger.warning(
                f"Nested loop in body step '{step.id}' is not supported — skipping."
            )
            return f"> Nested loop not supported — skipping step '{step.id}'.\n\n"

        return ""

    def _render_body_step_output(self, step: Step, lang: str) -> str:
        """Render output files for a body step."""
        if not step.output:
            return ""
        lines = [f"**{t('output_files', lang)}**"]
        for output_def in step.output:
            lines.append(f"- `{output_def.file}` (schema: {output_def.schema})")
        lines.append("")
        return "\n".join(lines)

    def _render_body_step_quality_check(self, step: Step, lang: str) -> str:
        """Render quality check as inline gate for a body step."""
        qc = step.quality_check
        if qc is None:
            return ""
        lines = [f"**Quality Check ({t('quality_check_blocking', lang) if qc.blocking else t('quality_check_non_blocking', lang)}):**"]
        if qc.review_prompt:
            lines.append(qc.review_prompt)
        if qc.rules:
            for rule in qc.rules:
                lines.append(f"- {rule}")
        if qc.blocking:
            lines.append("")
            lines.append(f"> Do NOT proceed past this body step until quality check passes.")
        lines.append("")
        return "\n".join(lines)

    def _render_post_iteration(self, step: Step, ctx: RenderContext) -> str:
        """Render the post-iteration goal-check and loop control rules."""
        lang = ctx.lang
        lines = [
            f"### {t('loop_after_each_header', lang)}",
            "",
            t("loop_goal_check_dispatch", lang),
            "",
            self._render_goal_check_prompt(step, ctx),
            "",
            "**Loop control:**",
            "",
            f"1. {t('loop_goal_met_action', lang)}",
            f"2. {t('loop_goal_not_met_action', lang)}",
            f"3. {t('loop_max_reached_action', lang)}",
            "",
            t("loop_iteration_history", lang),
        ]
        return "\n".join(lines)

    def _render_goal_check_prompt(self, step: Step, ctx: RenderContext) -> str:
        """Render the goal-check sub-agent prompt template."""
        lang = ctx.lang

        # Collect evidence files from body step outputs
        evidence_lines: list[str] = []
        if step.body:
            for body_step in topological_sort(step.body):
                if body_step.output:
                    for out in body_step.output:
                        evidence_lines.append(
                            f"- Read `{out.file}` (schema: `{out.schema}`)"
                        )

        evidence = "\n".join(evidence_lines) if evidence_lines else "- Review all output files from body steps"

        return f"""```
You are a goal evaluator. Determine if the loop goal has been met.

**Goal:** {step.goal}

**Evidence files:**
{evidence}

**Instructions:**
1. Read the evidence files
2. Check if the goal condition is definitively satisfied
3. Return a structured verdict:

{t('loop_goal_check_schema', lang)}

**Rules:**
- Only conclude goal_met: true when the condition is definitively satisfied
- Be specific in summary — mention counts, file names, error types
```"""

    def _render_state_management(self, step: Step, lang: str) -> str:
        """Render iteration_history.json state management instructions."""
        return f"""### {t('loop_state_header', lang)}

**iteration_history.json** — maintain this file throughout the loop:

1. {t('loop_state_init', lang)}
2. {t('loop_state_inject', lang)}
3. {t('loop_state_append', lang)}
4. {t('loop_state_keep', lang)}"""

    def _render_execution(self, step: Step, ctx: RenderContext) -> str:
        """Not used — render() is overridden."""
        return ""
```

- [ ] **Step 2: Verify syntax and import**

```bash
cd /Users/hzp/github/agent-runbook && python3 -c "from agent_runbook.strategies.loop import LoopStepStrategy; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Quick smoke test — render with English**

```bash
cd /Users/hzp/github/agent-runbook && python3 -c "
from agent_runbook.strategies.loop import LoopStepStrategy
from agent_runbook.context import RenderContext
from agent_runbook.schema import Step, StepType

step = Step(
    id='fix_loop', type=StepType.LOOP,
    goal='all tests pass', max_iterations=3, depends_on=[],
    body=[
        Step(id='run', type=StepType.SCRIPT, command='pytest', depends_on=[]),
        Step(id='fix', type=StepType.AGENT, prompt='Fix bugs', depends_on=['run']),
    ]
)
ctx = RenderContext(runbook=None, execution_order=[], branch_groups={}, runbook_dir='/tmp')
out = LoopStepStrategy().render(step, ctx)
print(out[:500])
assert 'Loop Orchestrator' in out
assert 'pytest' in out
assert 'Fix bugs' in out
assert 'goal-check' in out.lower()
assert 'iteration_history.json' in out
print('--- SMOKE PASS ---')
"
```

Expected: `--- SMOKE PASS ---`

- [ ] **Step 4: Commit**

```bash
git add agent_runbook/strategies/loop.py
git commit -m "feat(loop): rewrite render as orchestrator dispatch instructions

Replace inline loop execution doc with scheduler-oriented output:
- Body steps rendered as type-specific dispatch (script→Bash, agent→Agent, inline→self)
- Goal-check sub-agent prompt generated per iteration
- iteration_history.json state management instructions added
- Nested loops emit warning and skip

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: Update loop tests

**Files:**
- Modify: `agent_runbook/tests/test_strategies/test_loop.py`

- [ ] **Step 1: Rewrite test file**

Replace entire file content:

```python
"""Tests for LoopStepStrategy orchestrator rendering."""

from __future__ import annotations

import pytest
from agent_runbook.context import RenderContext
from agent_runbook.schema import Step, StepType, QualityCheckConfig


class TestLoopOrchestratorRender:
    """Tests for LoopStepStrategy orchestrator output."""

    def _make_ctx(self, lang: str = "en") -> RenderContext:
        return RenderContext(
            runbook=None,
            execution_order=[],
            branch_groups={},
            runbook_dir="/test",
            lang=lang,
        )

    def _make_loop_step(self) -> Step:
        return Step(
            id="fix_loop",
            type=StepType.LOOP,
            description="Fix all lint errors",
            goal="ESLint passes with zero errors on all files",
            max_iterations=10,
            depends_on=["setup"],
            body=[
                Step(
                    id="discover",
                    type=StepType.INLINE,
                    prompt="Run eslint, write errors to eslint_output.json",
                    output=[{"schema": "schemas/eslint.schema.json", "file": "eslint_output.json"}],
                    depends_on=[],
                ),
                Step(
                    id="fix",
                    type=StepType.AGENT,
                    prompt="Pick a batch of errors and fix them",
                    depends_on=["discover"],
                    quality_check=QualityCheckConfig(
                        blocking=True,
                        rules=["Only src/ files modified", "No test files changed"],
                    ),
                ),
                Step(
                    id="verify",
                    type=StepType.SCRIPT,
                    command="eslint src/ --format json",
                    depends_on=["fix"],
                    output=[{"schema": "schemas/eslint.schema.json", "file": "eslint_output.json"}],
                ),
            ],
        )

    # -- Existing test coverage (updated) --

    def test_render_includes_goal(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        output = strategy.render(self._make_loop_step(), self._make_ctx())
        assert "ESLint passes with zero errors on all files" in output

    def test_render_includes_max_iterations(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        output = strategy.render(self._make_loop_step(), self._make_ctx())
        assert "10" in output

    def test_render_includes_body_step_ids(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        output = strategy.render(self._make_loop_step(), self._make_ctx())
        assert "discover" in output
        assert "fix" in output
        assert "verify" in output

    def test_render_includes_body_prompts(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        output = strategy.render(self._make_loop_step(), self._make_ctx())
        assert "Run eslint, write errors to eslint_output.json" in output
        assert "Pick a batch of errors and fix them" in output

    def test_render_has_orchestrator_structure(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        output = strategy.render(self._make_loop_step(), self._make_ctx())
        assert "Loop Orchestrator" in output
        assert "Loop Config" in output
        assert "Body Steps" in output
        assert "After Each Iteration" in output
        assert "State Management" in output

    # -- New tests for dispatch instructions --

    def test_script_step_has_bash_dispatch(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        output = strategy.render(self._make_loop_step(), self._make_ctx())
        assert "eslint src/ --format json" in output

    def test_agent_step_has_dispatch_instruction(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        output = strategy.render(self._make_loop_step(), self._make_ctx())
        assert "Agent tool" in output

    def test_inline_step_has_handle_instruction(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        output = strategy.render(self._make_loop_step(), self._make_ctx())
        assert "Run eslint" in output

    def test_goal_check_prompt_includes_evidence_files(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        output = strategy.render(self._make_loop_step(), self._make_ctx())
        assert "eslint_output.json" in output

    def test_goal_check_prompt_includes_schema(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        output = strategy.render(self._make_loop_step(), self._make_ctx())
        assert "goal_met" in output
        assert "goal-check" in output.lower()

    def test_quality_check_in_body_step(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        output = strategy.render(self._make_loop_step(), self._make_ctx())
        assert "Only src/ files modified" in output
        assert "No test files changed" in output

    def test_state_management_in_output(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        output = strategy.render(self._make_loop_step(), self._make_ctx())
        assert "iteration_history.json" in output

    # -- Chinese translation --

    def test_render_zh_has_translated_labels(self):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        step = self._make_loop_step()
        ctx = self._make_ctx(lang="zh")

        output = strategy.render(step, ctx)
        # Goal is user-provided, stays as-is
        assert "ESLint passes with zero errors on all files" in output
        # Chinese translations should appear for labels
        assert "目标" in output
        assert "最大迭代次数" in output
        assert "状态管理" in output
        assert "每次迭代后" in output

    # -- Nested loop warning --

    def test_nested_loop_emits_warning(self, caplog):
        from agent_runbook.strategies.loop import LoopStepStrategy

        strategy = LoopStepStrategy()
        step = Step(
            id="outer",
            type=StepType.LOOP,
            goal="done",
            max_iterations=3,
            depends_on=[],
            body=[
                Step(
                    id="inner",
                    type=StepType.LOOP,
                    goal="inner done",
                    max_iterations=2,
                    depends_on=[],
                    body=[
                        Step(id="s", type=StepType.INLINE, prompt="x", depends_on=[]),
                    ],
                ),
            ],
        )
        ctx = self._make_ctx()

        import logging
        with caplog.at_level(logging.WARNING):
            output = strategy.render(step, ctx)

        assert "Nested loop" in output
        assert "inner" in output
```

- [ ] **Step 2: Run tests**

```bash
cd /Users/hzp/github/agent-runbook && python3 -m pytest agent_runbook/tests/test_strategies/test_loop.py -v
```

Expected: all 13 tests PASS.

- [ ] **Step 3: Run full test suite**

```bash
cd /Users/hzp/github/agent-runbook && python3 -m pytest agent_runbook/tests/ -v
```

Expected: all tests PASS (no regressions).

- [ ] **Step 4: Commit**

```bash
git add agent_runbook/tests/test_strategies/test_loop.py
git commit -m "test(loop): update tests for orchestrator dispatch output

- Update assertions for new orchestrator structure
- Add tests for type-specific dispatch (script/agent/inline)
- Add tests for goal-check prompt generation
- Add test for quality_check in body steps
- Add test for state management instructions
- Add test for nested loop warning
- Update Chinese translation test

Co-Authored-By: Claude <noreply@anthropic.com>"
```
