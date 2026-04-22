export interface MockAgent {
  id: string
  name: string
  slug: string
  description: string
  category: string
}

export const MOCK_AGENTS: MockAgent[] = [
  {
    id: 'agent-code-review',
    name: 'Code Review',
    slug: 'code-review',
    description: 'Automated PR reviews with inline comments and severity ratings.',
    category: 'Quality',
  },
  {
    id: 'agent-test-generator',
    name: 'Test Generator',
    slug: 'test-generator',
    description: 'Generates unit and integration tests for changed files on every push.',
    category: 'Quality',
  },
  {
    id: 'agent-security-scanner',
    name: 'Security Scanner',
    slug: 'security-scanner',
    description: 'Scans diffs for OWASP top-10 vulnerabilities and secrets exposure.',
    category: 'Security',
  },
  {
    id: 'agent-doc-writer',
    name: 'Doc Writer',
    slug: 'doc-writer',
    description: 'Keeps inline docs and README sections in sync with code changes.',
    category: 'Docs',
  },
  {
    id: 'agent-release-notes',
    name: 'Release Notes',
    slug: 'release-notes',
    description: 'Drafts human-readable release notes from merged PRs and commit logs.',
    category: 'Releases',
  },
  {
    id: 'agent-dep-updater',
    name: 'Dep Updater',
    slug: 'dep-updater',
    description: 'Opens PRs to bump outdated dependencies with changelog summaries.',
    category: 'Maintenance',
  },
]
