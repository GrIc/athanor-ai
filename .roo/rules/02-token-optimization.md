# Token Optimization Rules

## Output Efficiency
- Skip obvious explanations — assume senior DevSecOps engineer
- No "Let me explain..." or "Here's what I'll do..." — just do it
- For file edits: use diff-based editing, never rewrite entire files
- Batch related changes in a single response when possible
- When reading files for context: read only the relevant sections, not entire files

## Context Management
- Reference `docs/INDEX.md` for extended documentation — don't ask me to paste content
- For architecture questions → read `docs/ARCHITECTURE.md`
- For cost questions → read `docs/FINOPS.md`
- For security questions → read `docs/SECURITY.md`
- For OpenWebUI config → read `docs/OPENWEBUI.md`

## Scope Discipline
- Stay on task — don't expand scope beyond what was asked
- If a task is large, propose a phased plan and confirm before executing
- One concern per response — don't refactor unrelated code while fixing a bug
