import { Navigate, useLocation } from 'react-router'
import { useAppSelector } from '@/store/hooks'
import { selectIsAuthenticated } from '@/store/auth'

export default function PublicRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAppSelector(selectIsAuthenticated)
  const location = useLocation()
  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/'

  return isAuthenticated ? <Navigate to={from} replace /> : <>{children}</>
}
