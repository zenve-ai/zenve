# react-setup

Claude Code skill that scaffolds a complete, production-ready React 19 SPA.

## Stack

- **React 19** + **Vite 7** + **TypeScript**
- **Tailwind CSS v4** + **shadcn/ui** (new-york, neutral)
- **Redux Toolkit** + **RTK Query** (auth domain example)
- **React Router v7** with `PrivateRoute` / `PublicRoute` guards
- **Docker** + **nginx** production setup (port 4000)

## Install

```bash
npx skills add ghalex/skills --skill react-setup
```

## Usage

Just tell Claude:

> "create a new React project called myapp"
> "scaffold a react spa called dashboard"
> "new react frontend"

## What gets generated

```
myapp/
├── src/
│   ├── components/auth/   # PrivateRoute, PublicRoute
│   ├── lib/               # api.ts, token.ts, utils.ts
│   ├── pages/             # home.tsx, login.tsx
│   ├── store/auth/        # RTK Query + Redux slice
│   ├── app.tsx            # restoreFromStorage on init
│   ├── layout.tsx         # header + main + Toaster
│   ├── main.css           # Tailwind v4 + OKLCH theme
│   ├── routes.tsx         # React Router v7 routes
│   └── types.ts           # User, LoginData, SignupData
├── components.json        # shadcn config (new-york, neutral, lucide)
├── Dockerfile             # node:20-alpine → nginx:1.27-alpine
├── nginx.conf             # SPA routing, /healthz, port 4000
├── CLAUDE.md              # architecture rules
└── .env.example
```

## Commands after scaffolding

```bash
pnpm install
cp .env.example .env
pnpm dev                                    # http://localhost:5173/app

pnpm dlx shadcn@latest add sonner           # required for layout
pnpm dlx shadcn@latest add button card input label

docker compose up --build                   # production at :4000
```

## Architecture

- **Server data** → RTK Query (`store/{domain}/api.ts`)
- **Client state** → Redux slice (`store/{domain}/slice.ts`)
- **Typed hooks** → `useAppDispatch` / `useAppSelector` only
- **Route guards** → `<PrivateRoute>` / `<PublicRoute>`
- **Path alias** → `@` maps to `src/`
- **CLAUDE.md** → architecture rules loaded automatically on every session
