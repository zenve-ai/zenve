import { Navigate, useLocation } from 'react-router'
import { useAppSelector } from '@/store/hooks'
import { selectIsAuthenticated, selectIsInitialized } from '@/store/auth'

export default function PrivateRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAppSelector(selectIsAuthenticated)
  const isInitialized = useAppSelector(selectIsInitialized)
  const location = useLocation()

  if (!isInitialized) {
    return <div className="flex min-h-screen items-center justify-center">Loading...</div>
  }

  return isAuthenticated
    ? <>{children}</>
    : <Navigate to="/login" state={{ from: location }} replace />
}
