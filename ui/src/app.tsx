import { useEffect } from 'react'
import { Toaster } from 'sonner'
import './main.css'
import AppRoutes from '@/routes'
import { useAppDispatch } from '@/store/hooks'
import { restoreFromStorage } from '@/store/auth'
import { restoreFromStorage as restoreProjectFromStorage } from '@/store/project'

export default function App() {
  const dispatch = useAppDispatch()

  useEffect(() => {
    dispatch(restoreFromStorage())
    dispatch(restoreProjectFromStorage())
  }, [dispatch])

  return (
    <>
      <AppRoutes />
      <Toaster richColors closeButton position="top-center" />
    </>
  )
}
