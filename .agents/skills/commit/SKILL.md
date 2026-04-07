---
name: commit
description: "Use this skill when the user asks to commit code, create a commit, or save changes to git"
version: 1.0.0
---

You are about to create git commit(s). Follow these steps:

1. **Check git status**:
   - Run `git status` to see all unstaged and staged files
   - Show me what files have changed

2. **Review the changes**:
   - Run `git diff` to see the actual changes in all modified files
   - Analyze all changes to understand what was modified

3. **Group files by related changes**:
   - Analyze the changes and group files into logical commits
   - Grouping criteria:
     - Files that implement the same feature together
     - UI components in one commit, Redux changes in another
     - Documentation updates separate from code changes
     - Configuration files (package.json, .md files) grouped by purpose
     - Agent files (.agents/) grouped together if related
   - Examples:
     - Group 1: `simple-signup-form.tsx` (new UI component)
     - Group 2: `CLAUDE.md`, `redux-agent.md`, `ui-agent.md` (documentation)
     - Group 3: `package.json` (dependency or script changes)
     - Group 4: `store/users/api.ts`, `store/users/slice.ts`, `store/users/index.ts` (Redux module)

4. **Present the grouping plan**:
   - Show me the proposed groups and ask for confirmation
   - Format:
     ```
     Commit 1: feat(ui): add simple signup form
     - src/components/custom/simple-signup-form.tsx

     Commit 2: docs: add redux and ui agent instructions
     - .agents/redux-agent.md
     - .agents/ui-agent.md
     - CLAUDE.md

     Commit 3: chore: add lint:file script to package.json
     - package.json
     ```
   - Wait for my approval or adjustments

5. **Create commits sequentially**:
   For each approved group:
   - Run `git add <files>` for only the files in that group
   - Create a meaningful commit message following conventional commit format:
     - Format: `type(scope): description`
     - Types: feat, fix, refactor, docs, style, test, chore
     - Keep the first line under 72 characters
   - Run `git commit -m "message"` with the generated message
   - Run `git log -1` to confirm the commit

6. **Final summary**:
   - Run `git log -<n>` where n = number of commits created
   - Show me all commits that were created

**Conventional Commit Examples:**
- `feat(ui): add simple signup form with Field components`
- `feat(redux): add user preferences state management`
- `fix(auth): prevent duplicate loading states in slices`
- `docs: update CLAUDE.md with redux-agent instructions`
- `docs(agents): add ui-agent workflow documentation`
- `refactor(auth): improve token validation logic`
- `chore: add lint:file script to package.json`
- `style(ui): update button component spacing`

**Important Rules:**
- NEVER include unrelated files in the same commit
- ALWAYS ask for confirmation before creating commits
- DO NOT push to remote unless I explicitly ask you to
- If there's only one logical group, create a single commit
