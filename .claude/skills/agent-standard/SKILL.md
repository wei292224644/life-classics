---
name: agent-standard
description: >-
  Designs and writes high-quality AI agents following standardized structure.
  Use when creating new agents, reviewing agent quality, or establishing
  agent design principles. Triggers on: "create agent", "design agent",
  "agent standard", "agent quality", "agent specification".
type: skill
version: "1.0"
triggers:
  - "create agent"
  - "design agent"
  - "agent standard"
  - "agent quality"
  - "agent specification"
  - "write agent"
  - "agent template"
boundary:
  cannot:
    - "不定义 agent 类型和职责就写内容"
    - "不写测试用例就提交"
    - "用泛泛的描述代替具体触发词"
  requires:
    - "需要知道 agent 的用途或已有需求"
---

# Agent Design Standard

This skill provides a comprehensive standard for designing and writing AI agents.

---

## What This Skill Does

Provides a complete framework for creating standardized AI agents with:
- Clear type definitions (Role vs Skill)
- Structured frontmatter specification
- Persona/Operations body separation
- Testing methodology
- Multi-agent collaboration patterns
- Quality checklists

---

## Quick Start

### Step 1: Determine Agent Type

| Type | Purpose | Trigger |
|------|---------|---------|
| **Role Agent** | Personality + workflow | Conversation |
| **Skill Agent** | Task capability | Keywords |

### Step 2: Write Frontmatter

```yaml
---
name: {prefix}:agent-name
description: >-  # Start with verb, include trigger scenarios
type: role | skill
version: "1.0"
boundary:
  cannot: [...]   # What NEVER to do
  requires: [...] # What is needed
---
```

### Step 3: Write Body

Role Agent → Persona (Identity) + Operations (Mission, Rules, Deliverables, Workflow)

Skill Agent → What, How, Output, Examples

### Step 4: Validate

Run `scripts/validate-agent.sh` to check format compliance.

---

## Directory Structure

```
{prefix}:agent-name/
├── SKILL.md                    # This file
├── scripts/
│   └── validate-agent.sh        # Validation script
├── references/
│   └── agent-examples.md        # Example agents
└── assets/
    └── agent-template.md        # Full templates
```

---

## Key Principles

### 1. Description Triggering

Description is the **only triggering mechanism**:

- [ ] Start with **verb** (Design, Build, Review...)
- [ ] Include **specific tech stack** (React, Python...)
- [ ] Explain **problem solved** (not "helpful", but "prevents X")
- [ ] List **trigger scenarios** ("Use when...")
- [ ] Avoid generic words (helpful, assistant, useful)

### 2. Persona / Operations Separation

| Group | Content | Purpose |
|-------|---------|---------|
| **Persona** | Identity, Memory, Communication | Who the agent is |
| **Operations** | Mission, Rules, Deliverables, Workflow | What the agent does |

### 3. Boundary Declaration

| Boundary | Purpose | Example |
|----------|---------|--------|
| `boundary.cannot` | Operational constraint | "不写 Python 代码" |
| `boundary.requires` | Activation constraint | "需要 existing codebase" |

---

## Validation Checklist

- [ ] `name` is `{prefix}:{name}` format
- [ ] `description` starts with verb, includes trigger scenarios
- [ ] `type` is `role` or `skill`
- [ ] `boundary.cannot` and `boundary.requires` are filled
- [ ] Body has Persona / Operations separation
- [ ] Deliverables have **runnable code** (not pseudo-code)
- [ ] Success Metrics are **quantifiable**
- [ ] At least 3 test cases in evals

---

## Scripts

### validate-agent.sh

Validates agent format compliance:

```bash
bash scripts/validate-agent.sh path/to/agent.md
```

Checks:
- Frontmatter has required fields
- Description starts with verb
- Boundary is defined
- Deliverables have code blocks
- Success Metrics are quantifiable

---

## References

See `references/agent-examples.md` for:
- Role Agent example
- Skill Agent example

See `assets/agent-template.md` for:
- Full Role Agent template
- Full Skill Agent template
- evals format
- Version evolution
- Changelog example

---

## Version

Current: **v1.0**

For version evolution rules, see `assets/agent-template.md`.
