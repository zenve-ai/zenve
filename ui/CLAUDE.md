# CLAUDE.md

## Stack
React 19 + Vite + TypeScript + Tailwind CSS v4 + shadcn/ui + Redux Toolkit + React Router

## Structure
- `src/pages/` — one file per route
- `src/store/{domain}/` — `slice.ts` + `api.ts` + `index.ts` per domain
- `src/lib/` — shared utilities (api, token, utils)
- `src/components/auth/` — PrivateRoute / PublicRoute guards
- `src/components/ui/` — shadcn components (do not edit manually)

## Component placement rules
- Feature-specific component → `src/components/{feature}/` (e.g. `logs/`, `alerts/`, `sources/`)
- Cross-cutting utility component → `src/components/common/`
- Missing shadcn primitive → `pnpm dlx shadcn@latest add <component>` (installs into `ui/`)
- **All filenames use kebab-case** — no exceptions: `my-component.tsx`, `private-route.tsx`, `login-form.tsx`
- Each feature folder has an `index.ts` barrel — always export from it

## Rules
- Use `useAppDispatch` / `useAppSelector` — never plain hooks
- Server data → RTK Query (`api.ts`), client state → Redux slice (`slice.ts`)
- All protected routes use `<PrivateRoute>`, public routes use `<PublicRoute>`
- Path alias `@` → `src/`
- **Forms:** always use `FieldGroup`, `FieldLabel`, `FieldDescription` from `@/components/ui/field` — never use `Label` directly in forms

## Component body ordering
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

## Implementation Checklist
- All imports use `@/` path aliases
- Use `cn()` utility for className merging (from `@/lib/utils.ts`)
- **CRITICAL:** Use Field components for forms, NOT Label
- Proper TypeScript types for all props
- Use CSS variables: `hsl(var(--primary))`, `hsl(var(--background))`, etc.
- Follow Tailwind spacing conventions (`p-4`, `gap-2`, etc.)
- Implement loading states for async operations
- Handle error states gracefully
- Make responsive using Tailwind breakpoints (`sm:`, `md:`, `lg:`)
- Extract complex logic to custom hooks
- Add utility functions to `src/lib/utils.ts`, not inline

## Design Style — Industrial Control Panel

The Zenve UI uses an **industrial control panel / operator dashboard** aesthetic. When building new pages or components, follow this direction:

- **Status indicators** — colored left-edge bars (`w-[3px]`) on cards, monospace all-caps labels (`LIVE`, `HOLD`, `ERR`, `OFF`) with pulsing dots
- **Dividers** — dashed borders (`border-dashed border-border/60`) to separate card sections; pipe `|` separators in meta strips
- **Typography** — `font-mono` for metadata, slugs, timestamps, and status labels; small tight tracking (`tracking-widest`) on status badges
- **Density** — compact padding (`px-3 py-1.5`, `py-2`), small text sizes (`text-[10px]`–`text-[13px]`), high information density
- **Toolbars** — ghost button rows at card bottoms with `bg-muted/30`, `rounded-none`, hairline dividers between actions
- **Color** — semantic status colors only (emerald = active, amber = paused, red = error, muted = off); no decorative color fills
- **Tone** — utilitarian, no-nonsense; feels like a network operations terminal or industrial SCADA interface
- **Button size** — all action buttons across pages use `size="xs" className="rounded-none"`; never mix `xs` and `sm` in the same UI context
- **No rounded corners** — all cards, panels, and buttons use sharp edges (`rounded-none`); never use `rounded-md` or any border-radius on structural elements

## Adding a domain
1. Types → `src/types.ts`
2. `src/store/{domain}/slice.ts` → `api.ts` → `index.ts`
3. Register in `src/store/index.ts`
4. Page → `src/pages/{domain}.tsx`
5. Route → `src/routes.tsx`
