# CLAUDE.md

## 1. Stack
React 19 + Vite + TypeScript + Tailwind CSS v4 + shadcn/ui + Redux Toolkit + React Router

## 2. Structure
- `src/pages/` — one file per route
- `src/store/{domain}/` — `slice.ts` + `api.ts` + `index.ts` per domain
- `src/lib/` — shared utilities (api, token, utils)
- `src/components/auth/` — PrivateRoute / PublicRoute guards
- `src/components/ui/` — shadcn components (do not edit manually)
- `src/components/{feature}/` — feature-specific components (e.g. `agents/`, `logs/`, `alerts/`)
- `src/components/common/` — cross-cutting utility components
- **All filenames use kebab-case** — no exceptions: `my-component.tsx`, `private-route.tsx`, `login-form.tsx`
- Each feature folder has an `index.ts` barrel — always export from it
- Missing shadcn primitive → `pnpm dlx shadcn@latest add <component>` (installs into `ui/`)
- Path alias `@` → `src/` — all imports use `@/` paths

## 3. Component
- **One component per file** — never define multiple components in a single file. If a page needs sub-components (tabs, sections, dialogs, helper blocks), extract each into its own file under `src/components/{feature}/` and import it. Trivial one-liner wrappers used only once (e.g. a styled `<div>`) may stay inline.
- Proper TypeScript types for all props
- Use `cn()` for className merging (from `@/lib/utils.ts`)
- **Forms:** always use `FieldGroup`, `FieldLabel`, `FieldDescription` from `@/components/ui/field` — never use `Label` directly in forms
- Extract complex logic to custom hooks
- Add utility functions to `src/lib/utils.ts`, not inline
- Use `React.memo` for expensive components
- Implement proper `key` props for lists
- Lazy load heavy components when appropriate
- Minimize re-renders through proper state management

### Body ordering
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

## 4. Store
- Use `useAppDispatch` / `useAppSelector` — never plain hooks
- Server data → RTK Query (`api.ts`), client state → Redux slice (`slice.ts`)
- All protected routes use `<PrivateRoute>`, public routes use `<PublicRoute>`

### Adding a domain
1. Types → `src/types.ts`
2. `src/store/{domain}/slice.ts` → `api.ts` → `index.ts`
3. Register in `src/store/index.ts`
4. Page → `src/pages/{domain}.tsx`
5. Route → `src/routes.tsx`

## 5.Design Style (Industrial Control Panel)

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

## 6. Decorative Panel Pattern (Dark Hero / Auth / Onboarding)

Use this pattern for full-height decorative right-panels on split-layout pages (onboarding, auth, landing).

**Structure:**
```
bg-black relative overflow-hidden
  ├── grid line background (CSS background-image)
  ├── decorative SVG boxes with plus-sign corners (top-left, bottom-right)
  ├── radial vignette overlay
  └── centered content (z-10): badge → headline → description → cards
```

**Background grid:**
```tsx
<div className="absolute inset-0" style={{
  backgroundImage: `
    linear-gradient(to right, rgba(255,255,255,0.06) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(255,255,255,0.06) 1px, transparent 1px)
  `,
  backgroundSize: '48px 48px',
}} />
```

**Plus-corner SVG box** (reusable helper — keep inline in the file):
```tsx
const PlusCorner = ({ x, y }: { x: number; y: number }) => (
  <g transform={`translate(${x - 6}, ${y - 6})`}>
    <line x1="6" y1="2" x2="6" y2="10" stroke="rgba(255,255,255,0.5)" strokeWidth="1.5" />
    <line x1="2" y1="6" x2="10" y2="6" stroke="rgba(255,255,255,0.5)" strokeWidth="1.5" />
  </g>
)
// usage: one <svg> per box, positioned with absolute + top/bottom/left/right classes
<svg className="absolute top-8 left-8 pointer-events-none" width="140" height="80">
  <rect x="0" y="0" width="140" height="80" fill="none" stroke="rgba(255,255,255,0.12)" strokeWidth="1" />
  <PlusCorner x={0} y={0} /> <PlusCorner x={140} y={0} />
  <PlusCorner x={0} y={80} /> <PlusCorner x={140} y={80} />
</svg>
```

**Radial vignette:**
```tsx
<div className="absolute inset-0" style={{
  background: 'radial-gradient(ellipse at center, transparent 30%, rgba(0,0,0,0.55) 100%)',
}} />
```

**Content layer:**
- Badge: `border border-white/15 bg-white/5 px-3 py-1.5` with a small `rounded-full` status dot and `font-mono text-[10px] tracking-widest uppercase text-white/50`
- Headline: `text-3xl font-bold text-white` with gradient span: `bg-gradient-to-r from-white via-white/70 to-white/30 bg-clip-text text-transparent`
- Description: `font-mono text-[12px] text-white/35`
- Cards grid: `grid grid-cols-2 gap-2` — each card: `border border-white/10 bg-white/5 p-3` (no rounded corners) with icon in `bg-white/10 p-1.5` wrapper

**Rules:**
- Always `bg-black` — never inherit theme background
- No `rounded-*` anywhere — all sharp edges
- No framer-motion — Zenve does not use it
- Keep `PlusCorner` as a file-local SVG helper component, not exported
- Two decorative boxes minimum: one top-left, one bottom-right

## 7. Skills

Use these slash commands before starting related work:

- `/shadcn` — when adding, composing, or debugging shadcn/ui components
- `/frontend-design` — when building new pages, components, or polishing UI
- `/react-architect` — when reviewing component structure or auditing architecture
- `/simplify` — after finishing code changes, to review for reuse and quality
