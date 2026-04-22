import { Route, Routes, Navigate } from 'react-router'
import AgentDetail from './pages/agent-detail'
import AgentsList from './pages/agents-list'
import Dashboard from './pages/dashboard'
import GitHubSetup from './pages/github-setup'
import GitHubCallback from './pages/github-callback'
import Login from './pages/login'
import NoProjectPage from './pages/no-project'
import OnboardingPage from './pages/onboarding'
import ProjectLayout from './pages/project-layout'
import { RootPathRedirect } from './pages/root-path-redirect'
import { PrivateRoute, PublicRoute } from './components/auth'

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />

      {/* `/` is not a public page — redirect only (to /:projectSlug or /no-project). Guests are sent to /login by PrivateRoute. */}
      <Route path="/" element={<PrivateRoute><RootPathRedirect /></PrivateRoute>} />

      <Route path="/no-project" element={<PrivateRoute><NoProjectPage /></PrivateRoute>} />
      <Route path="/onboarding" element={<PrivateRoute><Navigate to="/onboarding/1" replace /></PrivateRoute>} />
      <Route path="/onboarding/:step" element={<PrivateRoute><OnboardingPage /></PrivateRoute>} />
      <Route path="/github/callback" element={<PrivateRoute><GitHubCallback /></PrivateRoute>} />
      <Route
        path="/no-organization"
        element={<PrivateRoute><Navigate to="/no-project" replace /></PrivateRoute>}
      />
      <Route
        path="/:projectSlug"
        element={(
          <PrivateRoute>
            <ProjectLayout />
          </PrivateRoute>
        )}
      >
        <Route index element={<Dashboard />} />
        <Route path="agents" element={<AgentsList />} />
        <Route path="agents/:agentSlug" element={<AgentDetail />} />
        <Route path="github/setup" element={<GitHubSetup />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
