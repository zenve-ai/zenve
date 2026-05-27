import { Route, Routes, Navigate } from 'react-router'
import AgentDetail from './pages/agent-detail'
import AgentsList from './pages/agents-list'
import RuntimesPage from './pages/runtimes'
import IssuesList from './pages/issues-list'
import IssueDetail from './pages/issue-detail'
import PullRequestsList from './pages/pull-requests-list'
import PullRequestDetail from './pages/pull-request-detail'
import AuthOAuthCallback from './pages/github-auth-callback'
import Login from './pages/login'
import Signup from './pages/signup'
import NoWorkspacePage from './pages/no-workspace'
import OnboardingPage from './pages/onboarding'
import WorkspaceLayout from './pages/workspace-layout'
import SettingsPage, { SettingsRedirect } from './pages/settings'
import SettingsProfilePage from './pages/settings-profile'
import SettingsGeneralPage from './pages/settings-general'
import SettingsGlobalPage from './pages/settings-global'
import SettingsPipelinePage from './pages/settings-pipeline'
import SettingsIntegrationsPage from './pages/settings-integrations'
import SettingsDangerPage from './pages/settings-danger'
import { RootPathRedirect } from './pages/root-path-redirect'
import { PrivateRoute, PublicRoute } from './components/auth'

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
      <Route path="/signup" element={<PublicRoute><Signup /></PublicRoute>} />
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
        <Route index element={<Navigate to="agents" replace />} />
        <Route path="agents" element={<AgentsList />} />
        <Route path="agents/:agentSlug" element={<AgentDetail />} />
        <Route path="runtime" element={<RuntimesPage />} />
        <Route path="issues" element={<IssuesList />} />
        <Route path="issues/:issueId" element={<IssueDetail />} />
        <Route path="pull-requests" element={<PullRequestsList />} />
        <Route path="pull-requests/:prNumber" element={<PullRequestDetail />} />
        <Route path="settings" element={<SettingsPage />}>
          <Route index element={<SettingsRedirect />} />
          <Route path="profile" element={<SettingsProfilePage />} />
          <Route path="global" element={<SettingsGlobalPage />} />
          <Route path="general" element={<SettingsGeneralPage />} />
          <Route path="pipeline" element={<SettingsPipelinePage />} />
          <Route path="integrations" element={<SettingsIntegrationsPage />} />
          <Route path="danger" element={<SettingsDangerPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
