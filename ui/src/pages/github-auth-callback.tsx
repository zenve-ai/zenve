import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate, Link } from 'react-router'
import { AlertTriangle, Loader2 } from 'lucide-react'
import { setToken, setUserData } from '@/lib/token'
import { useAppDispatch } from '@/store/hooks'
import { setCurrentUser } from '@/store/auth'
import config from '@/config'
import type { User } from '@/types'

export default function AuthOAuthCallback() {
  // --- declarations ---
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const token = searchParams.get('token')
  const [hasError, setHasError] = useState(false)

  // --- effects ---
  useEffect(() => {
    if (!token) { setHasError(true); return }

    setToken(token)

    fetch(`${config.apiUrl}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => {
        if (!r.ok) throw new Error('auth failed')
        return r.json() as Promise<User>
      })
      .then((user) => {
        setUserData(user)
        dispatch(setCurrentUser(user))
        navigate('/', { replace: true })
      })
      .catch(() => setHasError(true))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // --- render helpers ---
  const renderError = () => (
    <div className="flex min-h-screen items-center justify-center bg-background p-8">
      <div className="w-full max-w-md border border-dashed border-red-500/40">
        <div className="flex items-center gap-3 border-b border-dashed border-red-500/40 px-4 py-3">
          <AlertTriangle className="size-4 text-red-400" />
          <p className="text-sm font-mono font-medium text-red-400">Authentication failed</p>
        </div>
        <p className="px-4 py-4 text-[13px] font-mono text-muted-foreground">
          {!token
            ? <>No token was returned from GitHub.</>
            : <>Could not verify your account.</>
          }{' '}
          Please <Link to="/login" className="text-foreground underline">try again</Link>.
        </p>
      </div>
    </div>
  )

  const renderLoading = () => (
    <div className="flex min-h-screen items-center justify-center bg-background p-8">
      <div className="w-full max-w-md border border-dashed border-border/60">
        <div className="flex items-center gap-3 px-4 py-4">
          <Loader2 className="size-4 animate-spin text-muted-foreground/50" />
          <p className="text-[13px] font-mono text-muted-foreground">Signing you in…</p>
        </div>
      </div>
    </div>
  )

  // --- compose ---
  const renderMain = () => {
    if (hasError) return renderError()
    return renderLoading()
  }

  return renderMain()
}
