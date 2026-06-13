# SkillOpt and KamaClaude

This note explains what Microsoft SkillOpt is, how it can fit KamaClaude, and where to put the generated skill files.

## What SkillOpt Is

SkillOpt is an offline optimizer for agent skills. It treats a skill document as trainable state while keeping the base agent model frozen.

Its core loop is:

```text
rollout -> reflect -> aggregate -> select -> update -> evaluate
```

In practice, SkillOpt runs tasks, inspects failures and successes, proposes bounded edits to a skill document, evaluates the edited skill, and keeps the version that improves validation performance. The output is usually a compact skill file such as `best_skill.md`.

SkillOpt also describes a deployment-time companion called SkillOpt-Sleep:

```text
harvest transcripts -> mine recurring tasks -> replay offline -> consolidate -> gate -> stage proposal -> user adopt
```

That means it can learn from real session traces, but the generated skill should still be reviewed before adoption.

## How It Maps To KamaClaude

KamaClaude already has a skill runtime. A KamaClaude skill is a prompt/template artifact loaded by the SkillLoader and invoked through slash commands in CLI, TUI, or Web UI.

SkillOpt should not be placed inside the normal KamaClaude runtime path. It is better used as an offline tool that produces improved skill markdown. KamaClaude then imports or copies that markdown into its own skill directories.

Recommended placement:

```text
.kama/skills/<skill-name>.md             project-local skill
.kama/skills/<skill-name>/SKILL.md       project-local skill folder
~/.kama/skills/<skill-name>.md           global user skill
```

Example flow:

```bash
# 1. Run SkillOpt outside KamaClaude against your task/eval set.
skillopt ...

# 2. Review its generated best skill.
# Example output path depends on your SkillOpt run config.

# 3. Copy or adapt the generated markdown into KamaClaude.
mkdir -p .kama/skills
cp path/to/best_skill.md .kama/skills/refactor-review.md

# 4. Use it from KamaClaude.
uv run kama chat
# then type: /refactor-review src/kama_claude/core/app.py
```

## Runtime Logic In KamaClaude

When a skill is used in KamaClaude, the flow is:

```text
CLI/TUI/Web user input
  -> slash command parsing
  -> SkillLoader reads .kama/skills and ~/.kama/skills
  -> skill prompt is expanded with user arguments
  -> AgentRunner builds the run context and ToolRegistry
  -> AgentLoop sends prompt to the model
  -> model may call allowed tools
  -> permission layer gates local side effects
  -> events stream back to CLI/TUI/Web
```

The skill document is therefore not executable code by itself. It shapes model behavior and may declare or imply which tools the agent should use.

## What It Can Bring

SkillOpt can help when a task repeats often and a hand-written skill is too vague. Good examples are code review, migration planning, bug triage, release-note generation, test-writing policy, or project-specific refactor workflows.

It can produce a more compact and empirically tested skill prompt, reduce repeated instruction text, and standardize how KamaClaude handles recurring work.

## Risks And Tradeoffs

SkillOpt is an optimization loop, so it needs task data, evaluation design, API budget, and time. A weak validation set can make a skill overfit or encode bad habits.

Generated skills may ask for tools that your KamaClaude configuration does not allow. Review `allowed_tools` or tool instructions before using the skill in a real project.

Long generated skills consume context. Prefer compact skills and keep examples small.

SkillOpt's own runtime dependencies may be heavier than KamaClaude's runtime dependencies, especially on Termux. Keep SkillOpt outside the Android/Termux runtime path and only copy the final markdown skill into KamaClaude.

## Recommended Integration Plan

For now, use SkillOpt as an external offline optimizer. Do not vendor the full SkillOpt project into KamaClaude.

A future KamaClaude integration can add:

```text
uv run kama skill import path/to/best_skill.md
uv run kama skill list
uv run kama skill show <name>
uv run kama skill sleep --from-sessions --stage-proposal
```

The safe first step is manual import: generate `best_skill.md`, review it, place it in `.kama/skills/`, then invoke it with `/skill-name`.
