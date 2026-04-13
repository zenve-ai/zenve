import { useEffect } from 'react'
import { Toaster } from 'sonner'
import './main.css'
import AppRoutes from '@/routes'
import { useAppDispatch } from '@/store/hooks'
import { restoreFromStorage } from '@/store/auth'
import { restoreFromStorage as restoreOrganizationFromStorage } from '@/store/organization'

export default function App() {
  const dispatch = useAppDispatch()

  useEffect(() => {
    dispatch(restoreFromStorage())
    dispatch(restoreOrganizationFromStorage())
  }, [dispatch])

  return (
    <>
      <AppRoutes />
      <Toaster richColors closeButton position="top-center" />
    </>
  )
}
