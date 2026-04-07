import { Route, Routes, Navigate } from 'react-router'
import Home from './pages/home'
import Login from './pages/login'
import NoOrganizationPage from './pages/no-organization'
import { RootPathRedirect } from './pages/root-path-redirect'
import { PrivateRoute, PublicRoute } from './components/auth'

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />

      {/* `/` is not a public page — redirect only (to /:orgSlug or /no-organization). Guests are sent to /login by PrivateRoute. */}
      <Route path="/" element={<PrivateRoute><RootPathRedirect /></PrivateRoute>} />

      <Route path="/no-organization" element={<PrivateRoute><NoOrganizationPage /></PrivateRoute>} />
      <Route path="/:orgSlug" element={<PrivateRoute><Home /></PrivateRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
