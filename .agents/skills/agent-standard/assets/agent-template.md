# Agent Templates

Full templates for creating agents following the standard.

---

## Role Agent Template

```markdown
---
name: {prefix}:agent-name
description: >-
  [Verb] [specific function]. [Tech stack]. Use when [trigger scenarios].
  Not: generic "helpful", "assistant".
type: role
version: "1.0"
boundary:
  cannot:
    - [What NEVER to do]
    - [What NEVER to do]
  requires:
    - [What is needed to activate]
tools:
  - file:read
  - file:write
  # Add others as needed
---

# Agent Name

## 🧠 Identity & Memory
- **Role**: [Specific role, not "developer"]
- **Personality**: [3-5 adjectives]
- **Perspective**: [How this agent sees problems]
- **Memory**: [What to remember between sessions]
  - Note: Implementation varies by tool

## 🎯 Core Mission
1. **Primary 1** — [Specific deliverable with constraints]
2. **Primary 2** — [With success criteria]
3. **Primary 3** — [With measurable outcomes]
- **Default Mode**: [How work is done by default]

## 🚨 Critical Rules
Operational constraints (not duplicated in boundary):
1. **Rule 1** — [With reason]
2. **Rule 2** — [With reason]
3. **Quality threshold** — [Fail if below this]

## 📋 Deliverables
### [Deliverable Name]
```[language]
// Runnable code, not pseudo-code
// Include comments explaining key decisions
```

### Output Template
```output
# Exact format to produce
## Section 1
## Section 2
```

## 🔄 Workflow
### Phase 1: [Name]
1. [Step with checkpoint]
2. [Step]
### Phase 2: [Name]
...

## 💬 Communication Style
- **Start with**: [First sentence format]
- **When blocked**: [How to handle]
- **Escalation**: [When to escalate]

## 📊 Success Metrics
Quantifiable only:
- "[Metric] < [Number]" or "> [Number]"
- "[Metric] = [Exact value]"
NOT: "fast", "good", "as few as possible"

## 🔗 Handoff Protocols
- **To [Agent]**: Must include [what info]
- **From [Agent]**: Expects [what format]
```

---

## Skill Agent Template

```markdown
---
name: {prefix}:skill-name
description: >-
  [One sentence]. Use when: [triggers].
type: skill
version: "1.0"
triggers:
  - "trigger phrase 1"
  - "trigger phrase 2"
boundary:
  cannot:
    - [What this skill does NOT do]
  requires:
    - [What is needed to use this skill]
---

# Skill Name

## What This Skill Does
[One sentence describing the skill]

## How to Use
### Step 1: [Specific step]
[What to do and how]
### Step 2: [Specific step]
[What to do and how]

## Output Format
```output
[Exact template - every field specified]
```

## Boundaries
- **Only does**: [Scope]
- **Does not do**: [Explicit exclusions]

## Examples
### Example 1
**Input**: [User prompt]
**Output**: [Expected output]

### Example 2
**Input**: [Edge case prompt]
**Output**: [Expected graceful handling]
```

---

## evals Template

```yaml
# evals/{prefix}:agent-name.yaml
agent: {prefix}:agent-name
version: "1.0"

evals:
  - id: 1
    name: Basic functionality
    prompt: |-
      [Test prompt - should trigger the agent]
    expected:
      contains: ["specific keywords that should appear"]
      excludes: ["error indicators that should NOT appear"]

  - id: 2
    name: Boundary case
    prompt: |-
      [Test something boundary.cannot prohibits]
    expected:
      boundary_respected: true      # Agent did NOT do the prohibited thing
      error_handled: true           # Handled gracefully

  - id: 3
    name: Performance benchmark
    prompt: |-
      [Performance-related prompt]
    expected:
      response_time_ms: < [threshold]

  - id: 4
    name: Handoff test
    prompt: |-
      [Task requiring collaboration]
    expected:
      handoff_complete: true
      format_correct: true
```

---

## Version Evolution

### Change Rules

| Version Type | When | Example |
|-------------|------|---------|
| **Patch** 1.0 → 1.1 | Bug fixes, no behavior change | Fix typo in description |
| **Minor** 1.0 → 1.2 | New content, no breaking changes | Add new trigger |
| **Major** 1.0 → 2.0 | Breaking changes | Change type |

### Changelog Format

```markdown
## Changelog

### v1.1 (YYYY-MM-DD)
- [ADDED] boundary.requires field
- [FIXED] description trigger words inaccurate
- [IMPROVED] test coverage 2 → 5 cases

### v1.0 (YYYY-MM-DD)
- Initial release
```

### Deprecation

```markdown
---
name: {prefix}:old-agent
description: >-
  [DEPRECATED] Use {prefix}:new-agent instead.
  This agent will be removed in v2.0.
type: role
version: "1.1"
---
```

When deprecating:
1. Mark `[DEPRECATED]` at start of description
2. State replacement agent
3. Keep functional but discourage new use

---

## Naming Convention

```
{prefix}:{function}

Examples:
- frontend-developer
- code-reviewer
- react-performance
- api-design
```

| Part | Format | Purpose |
|------|--------|---------|
| `prefix` | `:{name}` | Product identifier |
| `function` | kebab-case | What the agent does |
