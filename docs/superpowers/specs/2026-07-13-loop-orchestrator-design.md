# Loop Orchestrator — 调度与执行分离

**Date:** 2026-07-13
**Status:** design

---

## 问题

当前 `loop` step type 的渲染 (`loop.py`) 把整个循环逻辑（调度、执行、目标检查）渲染成一段 markdown 描述文档，全部塞进生成的 `SKILL.md` 里。当 SKILL.md 被执行时，**一个 Agent 在内部自己做循环**——它自己跑 body steps、自己判断 goal、自己决定是否继续迭代。

具体问题：

1. **调度和执行耦合** — loop 的迭代控制、goal 检查等编排逻辑，和每个 body step 的执行混在一个 Agent 里
2. **body step 的 `type: agent` 形同虚设** — YAML 里写了 `type: agent`，渲染到 SKILL.md 里只是一段文字描述，没有被真正 dispatch 为独立子 agent
3. **单点瓶颈** — 一个 Agent 的 context window 要装下所有迭代的历史和输出
4. **无法并行** — body 里有 `parallel` 配置的步骤也无法真正并行

## 目标

**调度与执行分离：**

```
主 Agent（调度层，SKILL.md 指导）
  │
  ├─ 按 depends_on 拓扑排序 body steps
  ├─ 遍历执行每个 body step:
  │     ├─ type: script  → 主 agent 用 Bash tool 执行
  │     ├─ type: inline  → 主 agent 自己处理
  │     └─ type: agent   → Agent tool dispatch 独立子 agent
  ├─ Body 完成后，dispatch goal-check 子 agent 评估目标
  ├─ 目标达成 → 退出循环；未达成 → 维护迭代状态，下一轮
  └─ 每轮注入迭代摘要给子 agent
```

**不改项目定位** — agent-runbook 仍然是 YAML → SKILL.md 编译器，改动仅在渲染层。

---

## 设计

### 1. loop.py `render()` 重写

从"描述 loop body 内容的文档"改为"指导主 agent 如何调度 body steps 的指令"。

#### 1.1 新输出结构

```markdown
## Loop Orchestrator

You are the loop scheduler. Execute the following loop:

### Loop Config
- **Goal:** <step.goal>
- **Max Iterations:** <step.max_iterations>

### Body Steps (execute in dependency order per iteration)

#### Body Step 1: <step.body[N].id> (<step.body[N].type>)
<!-- dispatch instruction varies by type, see 1.2 -->

#### Body Step 2: <step.body[N+1].id> (<step.body[N+1].type>)
...

### After Each Iteration

1. Dispatch a **goal-check sub-agent** (see prompt below)
2. If goal_met == true → mark loop complete, proceed to next step
3. If goal_met == false and iterations remain → append to iteration_history, next iteration
4. If max iterations reached → mark "max_iterations_reached"

### State Management
<!-- see section 3 -->
```

#### 1.2 Body Step 按类型 Dispatch

**`type: script`** — 主 agent 用 Bash tool：
```markdown
#### Body Step N: <id> (script)

**Description:** <step.description>

Execute via Bash:
<step.command>
```

**`type: inline`** — 主 agent 自己处理：
```markdown
#### Body Step N: <id> (inline)

**Description:** <step.description>

Handle this step yourself:
<step.prompt or step.prompt_file>
```

**`type: agent`** — dispatch 独立子 agent：
```markdown
#### Body Step N: <id> (agent)

**Description:** <step.description>

Dispatch an independent sub-agent via Agent tool with the following prompt:
<step.prompt or step.prompt_file>

<!-- if quality_check present, include inline: -->
#### Quality Check (blocking gate)
Dispatch a quality-check sub-agent with rules:
  - <qc.rules[0]>
  - <qc.rules[1]>
Do NOT proceed past this body step until quality check passes.
```

**`type: loop`** — body 内不支持嵌套 loop。如果 body step 的 type 是 `loop`，渲染时跳过并输出 warning 日志（`logging.warning`），不阻塞生成。未来可扩展支持。

#### 1.3 Body Step 的完整能力保留

Body step 是完整 `Step` 对象，所有能力在渲染时保留：

| 能力 | 处理方式 |
|---|---|
| `input` | 渲染为 Input Files 列表 |
| `output` | 渲染为 Output Files 列表 |
| `depends_on` | 用 `topological_sort` 排序 body steps |
| `parallel` | 检测到并行组时，渲染 `> Note: Step X and Step Y must run in parallel` 注解 |
| `checkpoint` | 渲染 checkpoint 指令 |
| `condition` | 渲染条件判断指令 |
| `quality_check` | 渲染为 body step 内联的 quality check 子 agent dispatch 指令 |

#### 1.4 移除的方法

- `_render_body_step()` — 不再需要将 body step 渲染为"文档描述"，取而代之的是按类型生成 dispatch 指令
- `_render_execution()` — loop 不再使用基类的执行渲染

---

### 2. Goal-Check 子 Agent

每次迭代结束后，主 agent dispatch 一个专用子 agent 评估目标。

#### 2.1 生成的 Prompt 模板

```markdown
## Goal Check

You are a goal evaluator. Determine if the loop goal has been met.

**Goal:** <step.goal>

**Evidence:**
<!-- 从 body steps 的 output 推导 -->
- Read `<output_def.file>` (schema: `<output_def.schema>`)

**Instructions:**
1. Read the evidence files
2. Check if the goal condition is definitively satisfied
3. Return a structured verdict:

```json
{
  "goal_met": true/false,
  "confidence": "high" | "medium" | "low",
  "summary": "1-2 sentence summary of what happened this iteration",
  "remaining": "What still needs to be done (if goal not met)",
  "evidence": "Key observations from output files"
}
```

**Rules:**
- Only conclude goal_met: true when the condition is definitively satisfied
- Be specific in summary — mention counts, file names, error types
```

#### 2.2 推导 Evidence Files

渲染时遍历 body steps，收集所有有 `output` 的步骤，提取 `file` 和 `schema` 引用。这些作为 goal-check 子 agent 的"需要读取的证据文件"列表。

---

### 3. 迭代状态管理

#### 3.1 `iteration_history.json` 格式

```json
{
  "loop_step_id": "fix_loop",
  "goal": "pytest exits with 0 failures",
  "max_iterations": 10,
  "current_iteration": 3,
  "history": [
    {
      "iteration": 1,
      "goal_met": false,
      "summary": "Fixed division by zero in calc.py. 5 tests still failing.",
      "files_changed": ["src/calc.py"]
    },
    {
      "iteration": 2,
      "goal_met": false,
      "summary": "Fixed off-by-one in validator.py. 2 tests still failing.",
      "files_changed": ["src/validator.py"]
    }
  ]
}
```

#### 3.2 SKILL.md 中的操作指令

```markdown
### State Management

**iteration_history.json** — maintain this file throughout the loop:

1. **Before first iteration:** Create/overwrite with empty history
2. **When dispatching body steps:** Inject the latest summary from previous iterations into the sub-agent's prompt as context
3. **After goal-check:** Append the goal-check result to history
4. **After loop ends:** Keep the file — downstream steps may read it
```

#### 3.3 子 Agent 上下文注入

```markdown
[Iteration 3 context]

Previous iterations:
- Iteration 1: Fixed division by zero in calc.py. 5 tests still failing.
- Iteration 2: Fixed off-by-one in validator.py. 2 tests still failing.

---

<original body step prompt>
```

---

### 4. i18n 新增 Key

在 `i18n.py` 的 `TRANSLATIONS` 中为 8 种语言新增以下 key：

| Key | 用途 |
|---|---|
| `loop_orchestrator` | "Loop Orchestrator" section heading |
| `loop_orchestrator_intro` | "You are the loop scheduler..." |
| `loop_config` | "Loop Config" subheading |
| `loop_body_dispatch_header` | "Body Steps (execute in dependency order per iteration)" |
| `loop_body_script_bash` | "Execute via Bash:" |
| `loop_body_agent_dispatch` | "Dispatch an independent sub-agent via Agent tool..." |
| `loop_body_inline_handle` | "Handle this step yourself:" |
| `loop_after_each_header` | "After Each Iteration" |
| `loop_goal_check_dispatch` | "Dispatch a goal-check sub-agent..." |
| `loop_goal_check_prompt_header` | "Goal Check" prompt header |
| `loop_state_header` | "State Management" |
| `loop_state_init` | "Before first iteration: Create/overwrite..." |
| `loop_state_inject` | "When dispatching body steps: Inject..." |
| `loop_state_append` | "After goal-check: Append..." |
| `loop_max_reached_label` | "max_iterations_reached" status text |

---

### 5. 文件变更

| 文件 | 改动 |
|---|---|
| `agent_runbook/strategies/loop.py` | 重写 `render()`，新增 `_render_body_step_dispatch()`、`_render_goal_check_prompt()`、`_render_state_management()`、`_render_loop_config()`。移除 `_render_body_step()` 和 `_render_execution()` |
| `agent_runbook/i18n.py` | 新增约 15 个 key，8 种语言 × 15 = 120 行翻译 |

**不需要改的文件：** `schema.py`、`generator.py`、`composer.py`、`dag.py`、其他 strategy 文件

---

### 6. 测试影响

`tests/test_strategies/test_loop.py` 中的测试需要更新断言：

- `test_render_includes_goal` — goal 仍然出现，通过
- `test_render_includes_max_iterations` — max_iterations 仍然出现，通过
- `test_render_includes_body_steps` — body step ID 仍然出现，通过
- `test_render_includes_loop_structure` — 需要更新关键字：新输出用 "orchestrator" 替代部分 "iteration" 相关词
- `test_render_includes_body_prompts` — prompt 内容仍然出现，通过
- `test_render_zh` — 需要更新断言为中文翻译后的关键字

可能需要新增测试：
- 验证 `script` 类型 body step 的 Bash dispatch 指令
- 验证 `agent` 类型 body step 的 Agent tool dispatch 指令
- 验证 goal-check prompt 包含 evidence files
- 验证 `quality_check` 在 body step 中渲染为内联门禁
