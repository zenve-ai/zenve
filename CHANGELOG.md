# Changelog
## [Unreleased]

### Documentation

- **cli**: Update README to reflect new features

## [0.1.2] - 2026-05-05

### Refactoring

- Comment old macs from release

## [0.1.1] - 2026-05-05

### Bug Fixes

- **server**: Add --package flag to uv run in justfile
- Server tests actions
- Defer settings instantiation to avoid import-time failure
- Give secret_key a default so tests don't require SECRET_KEY env var
- **db**: Switch default engine from SQLite to PostgreSQL
- Lint and type errors
- Small fixes
- Delete branch for artifact pr
- Code_pr on a pr to use same branch

### Chores

- Remove scratchpad architecture docs
- Add frontend-design and shadcn skills
- **example**: Switch run_claude_code to claude_code adapter
- Add .env.local and *.pem to gitignore

### Documentation

- Add custom agents usage instructions to CLAUDE.md
- Add agents dir as example
- **arch**: Design full agent file templates for chunk 03
- **arch**: Refine chunk 03 agent filesystem & templates
- **chunk-03**: Add bundled templates & bootstrap seeding design
- **arch**: Design agents CRUD chunk 04
- Document auth model and membership system
- Update CLAUDE.md files with component ordering rules
- **architect**: Remove TOOLS.md template, move tool permissions to gateway.json
- **architect**: Add run event system chunk and cross-references
- Update adapter arch docs to reflect context injection
- Add org-level git versioning design (chunk 16)
- Update architectural docs
- Update architecture docs to reflect implementation status
- Update chunk 15 to reflect SSE and asyncio executor
- Add chunk 17 org-websocket and update overview
- **ui**: Add decorative panel pattern to CLAUDE.md
- Update cli doc and architecture
- Update CLAUDE.md for cli

### Features

- **orgs**: Add organizations CRUD with API key authentication
- **filesystem**: Implement FilesystemService with bundled template seeding
- **agents**: Implement agents CRUD (chunk 04)
- **ui**: Organization slug routing, org switcher, and loading states
- Add ai agent skills
- **server**: Add user-org membership model, service, and DB table
- **server**: Switch org routes to JWT auth with membership checks
- **ui**: Connect org store to real API and fix route guards
- **server**: Switch agent routes from API-key to JWT auth
- **ui**: Add agents store, pages, and routing
- **adapters**: Setup pytest and add initial unit tests
- **api**: Update log config
- **server**: Add on_events to adapters
- **server**: Add presets for creating agents
- **server**: Opencode adapter
- **server**: Store run transcript in directories
- **run**: Add outcome field and signal-based status parsing
- **scaffolding**: Improve RUN/HEARTBEAT templates with outcome guidance
- **run**: Implement run event system with SSE streaming
- **ws**: Implement org-level WebSocket server-side
- **ws**: Implement org-level WebSocket frontend
- **ui**: Add agent detail page with dashboard tab and WS integration
- **server**: Add session id to resume session
- **ui**: Update agent details page
- **cli**: Create cli app
- **server**: Add redis url
- **ui**: Add onboarding process to create new project
- **server**: Add GitHub installation and repo listing endpoints
- **ui**: Improve GitHub onboarding with repo selection and session handling
- **server**: Remove scaffolding and use github as template repo
- **server**: Add project init endpoint and scaffolding utils
- **cli**: Add init command
- **ui**: Wire real templates and project init in onboarding
- **cli**: Update logo
- **cli**: New command and update agents
- **cli**: New console tui for events
- **cli**: Add tui for events when run
- **cli**: Add claims to run
- **cli**: Post comment with output
- **cli**: Add project desc to context
- **cli**: Update architecture.md file
- **cli**: Add worktree for agents
- **cli**: Add skill command
- **cli**: Add loading when showing events
- **cli**: Add git check before run
- **cli**: Add artifact pr for some agents
- **cli**: Add review_pr agent mode with RUN_CHANGES_REQUESTED support
- **cli**: Pr review flow complete
- **cli**: Add build pipeline for cli

### Refactoring

- Change repo to monorepo
- **server**: Move tool permissions from adapter config to RunContext
- User id from int to str
- Remove gateway.json from agents
- Directories
- **ui**: Agent page
- **ui**: Refactor agent details
- Cli to get redis url
- Refactor zenve cli
- **server**: Remove org
- **server**: Replace HTTPException with domain errors
- **cli**: Move console in a new package
- Remove plans dir
- Remove docs folder
- Move code to services

### Testing

- **adapters**: TDD tests for run event system (chunk 15)

### Style

- **server**: Remove extra blank line in example


