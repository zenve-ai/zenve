import { Route, Routes, Navigate } from 'react-router'
import Home from './pages/home'
import Login from './pages/login'
import NoOrganizationPage from './pages/no-organization'
import { OrgRootRedirect } from './pages/org-root-redirect'
import { PublicRoute } from './components/auth'

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
      <Route path="/no-organization" element={<PublicRoute><NoOrganizationPage /></PublicRoute>} />
      <Route path="/" element={<PublicRoute><OrgRootRedirect /></PublicRoute>} />
      <Route path="/:orgSlug" element={<PublicRoute><Home /></PublicRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
