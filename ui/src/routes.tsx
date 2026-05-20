import { Route, Routes, Navigate } from 'react-router'
import AgentDetail from './pages/agent-detail'
import AgentsList from './pages/agents-list'
import Dashboard from './pages/dashboard'
import RuntimesPage from './pages/runtimes'
import IssuesList from './pages/issues-list'
import IssueDetail from './pages/issue-detail'
import AuthOAuthCallback from './pages/github-auth-callback'
import Login from './pages/login'
import NoWorkspacePage from './pages/no-workspace'
import OnboardingPage from './pages/onboarding'
import WorkspaceLayout from './pages/workspace-layout'
import { RootPathRedirect } from './pages/root-path-redirect'
import { PrivateRoute, PublicRoute } from './components/auth'

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
      <Route path="/auth/callback" element={<AuthOAuthCallback />} />

      {/* `/` is not a public page — redirect only (to /:workspaceId or /no-workspace). Guests are sent to /login by PrivateRoute. */}
      <Route path="/" element={<PrivateRoute><RootPathRedirect /></PrivateRoute>} />

      <Route path="/no-workspace" element={<PrivateRoute><NoWorkspacePage /></PrivateRoute>} />
      <Route path="/onboarding" element={<PrivateRoute><Navigate to="/onboarding/1" replace /></PrivateRoute>} />
      <Route path="/onboarding/:step" element={<PrivateRoute><OnboardingPage /></PrivateRoute>} />
      <Route
        path="/:workspaceId"
        element={(
          <PrivateRoute>
            <WorkspaceLayout />
          </PrivateRoute>
        )}
      >
        <Route index element={<Dashboard />} />
        <Route path="agents" element={<AgentsList />} />
        <Route path="agents/:agentSlug" element={<AgentDetail />} />
        <Route path="runtime" element={<RuntimesPage />} />
        <Route path="issues" element={<IssuesList />} />
        <Route path="issues/:issueId" element={<IssueDetail />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
