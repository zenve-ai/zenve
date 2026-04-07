# commit

Claude Code skill for creating well-structured git commits using conventional commit format.

## Install

```bash
npx skills add ghalex/skills --skill commit
```

## Usage

```
/commit
```

## What it does

1. Runs `git status` and `git diff` to analyze all changes
2. Groups files into logical commits by topic (UI, Redux, docs, config, etc.)
3. Presents the grouping plan and **waits for your approval**
4. Creates commits sequentially using conventional commit format
5. Shows a final summary of all commits created

## Commit format

```
type(scope): description
```

Types: `feat`, `fix`, `refactor`, `docs`, `style`, `test`, `chore`

## Example output

```
Commit 1: feat(ui): add simple signup form
- src/components/custom/simple-signup-form.tsx

Commit 2: docs: update agent instructions
- .agents/redux-agent.md
- CLAUDE.md

Commit 3: chore: add lint:file script
- package.json

Proceed with these commits? (yes/no)
```

## Rules

- Never mixes unrelated files in one commit
- Always asks for confirmation before committing
- Never pushes unless explicitly asked
