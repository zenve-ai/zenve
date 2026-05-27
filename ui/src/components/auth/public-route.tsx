import { Navigate } from 'react-router'
import { useAppSelector } from '@/store/hooks'
import { selectIsAuthenticated, selectIsInitialized } from '@/store/auth'

export default function PublicRoute({ children }: { children: React.ReactNode }) {
  const isInitialized = useAppSelector(selectIsInitialized)
  const isAuthenticated = useAppSelector(selectIsAuthenticated)

  if (!isInitialized) return null
  if (isAuthenticated) return <Navigate to="/" replace />
  return <>{children}</>
}
