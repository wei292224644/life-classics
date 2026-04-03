#!/usr/bin/env bash
#
# validate-agent.sh — Validates agent markdown files against the standard.
#
# Usage: bash scripts/validate-agent.sh path/to/agent.md
#
# Exits 0 if valid, 1 if errors found.

set -euo pipefail

ERRORS=0
WARNINGS=0

check_file() {
    local file="$1"

    echo "Validating: $file"

    # Check frontmatter exists
    if ! head -1 "$file" | grep -q "^---"; then
        echo "  ERROR: Missing frontmatter opening ---"
        ((ERRORS++))
        return
    fi

    # Extract frontmatter
    local frontmatter
    frontmatter=$(awk 'NR==1{next} /^---$/{exit} {print}' "$file")

    if [[ -z "$frontmatter" ]]; then
        echo "  ERROR: Empty or malformed frontmatter"
        ((ERRORS++))
        return
    fi

    # Check required fields
    local required_fields=("name" "description" "type" "version")
    for field in "${required_fields[@]}"; do
        if ! echo "$frontmatter" | grep -qE "^${field}:[[:space:]]*"; then
            echo "  ERROR: Missing required field: ${field}"
            ((ERRORS++))
        fi
    done

    # Check type is role or skill
    local agent_type
    agent_type=$(echo "$frontmatter" | grep "^type:" | sed 's/type:[[:space:]]*//')
    if [[ "$agent_type" != "role" && "$agent_type" != "skill" ]]; then
        echo "  ERROR: type must be 'role' or 'skill', got '$agent_type'"
        ((ERRORS++))
    fi

    # Check boundary exists
    if ! echo "$frontmatter" | grep -q "^boundary:"; then
        echo "  WARNING: Missing boundary section"
        ((WARNINGS++))
    fi

    # Check boundary.cannot and boundary.requires
    if echo "$frontmatter" | grep -q "^boundary:"; then
        if ! echo "$frontmatter" | grep -q "cannot:"; then
            echo "  WARNING: boundary.cannot not defined"
            ((WARNINGS++))
        fi
        if ! echo "$frontmatter" | grep -q "requires:"; then
            echo "  WARNING: boundary.requires not defined"
            ((WARNINGS++))
        fi
    fi

    # Extract body (after second ---)
    local body
    body=$(awk 'BEGIN{fm=0} /^---$/{fm++; next} fm>=2{print}' "$file")

    # Check description starts with verb
    local desc_line
    desc_line=$(echo "$frontmatter" | grep "^description:" | head -1)
    local first_word
    first_word=$(echo "$desc_line" | sed 's/description:[[:space:]]*//' | awk '{print $1}')
    local verbs=("Designs" "Builds" "Reviews" "Optimizes" "Creates" "Implements" "Specializes" "Develops")
    local is_verb=false
    for verb in "${verbs[@]}"; do
        if [[ "$first_word" == "$verb"* ]]; then
            is_verb=true
            break
        fi
    done
    if [[ "$is_verb" == false ]]; then
        echo "  WARNING: description should start with a verb (got: $first_word)"
        ((WARNINGS++))
    fi

    # Check for generic words
    local generic_words=("helpful" "assistant" "useful")
    for word in "${generic_words[@]}"; do
        if echo "$desc_line" | grep -qi "$word"; then
            echo "  WARNING: description contains generic word: $word"
            ((WARNINGS++))
        fi
    done

    # Check deliverables have code blocks
    if ! echo "$body" | grep -q '\`\`\`[a-z]*'; then
        echo "  WARNING: No code blocks found in deliverables"
        ((WARNINGS++))
    fi

    # Check Success Metrics are quantifiable
    if echo "$body" | grep -qi "success metrics"; then
        if echo "$body" | grep -A 10 "Success Metrics" | grep -qvE "(< [0-9]+| > [0-9]+|%|[0-9]+ |[0-9]+ms)"; then
            echo "  WARNING: Success Metrics should be quantifiable (use numbers, not 'fast', 'good')"
            ((WARNINGS++))
        fi
    fi

    echo "  Result: $ERRORS error(s), $WARNINGS warning(s)"
}

# Main
if [[ $# -eq 0 ]]; then
    echo "Usage: $0 path/to/agent.md [path/to/agent2.md ...]"
    exit 1
fi

for file in "$@"; do
    if [[ ! -f "$file" ]]; then
        echo "ERROR: File not found: $file"
        ((ERRORS++))
    else
        check_file "$file"
    fi
done

echo ""
if [[ $ERRORS -gt 0 ]]; then
    echo "FAILED: $ERRORS error(s) found"
    exit 1
elif [[ $WARNINGS -gt 0 ]]; then
    echo "PASSED with warnings: $WARNINGS warning(s)"
    exit 0
else
    echo "PASSED: No errors or warnings"
    exit 0
fi
