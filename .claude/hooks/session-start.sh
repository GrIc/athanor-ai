#!/bin/bash
# .claude/hooks/session-start.sh
# Dynamic context injection — shows only what's relevant RIGHT NOW
set -euo pipefail

echo "⚗️  Athanor — Session Context"
echo "─────────────────────────────"

# 1. Git status
if git rev-parse --is-inside-work-tree &>/dev/null 2>&1; then
    BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")
    LAST_COMMIT=$(git log -1 --oneline 2>/dev/null || echo "no commits")
    DIRTY=$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')
    echo "📍 Branch: ${BRANCH} | Last: ${LAST_COMMIT}"
    if [ "$DIRTY" -gt 0 ]; then
        echo "⚠️  ${DIRTY} uncommitted change(s)"
    fi
else
    echo "📍 Not a git repo yet"
fi

# 2. Detect work context from current directory and recent files
CURRENT_DIR=$(basename "$PWD")
PARENT_DIR=$(basename "$(dirname "$PWD")")

case "$CURRENT_DIR" in
    "infra"|"modules"|"envs")
        echo ""
        echo "🏗️  Working on Terraform infrastructure"
        echo "   → Skill: Use /terraform for TF best practices"
        echo "   → docs/ARCHITECTURE.md for system design"
        if command -v terraform &>/dev/null; then
            echo "   → Terraform $(terraform version -json 2>/dev/null | grep -o '"terraform_version":"[^"]*"' | cut -d'"' -f4 || echo 'installed')"
        fi
        ;;
    "docker"|"pipelines")
        echo ""
        echo "🐳 Working on containers / OpenWebUI pipelines"
        echo "   → Skill: Use /cloud-run or /docker"
        echo "   → docs/OPENWEBUI.md for config reference"
        ;;
    "scripts")
        echo ""
        echo "🔧 Working on utility scripts"
        ;;
    ".github"|"workflows")
        echo ""
        echo "🚀 Working on CI/CD"
        echo "   → .github/workflows/ for existing pipelines"
        ;;
    "docs")
        echo ""
        echo "📚 Working on documentation"
        echo "   → docs/INDEX.md for doc navigation"
        ;;
esac

# Also check parent dir for monorepo-style navigation
case "$PARENT_DIR" in
    "modules")
        echo ""
        echo "🏗️  Inside a Terraform module: ${CURRENT_DIR}"
        echo "   → Skill: Use /terraform"
        ;;
    "pipelines")
        echo ""
        echo "🔌 Inside an OpenWebUI pipeline: ${CURRENT_DIR}"
        ;;
esac

# 3. Check for common issues
if [ -f "infra/main.tf" ]; then
    # Check if terraform is initialized
    if [ ! -d "infra/.terraform" ]; then
        echo ""
        echo "❌ Terraform not initialized → run: cd infra && terraform init"
    fi
fi

# 4. Show active phase from roadmap (if tracking file exists)
if [ -f ".claude/current-phase.txt" ]; then
    echo ""
    echo "📋 $(cat .claude/current-phase.txt)"
fi

echo "─────────────────────────────"