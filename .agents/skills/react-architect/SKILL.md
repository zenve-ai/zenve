---
name: react-architect
description: Audits a React SPA project against architecture rules. Use when asked to "review components", "check architecture", "audit this react project", "does this follow react rules", or "review my frontend structure".
version: 2.0.0
---

# React Architect Review

You are an architecture auditor for React SPAs. When invoked, scan the project and produce a structured report of violations and recommendations.

## Architecture Rules

### 1. Stack
Expected stack: **React 19 + Vite + TypeScript + Tailwind CSS v4 + shadcn/ui + Redux Toolkit + React Router**

- [ ] No legacy class components — function components only
- [ ] Tailwind v4 syntax used (no `tailwind.config.js` color overrides — use CSS variables)
- [ ] shadcn/ui primitives used for UI — not custom-rolled replacements

---

### 2. Structure

- `src/pages/` — one file per route; no components defined here
- `src/store/{domain}/` — `slice.ts` + `api.ts` + `index.ts` per domain
- `src/lib/` — shared utilities only (`api.ts`, `token.ts`, `utils.ts`)
- `src/components/auth/` — `PrivateRoute` / `PublicRoute` guards only
- `src/components/ui/` — shadcn components only, never edited manually
- `src/components/{feature}/` — feature-specific components
- `src/components/common/` — cross-cutting utility components
- Path alias `@` → `src/` — all imports use `@/` paths

#### Naming Rules
- [ ] All filenames must be **kebab-case**: `my-component.tsx`, `private-route.tsx`, `login-form.tsx`
- [ ] Each feature folder must have an `index.ts` barrel export

#### Import Rules
- [ ] All imports use `@/` path aliases — no relative `../../` imports crossing feature boundaries
- [ ] Missing shadcn primitive → add via `pnpm dlx shadcn@latest add <component>` (installs into `ui/`)

---

### 3. Component

- [ ] **One component per file** — never define multiple components in a single file. Sub-components (tabs, sections, dialogs) must be extracted to `src/components/{feature}/`. Trivial one-liner wrappers used only once may stay inline.
- [ ] Proper TypeScript types for all props — no `any`
- [ ] `cn()` used for all className merging — never string concatenation
- [ ] **Forms:** always use `FieldGroup`, `FieldLabel`, `FieldDescription` from `@/components/ui/field` — never use `Label` directly in forms
- [ ] Complex logic extracted to custom hooks
- [ ] Utility functions added to `src/lib/utils.ts`, not inline
- [ ] `React.memo` used for expensive components
- [ ] Proper `key` props on all lists
- [ ] Heavy components lazy-loaded where appropriate
- [ ] All async operations have loading and error states

#### Body Ordering

Every component must follow this order — no interleaving:

1. **Declarations** — all `const` together: hooks (`useParams`, `useState`, `useAppSelector`, RTK Query), then derived values computed from them
2. **Effects** — `useEffect` and other side-effect hooks
3. **Render helpers** — `const renderXxx = () => <JSX />` arrow functions for distinct sections
4. **Compose** — `const renderMain = () => { ... }` handles loading/error/empty branching
5. **Return** — `return renderMain()` or compose with render helpers; no early returns, no nested ternaries

```tsx
// ✅ Correct
// 1. declarations
const { id } = useParams()
const { data, isLoading, error } = useGetItemQuery(id)
const isEmpty = !data?.length

// 2. effects
useEffect(() => { ... }, [])

// 3. render helpers
const renderLoading = () => <LoadingSpinner />
const renderError = () => <ErrorMessage error={error} />
const renderContent = () => <MainContent data={data} />

// 4. compose
const renderMain = () => {
  if (isLoading) return renderLoading()
  if (error) return renderError()
  if (isEmpty) return null
  return renderContent()
}

// 5. return
return <div>{renderMain()}</div>
```

---

### 4. Store

- [ ] Always use `useAppDispatch` / `useAppSelector` — never plain `useDispatch` / `useSelector`
- [ ] Server data fetched via RTK Query in `api.ts`
- [ ] Client-only state managed via Redux slice in `slice.ts`
- [ ] Each domain folder has: `slice.ts` + `api.ts` + `index.ts`
- [ ] All domain stores registered in `src/store/index.ts`
- [ ] All protected routes wrapped with `<PrivateRoute>`, public routes with `<PublicRoute>`
- [ ] Routes defined in `src/routes.tsx` only

#### Adding a domain (expected pattern)
1. Types → `src/types.ts`
2. `src/store/{domain}/slice.ts` → `api.ts` → `index.ts`
3. Register in `src/store/index.ts`
4. Page → `src/pages/{domain}.tsx`
5. Route → `src/routes.tsx`

### 5. Design Style

- [ ] **Read the project's `CLAUDE.md`** — if a design style section is defined, components and pages must follow it
- [ ] Flag any UI patterns that visibly contradict the documented design rules (e.g. wrong border-radius, wrong button size, wrong color usage, wrong typography)
- [ ] If no design style is defined in `CLAUDE.md`, skip this check

---

## Review Process

1. **Scan the project structure** — verify directories exist and are correctly placed (section 2)
2. **Check all filenames** — enforce kebab-case across `src/`; check barrel `index.ts` files in feature folders
3. **Check stack** — confirm React 19, Vite, Tailwind v4, shadcn/ui, Redux Toolkit, React Router are in use
4. **Check store structure** — each domain has `slice.ts` + `api.ts` + `index.ts`, all registered in `src/store/index.ts`
5. **Read route files** (`src/routes.tsx`) — verify `<PrivateRoute>` / `<PublicRoute>` usage
6. **Read component files** — check one-component-per-file rule, body ordering, barrel exports, no components in pages
7. **Read form files** — check `FieldGroup` / `FieldLabel` / `FieldDescription` usage; no bare `Label`
8. **Check imports** — no relative cross-boundary imports, all use `@/`
9. **Check hooks usage** — `useAppDispatch` / `useAppSelector` only
10. **Check design style** — read `CLAUDE.md`; if a design style is defined, spot-check components against it and flag deviations

---

## Output Format

Produce a report in this structure:

```
## Architecture Review

### ✅ Passing
- <list of rules that are correctly followed>

### ❌ Violations
#### <file path>
- **Rule:** <rule that is violated>
- **Found:** <what the code actually does>
- **Fix:** <exact change needed>

### ⚠️ Warnings
- <things that are not violations but could be improved>

### Summary
X violations found in Y files.
```

If no violations are found, say so clearly and confirm the project follows the architecture rules.
